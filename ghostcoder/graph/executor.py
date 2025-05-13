from ..utils import *
from ..prompts import load_prompt_template
from .webcrawler import create_crawler_agent


from typing import TypedDict, Annotated, Optional, Type, Any
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
#langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.graph import CompiledGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.pregel import RetryPolicy
#from langgraph.types import interrupt
#Autogen executors
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


def create_executor_agent(
    chat_model: LanguageModelLike,
    code_model: LanguageModelLike,
    *,
    max_retry = 3,
    name: Optional[str] = "executor_subgraph",
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    store: Optional[BaseStore] = None,
    interrupt_before: Optional[list[str]] = None,
    interrupt_after: Optional[list[str]] = None,
    debug: bool = False,
    ) -> CompiledGraph:

    #----------------
    # Define graph state
    #----------------

    class State(TypedDict):
        #input
        generated_codeblock: str 
        env_profiles: dict 

        #generated
        language: str
        use_docker: str
        docker_image: str
        need_wrapped: str
        bash_cmd: str
        script_file: str
        
        execution_results: strs


    #----------------
    # Define nodes
    #----------------
    
    def node_env_parser(state:State):
        """
        """

        # Pass inputs
        generated_codeblock = state['generated_codeblock']
        env_profiles = state['env_profiles']

        # Call prompt template
        prompt, input_vars = load_prompt_template('executor.router')

        # Parse human input
        human_input = "## Code block to execute:  \n" +  generated_codeblock
        human_input += "## Runtime environment profiles:\n"
        human_input += "### Native environment" + env_profiles['Native env languages'] + "\n"
        human_input += "### Docker images: \n" +  env_profiles['Docker status'] + "\n"

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Chose code run env by llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                json_output = chain.invoke(message)
                # Parse outputs
                language = json_output['language']
                use_docker = json_output['use_docker']
                docker_image = json_output['use_docker']
                need_wrapped = json_output['need_wrapped']
                script_file = json_output['script_file']
                bash_cmd = json_output['bash_cmd']
                
                break

            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error choosing env due to: \n{e}")

        return{
            "language": language,
            "use_docker": use_docker,
            "docker_image": docker_image,
            "need_wrapped": need_wrapped,
            "bash_cmd": bash_cmd,
            "script_file": script_file,
        }

    def node_script_wrapper(state:State):
        """
        """
        # Pass inputs
        generated_codeblock = state['generated_codeblock']
        script_file = state['script_file']
        env_profiles = state['env_profiles']
        target_file_path = os.path.join(env_profiles['task_dir'], script_file)

        # Write to script file, 
        #--------
        # NOTE: only tested in R
        #--------
        with open(target_file_path, 'w', encoding = 'utf-8') as f:
            f.write(generated_codeblock)

        return{
        }

    def node_cmd_execute(state:State):
        """
        """

        # Pass inputs
        generated_codeblock = state['generated_codeblock']
        language = state['language']
        use_docker = state['use_docker']
        docker_image = state['docker_image']
        need_wrapped = state['need_wrapped']
        bash_cmd = state['bash_cmd']
        env_profiles = state['env_profiles']

        # Parse env profiles
        task_dir = env_profiles['task_dirs']['task_dir']

        # Parse code to run directly
        if need_wrapped:
            exe_code = bash_cmd
            language = "bash"
        else:
            exe_code = generated_codeblock

        # Call executor
        if use_docker:
            try:
                executor = DockerCommandLineCodeExecutor(
                    image = docker_image, 
                    timeout = 60, 
                    work_dir= task_dir, # Use the task main dir to store the code files.
                    #bind_dir="./", # Path inside the docker
                )   
            except Exception as e:
                print(f"Error create docker cmd executor due to: \n{e}")
        else: 
            try:
                executor = executor = LocalCommandLineCodeExecutor(
                    timeout=30,  # Timeout for each code execution in seconds.
                    work_dir=task_dir,  # Use the task main dir to store the code files.
                )
            except Exception as e:
                print(f"Error create local cmd executor due to: \n{e}")

        # Execute codes
        try:
            async with executor:
                exe_result = await executor.execute_code_blocks(
                    code_blocks = [
                        CodeBlock(
                            language = language,
                            code = exe_code,
                        )
                    ],
                    cancellation_token=CancellationToken(),
                )

        # Parse execution result
        exit_code = exe_result.exit_code
        output = exe_result.output
        #execution_results = "Code executed with exit code "+ str(exit_code) +"\n"
        execution_results = "Code executed with output:\n" + output + "\n"
        
        return{
            'execution_results': execution_results,
        }

    #----------------
    # Define conditional edges
    #----------------

    def router_wrap(state:State):
        if state['need_wrapped']:
            return "wrapper"
        else:
            return "execute"
        
        
    #----------------
    # Compile graph
    #----------------

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("Env parser", node_env_parser)
    builder.add_node("Wrapper", node_script_wrapper)
    builder.add_node("Executor",node_cmd_execute)
    # add edges
    builder.add_edge(START, "Env parser")
    builder.add_conditional_edges(
        "Env parser", 
        router_is_codeblock_qualified,
        {               
            "wrapper"   : "Wrapper", 
            "execute"   : "Executor"}
        )
    builder.add_edge("Wrapper", "Executor")
    builder.add_edge("Executor", END)
    
    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )
