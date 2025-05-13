from ..utils import *
from ..prompts import load_prompt_template
from .webcrawler import create_crawler_agent
from ..config import *

from typing import TypedDict, Annotated, Optional, Type, Any
import operator 
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



def create_coder_agent(
    chat_model: LanguageModelLike,
    code_model: LanguageModelLike,
    *,
    max_retry = 3,
    name: Optional[str] = "coder_subgraph",
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
        task_instruction: str 
        ref_codeblocks: str
        previous_codeblock: str
        data_perception: str
        env_profiles: str

        inputvar_names: list[str]
        
        presis_add: str

        #parameter
        n_iter: int
        n_error: int 
        critique_status: bool
        error_status: bool
        websearch: bool

        #generated
        generated_codeblock: Annotated[list[str], operator.add]
        critique: str
        execution_outstr: str
        error_summary: str
        web_summary: str
        error_solution: str

    #----------------
    # Load subgraphs
    #----------------
    # Get crawler subgraph 
    crawler_subgraph = create_crawler_agent(
        chat_model = chat_model, 
        code_model = code_model,
        max_retry = max_retry,
        name =  "crawler_subgraph",
        config_schema = config_schema,
        checkpointer = checkpointer,
        store = store,
        interrupt_before = interrupt_before,
        interrupt_after = interrupt_after,
        debug = debug,
        )
    
    executor_subgraph = create_executor_agent(
        chat_model = chat_model, 
        code_model = code_model,
        max_retry = max_retry,
        name =  "executor_subgraph",
        config_schema = config_schema,
        checkpointer = checkpointer,
        store = store,
        interrupt_before = interrupt_before,
        interrupt_after = interrupt_after,
        debug = debug,
        )

    #----------------
    # Define nodes
    #----------------

    def node_code_generation(state:State):
        """
        This function generates code based on the task description, data perception,
        previous code, generated code, and reference code blocks. It uses an LLM to generate the code
        and handles retries if the invocation fails.
        """

        # Pass inputs
        task_instruction = state['task_instruction']
        data_perception = state['data_perception']
        previous_codeblock = state['previous_codeblock']
        ref_codeblocks = state['ref_codeblocks']
        env_profiles = state['env_profiles']
        try:
            n_iter = state[n_iter]
        except:
            n_iter = 0
        
        try:
            error_status = state['error_status']
            error_summary = state['error_summary']
        except:
            error_status = False

        try:
            generated_codeblock = state['generated_codeblock'][-1]
        except:
            generated_codeblock = ""

        try:
            critique = state['critique']
        except:
            critique = ""

        try: 
            error_solution = state['error_solution']
        except:
            error_solution = ""

        # Parse human input
        human_input = "## Data  \nThe current code block serves the following data files:\n" + data_perception + '\n'
        
        # For error fix
        if error_status:
            human_input += "## Error fix  \nYour previously code had the following error:\n" + error_summary + "\n"
            human_input += "## Your code  \nThe code you generated for the above task is as follows, fix those error:\n" + generated_codeblock + "\n"
            if len(web_summary) > 0:
                human_input += "## Fix solution  \nFollowing are web searched solutions to help with fix above errors:\n" + error_solution

        # For iterated code generation with critique
        elif len(critique) > 0:
            human_input += "\n## Critique  \nUsers think your code has the following defects:  \n"+ critique +"\n"
            human_input += "## Your code  \nThe code you generated for the above task is as follows, please modify and enhance it according to the instructions above.\n" + generated_codeblock

        else:
            # For continued workflow, 1st iteration 
            if len(previous_codeblock) > 0:
                human_input += "\nThe previous code in the workflow to which the current code belongs is as follows, please use the same coding style as it:\n" + previous_codeblock

            # When RAG is available 
            if len(ref_codeblocks) > 0:
                few_shots = "## Reference code blocks\nSome code blocks you can refer to that accomplish similar tasks, but the specific details may differ from this task:\n" + ref_codeblocks
                human_input += few_shots


        # Call prompt template
        prompt, input_vars = load_prompt_template('coder.script_gen')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(
                task_instruction = task_instruction,
                output_dir = OUTPUT_DIR+'/',
                figure_dir = FIGURE_DIR+'/',
                )),
            HumanMessage(content=human_input)
        ]

        # Generate code with llm
        i = 0
        while i < max_retry:
            try:
                response = code_model.invoke(message)
                code_block = extract_python_codeblock(response.content)
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating code: {e}")

        # Handle failure after maximum retries
        if code_block is None:
            raise RuntimeError("Failed to generate code after maximum retries.")

        # Update iteration 
        n_iter += 1
            
        return {
            'generated_codeblock':[code_block],
            'n_iter':n_iter
        }


    def node_criticism(state:State):
        """
        This function evaluates the generated code using an LLM and provides a critique.
        It determines if the code is qualified and generates a self-critique report.
        """

        # Pass inputs
        task_instruction = state['task_instruction']
        generated_codeblock = state['generated_codeblock'][-1]

        # Parse human input
        human_input = "## Codes to be evaluated  \nThe code you generated for the above task is as follows, please conduct an evaluation:\n" + generated_codeblock

        # Call prompt template
        prompt, input_vars = load_prompt_template('coder.critisim')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(task_instruction = task_instruction)),
            HumanMessage(content=human_input)
        ]

        # Generate critique with llm
        chain = code_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                json_output = chain.invoke(message)
                critique_status = json_output['qualified']
                critique = json_output['self-critique report']
                critique = critique_report_2md(critique)
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating critique due to: \n{e}")

        return {
            'critique_status':critique_status, 
            'critique': critique
        }


    def node_executor(state:State):
        """
        """

        # Pass inputs
        subgraph_input = {
            "generated_codeblock":state['generated_codeblock'],
            "env_profiles":state['env_profiles']
        }


        # Invoke executor subgraph 
        subgraph_states = executor_subgraph.invoke(
            subgraph_input,
            config = config_schema
        )
        
        # Parse subgraph results
        execution_outstr = subgraph_states['execution_results']

        return {
            'execution_outstr': execution_outstr
        }


    def node_output_parser(state:State):
        """
        This function parses the output of code execution to determine if there was an error
        and if web search is needed. It uses an LLM to interpret the output.
        """
        
        # Pass inputs
        execution_outstr = state['execution_outstr']

        # Parse human input
        human_input = "The code excuted with folloing outputs:\n" + execution_outstr

        # Call prompt template
        prompt, input_vars = load_prompt_template('coder.ouput_parse')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
            ]

        # Parse execution output with llm
        chain = code_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                response = chain.invoke(message)
                error_status = response['error occurs']
                websearch = response['need web search']
                error_summary = response['error']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating code: {e}")

        return{
            'error_status':error_status,
            'websearch':websearch,
            'error_summary':error_summary
        }
    
    def node_webcrawler(state:State):
        # Pass inputs
        generated_codeblock = state['generated_codeblock'][-1]
        error_summary = state['error_summary']
        query_context = "I am experiencing the following problem with the execution of my code:\n" + error_summary
        query_context += "\n\nMy code as follow:\n" + generated_codeblock

        subgraph_input = {
            "query context": query_context
        }

        # Get error fix web search solution by subgraph
        subgraph_states = crawler_subgraph.invoke(
            subgraph_input,
            config = config_schema
        )

        # Parse result
        summary = subgraph_states['summary']
        
        return {
            "web_summary":summary
        }

        

    def node_debugger(state:State):
        """
        This function fixes errors in the generated code using information from data perception
        and potentially web solutions. It updates the generated code and iteration counters.
        """

        # Pass inputs
        error_summary = state['error_summary']
        generated_codeblock = state['generated_codeblock'][-1]
        try:
            web_summary = state['web_summary']
        except:
            web_summary = ""

        data_perception = state['data_perception']

        try:
            n_error = state['n_error']
        except:
            n_error = 0
        n_iter = state['n_iter']

        # Parse human input
        human_input = "## Original code  \n" + generated_codeblock +"\n\n"
        human_input += "## Data information  \n" + data_perception +"\n\n"
        human_input += "## Error message  \nThe error message and related information as follow:" +"\n---\n"
        human_input += error_summary +"\n---\n"
        if len(web_summary)>1:
            human_input += "## Web solution  \nSearching through the web, the recommended solutions are as follows:" +"\n---\n" + web_summary

        # Call prompt template
        prompt, input_vars = load_prompt_template('coder.gen_fixsolut')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Fix code error with llm
        i = 0
        while i < max_retry: 
            try:
                print("Fixing error code.")
                response = code_model.invoke(message)
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating code: {e}")
        
        # Update iteration 
        n_error += 1
        n_iter -= 1

        return {
            'error_solution':response.content, 
            'n_error':n_error,
            'n_iter':n_iter
        }

    #----------------
    # Define conditional edges
    #----------------

    def router_is_codeblock_qualified(state:State):
        if state['critique_status']:
            return "continue"
        else:
            return "regen"
        
    def router_is_error_occur(state:State):
        if state['error_status']:
            if state['websearch']:
                return "websearch"
            else:
                return "errorfix"
        else:
            return "end"
        
    #----------------
    # Compile graph
    #----------------

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("Code generation", node_code_generation)
    builder.add_node("Criticism",node_criticism)
    builder.add_node("Executor",node_executor)
    builder.add_node("Output parser",node_output_parser)
    builder.add_node("Webcrawler",node_webcrawler)
    builder.add_node("Consultant",node_debugger)
    # add edges
    builder.add_edge(START,"Code generation")
    builder.add_edge("Code generation", "Criticism")
    builder.add_conditional_edges(
        "Criticism", 
        router_is_codeblock_qualified,
        {
            "continue"  : "Executor", 
            "regen"     : "Code generation"}
        )
    builder.add_edge("Executor", "Output parser")
    builder.add_conditional_edges(
        "Output parser", 
        router_is_error_occur,
        {
            "websearch" : "Webcrawler", 
            "errorfix"  : "Consultant", 
            "end"       : END}
        )
    builder.add_edge("Webcrawler","Consultant")
    
    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )
