from ..utils import *
from ..prompts import load_prompt_template
from .crawler import create_crawler_agent

import pickle

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
        inputvar_names: list[str]
        data_perception: str
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

    #----------------
    # Define nodes
    #----------------
    
    def node_data_perception(state:State):
        """
        This function is responsible for perceiving data based on the current state.
        It extracts variable names from the state and returns them as part of the data perception.
        Note: The actual 'data_perception' logic is not implemented here and should be defined elsewhere.
        """

        # Pass inputs
        inputvar_names = state['inputvar_names']
        data_perception = state['data_perception']

        return{
            'data_perception': data_perception
        }

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
        try:
            n_iter = state[n_iter]
        except:
            n_iter = 0
        try:
            generated_codeblock = state['generated_codeblock'][-1]
        except:
            generated_codeblock = ""

        # Parse human input
        human_input = "## Input Variables and I/O   \nThe current code block serves the following variables:\n" + data_perception + '\n'

        # For continued workflow
        if len(previous_codeblock) > 0:
            human_input += "\nThe previous code in the workflow to which the current code belongs is as follows, please use the same coding style as it:\n" + previous_codeblock
        
        # For iterated code generation
        elif len(generated_codeblock) > 0:
            human_input += "\n## Iterative code generation  \nThe code you generated for the above task is as follows, please modify and enhance it according to the instructions above:\n" + generated_codeblock

        # When RAG is available 
        if len(ref_codeblocks) > 0:
            few_shots = "## Reference code blocks\nSome code blocks you can refer to that accomplish similar tasks, but the specific details may differ from this task:\n" + ref_codeblocks
            human_input += few_shots

        # Call prompt template
        prompt, input_vars = load_prompt_template('script_gen')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(task_instruction = task_instruction)),
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
        prompt, input_vars = load_prompt_template('critisim')

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


    def node_sandbox_run(state:State):
        """
        Runs the generated code block in a sandbox environment with provided input variables.
        Returns the execution output string, which includes both the output and any error messages.
        """

        # Pass inputs
        generated_codeblock = state['generated_codeblock'][-1]
        presis_add = state['presis_add']
        inputvar_names = state['inputvar_names']
    
        print(generated_codeblock)
        
        # Load input variables 
        with open(presis_add, 'rb') as f:
            inputvars = pickle.load(f)

        # Parse input variables
        var_dict = {}
        for i in range(len(inputvar_names)):
            var_dict[inputvar_names[i]] = inputvars[i]

        # Run in sandbox
        i = 0
        res = None
        while i < max_retry:
            try:
                print('Testing generated code...')
                res = trial_run(generated_codeblock, var_dict)
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating code: {e}")
        
        print(res)

        # Ensure res is not None to avoid later errors
        if res is None:
            res = {'output': '', 
                'error': 'Execution failed without any result', 
                'output_var': {}}

        # Parse output
        print('Code tested.')
        execution_outstr = ""
        if isinstance(res['output'], str):
            execution_outstr += '## Execution output  \n'+res['output'] + '\n\n'
            print('Code execution with output:\n'+res['output'])
        if isinstance(res['error'], str):
            execution_outstr += '## Execution error message  \n' +res['error'] + '\n\n'
            print('!!! Code execution with ERROR:\n'+res['error'])

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
        prompt, input_vars = load_prompt_template('ouput_parse')

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
    
    def node_websearch_subgraph(state:State):
        # Pass inputs
        subgraph_input = {
            "generated_codeblock":state['generated_codeblock'],
            "error_summary":state['error_summary']

        }

        # Get error fix web search solution by subgraph
        subgraph_states = crawler_subgraph.invoke(
            subgraph_input,
            config = config_schema
        )

        error_solution = subgraph_states['error_solution']
        return {
            "error_solution":error_solution
        }

        

    def node_error_fixer(state:State):
        """
        This function fixes errors in the generated code using information from data perception
        and potentially web solutions. It updates the generated code and iteration counters.
        """

        # Pass inputs
        error_summary = state['error_summary']
        generated_codeblock = state['generated_codeblock'][-1]
        try:
            error_solution = state['error_solution']
        except:
            error_solution = ""
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
        if len(error_solution)>1:
            human_input += "## Web solution  \nSearching through the web, the recommended solutions are as follows:" +"\n---\n" + error_solution

        # Call prompt template
        prompt, input_vars = load_prompt_template('gen_fixsolut')

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
                code_block = extract_python_codeblock(response.content)
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating code: {e}")
        
        # Handle failure after maximum retries
        if code_block is None:
            raise RuntimeError("Failed to fix code after maximum retries.")

        # Update iteration 
        n_error += 1
        n_iter -= 1

        return {
            'generated_codeblock':[code_block], 
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
    builder.add_node("Data perception", node_data_perception)
    builder.add_node("Code generation", node_code_generation)
    builder.add_node("Criticism",node_criticism)
    builder.add_node("Sandbox execution",node_sandbox_run)
    builder.add_node("Output parser",node_output_parser)
    builder.add_node("Web search",node_websearch_subgraph)
    builder.add_node("Error fix",node_error_fixer)
    # add edges
    builder.add_edge(START, "Data perception")
    builder.add_edge("Data perception","Code generation")
    builder.add_edge("Code generation", "Criticism")
    builder.add_conditional_edges(
        "Criticism", 
        router_is_codeblock_qualified,
        {
            "continue"  : "Sandbox execution", 
            "regen"     : "Code generation"}
        )
    builder.add_edge("Sandbox execution", "Output parser")
    builder.add_conditional_edges(
        "Output parser", 
        router_is_error_occur,
        {
            "websearch" : "Web search", 
            "errorfix"  : "Error fix", 
            "end"       : END}
        )
    builder.add_edge("Web search","Error fix")
    builder.add_edge("Error fix", "Sandbox execution")
    
    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )
