import logging
from ..utils import *
from ..prompts import load_prompt_template
from ..config import coder_config

from typing import TypedDict, Annotated, Optional, Type, Any
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
#langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
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

#----------------
# Initial logging
#----------------
logger = logging.getLogger(__name__)

#----------------
# Agent orchestration
#----------------
def create_executor_agent(
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
    ) -> CompiledStateGraph:

    #----------------
    # Define graph state
    #----------------

    class State(TypedDict):
        #input
        generated_codeblock: str 
        env_profiles: dict  

        #generated
        language: str
        use_docker: bool
        docker_image: str
        need_wrapped: bool
        bash_cmd: str
        script_file: str
        
        execution_results: str


    #----------------
    # Define nodes
    #----------------
    
    def node_env_parser(state:State):
        """
        """
        logger.debug("START node_env_parser")
        logger.info("============executor============\nStarting executor subagent...\n")
        # Pass inputs
        logger.info("Parsing env...")
        generated_codeblock = state['generated_codeblock']
        try: 
            env_profiles = state['env_profiles']
            logger.info("Using given env profiles from graph input.")
        except: 
            env_profiles = get_env_profiles()
            logger.info("Using default env profiles from config.")

        # Call prompt template
        prompt, input_vars = load_prompt_template('executor.router')
        logger.debug(
            "Using prompt:\n--------prompt--------\n"+
            str(prompt)+
            "\n----------------")

        # Parse human input
        human_input = "## Code block to execute:  \n" +  generated_codeblock + "\n"
        human_input += "## Runtime environment profiles:\n"
        human_input += "### Native environment" + str(env_profiles['native env languages']) + "\n"
        human_input += "### Docker images: \n" +  env_profiles['docker status'] + "\n"

        logger.info(
            "Code to be executed:\n--------code block--------\n"+
            str(generated_codeblock)+
            "\n----------------",
            )

        logger.debug(
            "Detailed env profiles:\n--------env profiles--------\n"+
            str(env_profiles)+
            "\n----------------",
            )

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Chose code run env by llm
        chain = code_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                json_output = chain.invoke(message)
                # Parse outputs
                language = json_output['language']
                use_docker = json_output['use_docker']
                docker_image = json_output['docker_image']
                need_wrapped = json_output['need_wrapped']
                script_file = json_output['script_file']
                bash_cmd = json_output['bash_cmd']
                # To log
                if need_wrapped:
                    logger.info(
                        "".join([
                            "LLM response:\n----------------",
                            "\ncoding language:",language,
                            "\nto use docker:",str(use_docker),', with docker image:', docker_image,
                            "\nto warp the code block:",str(need_wrapped),', to file',script_file,
                            '\nwith bash cmd:\n',bash_cmd,
                            "\n----------------",
                        ])
                        )
                else:
                    logger.info(
                        "".join([
                            "LLM response:\n--------",
                            "coding language:",language,
                            "\nto use docker:",str(use_docker),', with docker image:', docker_image,
                            "\nto warp the code block:",str(need_wrapped),
                            "\n----------------",
                        ])
                        )
                break

            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception with"+str(i)+"tries:\n")
                else:
                    logger.debug("Get exception when parsing env:\n"+str(e))
        logger.debug("END node_env_parser")
        return{
            "language": language,
            "use_docker": use_docker,
            "docker_image": docker_image,
            "need_wrapped": need_wrapped,
            "script_file": script_file,
            "bash_cmd": bash_cmd,
        }

    def node_script_wrapper(state:State):
        """
        """
        logger.debug("START node_script_wrapper")

        # Pass inputs
        generated_codeblock = state['generated_codeblock']
        script_file = state['script_file']
        env_profiles = state['env_profiles']
        target_file_path = os.path.join(env_profiles['task_dirs']['task_home'], script_file)
        
        # Parse code block
        logger.info("Trying to extract code block from markdown code block")
        try:
            generated_codeblock = extract_code_blocks(extract_code_blocks)
        except:
            generated_codeblock = generated_codeblock
            logger.debug("Failed to extract code block from markdown.")

        # Warp codeblock
        with open(target_file_path, 'w', encoding = 'utf-8') as f:
            f.write(generated_codeblock)
        logger.info("Successfully wrapped code blocks to"+target_file_path)

        logger.debug("END node_script_wrapper")

    async def node_cmd_execute(state:State):
        """
        """
        logger.debug("START node_cmd_execute") 

        # Pass inputs
        generated_codeblock = state['generated_codeblock']
        language = state['language']
        use_docker = state['use_docker']
        docker_image = state['docker_image']
        need_wrapped = state['need_wrapped']
        bash_cmd = state['bash_cmd']
        env_profiles = state['env_profiles']

        # Parse env profiles
        task_dir = env_profiles['task_dirs']['task_home']

        # Parse code to run directly
        if need_wrapped:
            if bash_cmd.startswith("```"):
                # Parse bash cmd
                bash_cmd = extract_code_blocks(bash_cmd)[0]
            exe_code = bash_cmd
            use_language = "bash"
            logger.info("Ready to execute warpped code block.")
        else:
            exe_code = generated_codeblock
            use_language = language
            logger.info("Ready to execute code block.")
        
        #print(exe_code)
        #print(use_docker)
        #print(docker_image)

        # 1. Check if EXECUTOR already exist
        if hasattr(coder_config, 'EXECUTOR') and coder_config.EXECUTOR is not None:
            executor = coder_config.EXECUTOR
            logger.info("Using created executor.")
        else:
            # Create executor
            if use_docker:
                try:
                    executor = DockerCommandLineCodeExecutor(
                        image = docker_image, 
                        timeout = 60, 
                        work_dir= task_dir, # Use the task main dir to store the code files.
                        #bind_dir="./", # Path inside the docker
                        delete_tmp_files  = True, # All code history saved in memory, no need temp code files
                        auto_remove = False, # Do not auto remove container, for consistent running env 
                        stop_container = False, # Do not auto stop container
                    )   
                    logger.info("Created new docker cmd executor with docker image:"+docker_image)
                except Exception as e:
                    logger.exception("Get exception when creating docker executor:")
                    # print(f"Error create docker cmd executor due to: \n{e}")
            else: 
                try:
                    executor = LocalCommandLineCodeExecutor(
                        timeout=30,  # Timeout for each code execution in seconds.
                        work_dir=task_dir,  # Use the task main dir to store the code files.
                    )
                    logger.info("Created new native env cmd executor.")
                except Exception as e:
                    logger.exception("Get exception when creating native executor:")
                    # print(f"Error create local cmd executor due to: \n{e}")
        # Update Executor
        coder_config.EXECUTOR = executor
        
        # Execute codes
        try:
            async with executor:
                exe_result = await executor.execute_code_blocks(
                    code_blocks = [
                        CodeBlock(
                            language = use_language,
                            code = exe_code,
                        )
                    ],
                    cancellation_token=CancellationToken(),
                )
                logger.info("Successfully executed code block.")
                logger.debug("with output:\n" + exe_result.output)
        except Exception as e:
            logger.exception("Get exception when running executor:")
            #print(f"Error executor code due to: \n{e}")

        # Parse execution result
        output = exe_result.output
        execution_results = "Code executed with output:\n" + output + "\n"
        #exit_code = exe_result.exit_code
        #execution_results = "Code executed with exit code "+ str(exit_code) +"\n"

        logger.info("End executor subagent...\n============executor============\n")
        logger.debug("END node_cmd_execute")

        return{
            'execution_results': execution_results,
        }

    #----------------
    # Define conditional edges
    #----------------

    # def router_wrap(state:State):
    #     logger.debug("START router_wrap")
    #     if state['need_wrapped']:
    #         logger.debug("SELECTED wrapper IN router_wrap")
    #         logger.debug("END router_wrap")
    #         return "wrapper"
            
    #     else:
    #         logger.debug("SELECTED execute IN router_wrap")
    #         logger.debug("END router_wrap")
    #         return "execute"
        
        
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
    builder.add_edge("Env parser","Wrapper")
    # builder.add_conditional_edges(
    #     "Env parser", 
    #     router_wrap,
    #     {               
    #         "wrapper"   : "Wrapper", 
    #         "execute"   : "Executor"}
    #     )
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
