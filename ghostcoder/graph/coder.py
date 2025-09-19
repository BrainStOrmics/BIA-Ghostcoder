import logging
from ..utils import *
from ..prompts import load_prompt_template
from .webcrawler import create_crawler_agent
from .executor import create_executor_agent
from ..config import *

from typing import TypedDict, Annotated, Optional, Type, Any
import operator 
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

#----------------
# Initial logging
#----------------
logger = logging.getLogger(__name__)

#----------------
# Agent orchestration
#----------------
def create_coder_agent(
    chat_model: LanguageModelLike,
    reason_model: LanguageModelLike,
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
    ) -> CompiledStateGraph:

    #----------------
    # Define graph state
    #----------------

    class State(TypedDict):
        #input
        # session_id: str # Moved to config
        task_instruction: str 
        ref_codeblocks: str
        previous_codeblock: str
        data_perception: str
        # env_profiles: str # Moved to config

        #tracing parameter
        n_iter: int
        n_error: int 
        # websearch: bool # Moved to config

        #generated
        generated_codeblock: Annotated[list[str], operator.add] # Generated code, save history for version control 
        comment: Annotated[list[str], operator.add] # Critique of the generated code
        execution_outstr: Annotated[list[str], operator.add]  # Execution output string
        error_status: bool
        error_summary: str
        web_summary: str # Summary of related web search for the error
        error_solution: str # Solution of fix the error
        
        #decision status
        critique_status: bool # Whether the code satisfied to the user's intention
        fix_type: str # Type of the error, to debug the code or manage packages

    #----------------
    # Load subgraphs
    #----------------
    # Get crawler subgraph 
    logger.debug("Loading crawler subgraph.")
    crawler_subgraph = create_crawler_agent(
        chat_model = chat_model, 
        max_retry = max_retry,
        name =  "crawler_subgraph",
        config_schema = config_schema,
        checkpointer = checkpointer,
        store = store,
        interrupt_before = interrupt_before,
        interrupt_after = interrupt_after,
        debug = debug,
        )
    
    logger.debug("Loading executor subgraph.")
    executor_subgraph = create_executor_agent(
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
        logger.debug("START node_code_generation")
        # 1. Pass inputs
        # 1.1 Basic inputs
        task_instruction = state['task_instruction']
        try:
            generated_codeblock = state['generated_codeblock'][-1]
        except:
            generated_codeblock = ""
        try:
            n_iter = state["n_iter"]
        except:
            n_iter = 0
        if n_iter == 0:
            logger.info("============coder============\nStarting coder subagent...\n")

        logger.debug("task_instruction: "+str(task_instruction))
        logger.debug("data_perception: "+str(data_perception))
        logger.info("Start #"+str(n_iter)+" iteration of code generation.")
        # 1.2 In a continues workflow
        previous_codeblock = state['previous_codeblock']
        logger.debug("previous_codeblock: "+str(previous_codeblock))
        # 1.3 When reference provided
        ref_codeblocks = state['ref_codeblocks']
        logger.debug("ref_codeblocks: "+str(ref_codeblocks))
        # 1.4 When working in code improvement loop
        try:
            comment = state['comment']
        except:
            comment = ""
        logger.debug("critique comment:"+str(comment))
        logger.debug("generated_codeblock:"+str(generated_codeblock))
        # 1.5 When working in error fix loop
        try:
            error_status = state['error_status']
            execution_outstr = state['execution_outstr']
        except:
            error_status = False
        logger.debug("error_status:"+str(error_status))
        # 1.6 Parse output paths
        fig_dir = file_config.FIGURE_DIR
        out_dir = file_config.OUTPUT_DIR
        output_paths = '--output_data_dir: '+out_dir + '\n--output_figure_dir'+ fig_dir
        logger.debug("Output paths: "+output_paths)

        # 2. Parse human input and Task Instruction
        human_input = "## Data  \nThe current code block serves the following data files:\n" + data_perception + '\n'
        # 2.1  When working in error fix loop
        if error_status:
            logger.info("Switch to error fix mode.")
            # 2.1.1 Edit task instruction
            task_instruction = "Please fix the errors. The code and error output encountered are attached at the end."
            # 2.1.2 Edit human input
            human_input += "## Error fix  \n### Your previously code had the following error:\n" + execution_outstr + "\n"
            human_input += "### The code you generated for the above task is as follows, fix those error:\n" + generated_codeblock + "\n"

        # 2.2 When working in code improvement loop
        elif len(comment) > 0:
            logger.info("Switch to iterated code generation mode.")
            # 2.2.1 Edit task instruction
            task_instruction = "When generating code for the following tasks:\n" + task_instruction + "\nThe generated code does not fully meet expectations. The suggestions received provided latter; please re-optimize the code." 
            # 2.2.2 Edit human input
            human_input += "\n## Critique comment\nUsers think your code has the following defects:  \n"+ comment +"\n"
            human_input += "### The code you generated for the above task is as follows, please modify and enhance it according to the instructions above.\n" + generated_codeblock
        # 2.3 When generate new code
        else:
            log_str = "Generating new code block..."
        # 2.3.1 Edit task instruction
            task_instruction = "Generate a code block to accomplish the following task:\n" + task_instruction + "\nWhile following the code generation procedure, you can also obtain additional useful information from the subsequent user input provided."
        # 2.3.2 In a continues workflow
            if len(previous_codeblock) > 0:
                log_str += " with previous code..."
                # Edit human input
                human_input += "\nThe previous code in the workflow to which the current code belongs is as follows, please use the same coding style as it:\n" + previous_codeblock
        # 2.3.3 When reference code is available 
            if len(ref_codeblocks) > 0:
                log_str += " with reference code block(s)..."
                # Edit human input
                few_shots = "## Reference code blocks\nSome code blocks you can refer to that accomplish similar tasks, but the specific details may differ from this task:\n" 
                i = 1
                for cb in ref_codeblocks:
                    few_shots += "### Reference code #" + str(i) + "\n" 
                    few_shots += cb + "\n\n" 
                human_input += few_shots
            logger.info(log_str)
        logger.debug("human_input: %s", human_input)

        # 3. Prepare LLM input
        # 3.1 Call prompt template
        prompt, input_vars = load_prompt_template('coder.script_gen')
        logger.debug("prompt:"+str(prompt))
        
        # 3.2 Construct input message
        message = [
            SystemMessage(content=prompt.format(
                task_instruction = task_instruction,
                output_dir = output_paths)),
            HumanMessage(content=human_input)
        ]

        # 4. Generate code with llm
        # 4.1 Construct LLM chain
        chain = code_model | JsonOutputParser()
        # 4.2 Invoke LLM with retry
        i = 0
        logger.info("Start generating code block with LLM...")
        while i < max_retry:
            try:
                response = chain.invoke(message)
                #code_block = extract_python_codeblock(response.content) # No longer limited to python code anymore
                code_block = response['code_block']
                script_type = response['script_type']
                logger.info("Successfully generated code block.")
                logger.debug("generated code block: "+str(code_block))
                logger.debug("generated script type: "+str(script_type))
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception when generating code:")
                    raise  
                else:
                    logger.debug("Get exception when generating code:\n"+str(e))
        # Handle failure after maximum retries
        if code_block is None:
            raise RuntimeError("Failed to generate code after maximum retries.")
        # Update iteration 
        n_iter += 1
        
        logger.debug("END node_env_parser")
        return {
            'generated_codeblock':[code_block],
            'scrpt_type': script_type
            'n_iter':n_iter
        }


    def node_criticism(state:State):
        """
        This function evaluates the generated code using an LLM and provides a critique.
        It determines if the code is qualified and generates a self critique report.
        """
        logger.debug("START node_criticism")

        # Pass inputs
        task_instruction = state['task_instruction']
        generated_codeblock = state['generated_codeblock'][-1]

        # Parse human input
        human_input = "## Codes to be evaluated  \nThe code you generated for the above task is as follows, please conduct an evaluation:\n" + generated_codeblock
        logger.debug("human_input: "+str(human_input))

        # Call prompt template
        prompt, input_vars = load_prompt_template('coder.critisim')
        logger.debug("prompt:"+str(prompt))

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(task_instruction = task_instruction)),
            HumanMessage(content=human_input)
        ]

        # Generate critique with llm
        logger.info("Critique generated code block with LLM...")
        chain = reason_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                json_output = chain.invoke(message)
                critique_status = json_output['recommendation']
                comment = json_output['comment']
                #critique = critique_report_2md(critique)
                logger.info("Successfully generated critique.")
                logger.debug("critique_status: "+str(critique_status))
                logger.debug("critique: "+str(critique))
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception when generating critique:")
                    raise  
                else:
                    logger.debug("Get exception when generating critique:\n"+str(e))
        
        logger.debug("END node_criticism")
        return {
            'critique_status': critique_status, 
            'comment': comment,
        }

    async def node_executor(state:State):
        """
        """
        logger.debug("START node_executor")

        # Pass inputs
        generated_codeblock = state['generated_codeblock'][-1]
        env_profiles = state['env_profiles']

        # Parse code block to fit with autogen executors
        code_blocks = extract_code_blocks(generated_codeblock)

        # Parse input
        subgraph_input = {
            "generated_codeblock": code_blocks[0], # ONLY use 1st code block
            "env_profiles": env_profiles
        }
        logger.debug("subgraph_input: "+str(subgraph_input))

        # Invoke executor subgraph 
        logger.info("Calling executor subagent from node_executor...")
        subgraph_states = await executor_subgraph.ainvoke(
            subgraph_input,
            config = config_schema
        )
        
        # Parse subgraph results
        execution_outstr = subgraph_states['execution_results']
        logger.info("Successfully executed code block.")
        logger.debug("execution_outstr: "+str(execution_outstr))

        # Parse human input
        human_input = "### EXECUTION OUTPUT:\n" + execution_outstr
        logger.debug("human_input: "+str(human_input))

        # Call prompt template
        prompt, input_vars = load_prompt_template('coder.ouput_parse')
        logger.debug("prompt:"+str(prompt))

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
            ]

        # Parse execution output with llm
        logger.info("Parse execution output with LLM...")
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                response = chain.invoke(message)
                error_status = response['has_error']
                error_summary = response['error_summary']
                logger.info("Successfully parsed execution output.")
                logger.debug("error_status: "+str(error_status))
                logger.debug("error_summary: "+str(error_summary))
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception when parsing execution output:")
                    raise  
                else:
                    logger.debug("Get exception when parsing execution output:\n"+str(e))

        logger.debug("END node_executor")
        return{
            'execution_outstr': execution_outstr,
            'error_status':error_status,
            'error_summary':error_summary
        }

    
    def node_webcrawler(state:State):
        """
        """
        logger.debug("START node_webcrawler")

        # Pass inputs
        generated_codeblock = state['generated_codeblock'][-1]
        error_summary = state['error_summary']
        query_context = "I am experiencing the following problem with the execution of my code:\n" + error_summary
        query_context += "\n\nMy code as follow:\n" + generated_codeblock

        subgraph_input = {
            "query_context": query_context
        }
        logger.debug("subgraph_input: "+str(subgraph_input))

        # Get error fix web search solution by subgraph
        logger.info("Calling crawler subagent from node_webcrawler...")
        subgraph_states = crawler_subgraph.invoke(
            subgraph_input,
            config = config_schema
        )

        # Parse result
        summary = subgraph_states['summary']
        logger.info("Successfully parsed crawler subgraph output.")
        logger.debug("summary: "+str(summary))
        
        logger.debug("END node_webcrawler")
        return {
            "web_summary":summary
        }

    # def node_debug_consultant(state:State):
    #     """
    #     This function fixes errors in the generated code using information from data perception
    #     and potentially web solutions. It updates the generated code and iteration counters.
    #     """
    #     logger.debug("START node_debug_consultant")

    #     # Pass inputs
    #     error_summary = state['error_summary']
    #     generated_codeblock = state['generated_codeblock'][-1]
    #     try:
    #         web_summary = state['web_summary']
    #         logger.debug("With web summary: "+str(web_summary))
    #     except:
    #         web_summary = ""
    #         logger.debug("Without web summary")

    #     data_perception = state['data_perception']

    #     try:
    #         n_error = state['n_error']
    #     except:
    #         n_error = 0
    #     logger.info("Trying to resolve error in "+str(n_error)+" times.")

    #     n_iter = state['n_iter']
    #     logger.debug("n_iter: "+str(n_iter))

    #     # Parse human input
    #     human_input = "## Original code  \n" + generated_codeblock +"\n\n"
    #     human_input += "## Data information  \n" + data_perception +"\n\n"
    #     human_input += "## Error message  \nThe error message and related information as follow:" +"\n---\n"
    #     human_input += error_summary +"\n---\n"
    #     if len(web_summary)>1:
    #         human_input += "## Web solution  \nSearching through the web, the recommended solutions are as follows:" +"\n---\n" + web_summary
    #     logger.debug("human_input: "+str(human_input))

    #     # Call prompt template
    #     prompt, input_vars = load_prompt_template('coder.gen_fixsolut')
    #     logger.debug("prompt:"+str(prompt))

    #     # Construct input message
    #     message = [
    #         SystemMessage(content=prompt.format()),
    #         HumanMessage(content=human_input)
    #     ]

    #     # Fix code error with llm
    #     logger.info("Start code error fix consulting with LLM...")
    #     i = 0
    #     while i < max_retry: 
    #         try:
    #             print("Fixing error code.")
    #             response = code_model.invoke(message)
    #             logger.info("Successfully fixed code error.")
    #             logger.debug("error_solution: "+str(response.content))
    #             break
    #         except Exception as e:
    #             i+=1
    #             if i == max_retry:
    #                 logger.exception("Get exception when fixing code error:")
    #                 raise  
    #             else:
    #                 logger.debug("Get exception when fixing code error:\n"+str(e))
        
    #     # Update iteration 
    #     n_error += 1
    #     n_iter -= 1

    #     logger.debug("END node_debug_consultant")
    #     return {
    #         'error_solution':response.content, 
    #         'n_error':n_error,
    #         'n_iter':n_iter
    #     }

    #----------------
    # Define conditional edges
    #----------------

    def router_skip_critic(state:State):
        logger.debug("START router_skip_critic")
        if state['scrpt_type'] == 'env':
            logger.debug("SELECT executor: code block for env profiling, skil critic")
            logger.debug("END router_skip_critic")
            return "exe"
        else:
            logger.debug("SELECT critic: code block for workflow, need reflection")
            logger.debug("END router_skip_critic")
            return "critic"

    def router_is_codeblock_qualified(state:State):
        logger.debug("START router_is_codeblock_qualified")
        if state['n_iter'] < coder_config.MAX_CRITIQUE:
            if state['critique_status'] == "APPROVE":
                logger.debug("SELECT continue: code block qualified, continue to executor")
                logger.debug("END router_is_codeblock_qualified")
                return "continue"
            else:
                logger.debug("SELECT regen: code block not qualified, regen")
                logger.debug("END router_is_codeblock_qualified")
                return "regen"
        else: 
            logger.debug("SELECT continue: code block not qualified, max iteration reached, continue to executor")
            logger.debug("END router_is_codeblock_qualified")
            return "continue"
        
    def router_is_error_occur(state:State):
        logger.debug("START router_is_error_occur")
        if state['error_status']:
            logger.debug("SELECT errorfix: error occur, continue to error fix")
            logger.debug("END router_is_error_occur")
            return "errorfix"
        else:
            logger.debug("SELECT end: no error, end the wrkflow")
            logger.debug("END router_is_error_occur")
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
    builder.add_node("Webcrawler",node_webcrawler)
    #builder.add_node("Consultant",node_debug_consultant)
    # add edges
    builder.add_edge(START,"Code generation")
    builder.add_conditional_edges(
        "Code generation", 
        router_skip_critic,
        {
            "exe"  : "Executor", 
            "critic"  : "Criticism"}
        )
    #builder.add_edge("Code generation", "Criticism")
    builder.add_conditional_edges(
        "Criticism", 
        router_is_codeblock_qualified,
        {
            "continue"  : "Executor", 
            "regen"     : "Code generation"}
        )
    builder.add_conditional_edges(
        "Executor", 
        router_is_error_occur,
        {
            "errorfix"  : "Webcrawler", #"Consultant", 
            "end"       : END}
        )
    builder.add_edge("Webcrawler","Code generation")#"Consultant")
    
    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )
