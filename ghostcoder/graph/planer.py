from ghostcoder.utils import *
from ghostcoder.prompts import load_prompt_template
from ghostcoder.config import tavily_config, crawler_config
from ..config import *

from typing import TypedDict, Optional, Type, Any, Annotated
import operator 
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import  JsonOutputParser
from langchain_tavily  import TavilySearch
#langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.pregel import RetryPolicy
from langgraph.types import interrupt 

#----------------
# Initial logging
#----------------
logger = logging.getLogger(__name__)

#----------------
# Agent orchestration
#----------------
def create_planner_agent(
    chat_model: LanguageModelLike,
    reason_model: LanguageModelLike,
    HILT: bool = False,
    *,
    max_retry = 3,
    name: Optional[str] = "planner_subgraph",
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    store: Optional[BaseStore] = None,
    interrupt_before: Optional[list[str]] = None,
    interrupt_after: Optional[list[str]] = None,
    debug: bool = False,
    ) -> CompiledStateGraph:

    if HILT:
        interrupt_before = ["node_user_feedback"]

    #----------------
    # Define graph state
    #----------------

    class State(TypedDict):
        #input
        user_input: str
        guidelines: list # [optional], better use list format
        data_dir: str # [optional], default use 
        max_iter: int # [optional], default use planner_config.MAX_CRITIQUE
        
        #parameter
        n_iter: int
        websearch: bool

        #generated
        web_summary: str
        plan: Annotated[list[str], operator.add]
        critique_status: bool
        critique: str
        splited_tasks: list[str]
    
    #----------------
    # Load subgraphs
    #----------------
    # Get crawler subgraph 
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
    
    #----------------
    # Define nodes
    #----------------

    def node_guideline_fetcher(stat:State):
        """"""
        logger.debug("START node_guideline_fetcher")
        logger.infor("============planner============\nStarting planner subagent...\n")
        # Pass inputs
        user_input = state['user_input']

        try:
            max_iter = state['max_iter']
        except:
            max_iter = planner_config.MAX_CRITIQUE
        
        try:
            websearch = state['websearch']
        except:
            websearch = False #Set not use websearch as default

        try:
            guidelines = state['guidelines']
            logger.debug("User provided guidelines.")
        except:
            guidelines = []
            logger.debug("User not provided guidelines.")
        logger.debug("User input: "+str(user_input))
        logger.debug("User webserach"+str(websearch))

        # Use provided guidelines
        guideline_str = "### Guidelines:\n"
        if len(guidelines) > 0:
            logger.info("Use user provided guideline")
            if type(guidelines) == list:
                n = 0
                for g in guidelines: 
                    guideline_str += "#### Guideline #"+str(n)+":\n"
                    guideline_str += g + '\n'
            elif type(guidelines) == str:
                guideline_str += guidelines + '\n'

        # Or fetch guidelines from web and reformat guideline
        else: 
            if websearch:
                logger.info("Fetch guideline from web search.")
                # Get error fix web search solution by subgraph
                subgraph_states = crawler_subgraph.invoke(
                    subgraph_input,
                    config = config_schema
                )

                # Parse result
                summary = subgraph_states['summary']
            else: 
                summary = ""
                logger.infor("Use no web search.")
            # Prepare LLM
            # Call prompt template
            prompt, input_vars = load_prompt_template('coder.script_gen')
            logger.debug("prompt:"+str(prompt))
            # Format LLM input
            if len(summary) > 0:
                human_input = "## References from web search as follow:\n" + summary
            else:
                human_input = "## No web search available\nPlease gen guildeline based on your knowledge"
            message = [
                SystemMessage(content=prompt.format(
                    user_input = user_input)),
                HumanMessage(content=human_input)
            ]
            # Generate guideline with LLM
            # Construct LLM chain
            chain = reason_model | JsonOutputParser()
            # Invoke LLM with retry
            i = 0
            logger.infor("Start reformat workflow guideline with LLM...")
            while i < max_retry:
                try:
                    response = chain.invoke(message)
                    guideline_str = response['guideline_markdown']
                    logger.info("Successfully reformat guideline.")
                    logger.debug("generated guideline: "+str(guideline_str))
                    break
                except Exception as e:
                    i+=1
                    if i == max_retry:
                        logger.exception("Get exception when reformat guideline:")
                        raise  
                    else:
                        logger.debug("Get exception when reformat guideline:\n"+str(e))

        # Return
        return {
            "max_iter": max_iter
            "guidelines": guideline_str,
        }

    def node_planner(state:State):
        """"""
        logger.info("START node_planner")
        # Pass inputs
        user_input = state['user_input']
        guidelines = state['guidelines']

        try:
            data_dir = state['data_dir']
            logger.info("Use defined data dir:"+str(data_dir))
        except:
            # Use default data dir 
            data_dir = str(file_config.DATA_DIR)
            logger.info("Use default data dir"+str(data_dir))

        try:
            critique = state['critique']
            logger.debug("Got critique:"+str(critique))
        except:
            critique = ""
            logger.debug("No critique, yet")

        try:
            old_plan = state['plan'][-1]
            logger.debug("Refine plan with last generated.")
        except:
            old_plan = ""
            logger.debug("Generate new plan")

        try:
            n_iter = state['n_iter']
        except:
            n_iter = 0
        logger.info("Start #"+str(n_iter)+" iteration of analysis workflow plan generation")

        # Parse inputs
        # Parse data file 
        data_files_str = "## Data files for given objective are:\n\n"
        for fn in os.listdir(data_dir):
            data_files_str += fn + "\n"
            data_files_str += "\n"
        logger.debug("Data files for given objective are:\n\n"+data_files_str)

        # Parse guidelines
        guideline_str = ""
        if len(guidelines) > 0:
            human_input += "## Reference guideline(s) for given objective.\n" + guidelines + "\n"
        
        # Parse critique
        if len(critique) >0: # if there is critique, no guideline needed
            human_input = "You've previously generated a plan, and now you want to iteratively optimize your previous plan based on others criticisms of your plan:"
            human_input += "## Previous plan:\n\n" + old_plan + "\n"
            human_input += "## Critique on your previous from others:\n\n" + critique + "\n"

        # Generate analysis workflow plan with LLM
        # Call prompt template
        prompt, input_vars = load_prompt_template('planer.gen_plan')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(
                objective = user_input,
                data_files = data_files_str
                )),
            HumanMessage(content=human_input)
        ]

        # Construct LLM chain 
        chain = reason_model | JsonOutputParser()
        
        # Generate bioinformatic analysis plan
        i = 0
        while i < max_retry: 
            try:
                response = chain.invoke(message)
                plan = response['plan_markdown']
                logger.info("Successfully generate analysis workflow plan:\n"+str(plan))
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generate analysis workflow plan: {e}")
                    raise
    
        # Update iteration 
        n_iter += 1

        # Return 
        return {
            'plan': [plan] ,
            'n_iter': n_iter
        }


    def node_criticism(state:State):
        """
        """
        # Pass inputs
        user_input = state['user_input']
        plan = state['plan'][-1]
        
        # Parse human input
        human_input = "## Plan to be evaluated\n" + plan

        # Call prompt template
        prompt, input_vars = load_prompt_template('planer.critisim')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(objective = user_input)),
            HumanMessage(content=human_input)
        ]

        # Generate critique with llm
        chain = reason_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                json_output = chain.invoke(message)
                critique_status = json_output['qualified']
                critique = json_output['self_critique']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating critique due to: \n{e}")
                    raise  

        return {
            'critique_status':critique_status, 
            'critique': critique
        }

    def node_user_feedback(state:State):
        """"""
        # Parse inputs
        logger.debug("START node_user_feedback")
        # Get HITL input
        if HILT:
            logger.info("Use HITL input, use user input as critique.")
            try:
                human_response = interrupt(
                    {
                        "Please input your feedback on the plan here(n for no feedback and approve the plan):\n":state["plan"][-1]
                    })
                logger.debug("HITL feedback received.")
                if human_response.lower().is.in(['n','no','nope','','skip','not','none']):
                    critique_status = "APPROVED"
                    logger.debug("User approved to plan, continue.")
                else: 
                    try:
                        critique_status = "REVISIONS_REQUIRED"
                        # Parse critique
                        critique = "User provided following feedback on your plan:\n" + human_response
                        logger.debug("User feedback successfully parsed")
                    except:
                        critique_status = "APPROVED"
                        logger.debug("Failed to parse user feedback, skip this step.")
            except:
                logger.debug("No HITL feed back received, use default no feedback.")
        else:
            critique_status = "APPROVED"
            logger.info("No HITL input, skip this step.")

        # Return 
        return {
            'critique_status':critique_status, 
            'critique': critique, 
        }



    # def node_splitter(state:State):
    #     """
    #     """
    #     # Pass inputs
    #     plan = state['plan'][-1]
        
    #     # Parse human input
    #     human_input = "## Plan to be splitted\n\n" + plan + "\n"

    #     # Call prompt template
    #     prompt, input_vars = load_prompt_template('planer.split')

    #     # Construct input message
    #     message = [
    #         SystemMessage(content=prompt.format()),
    #         HumanMessage(content=human_input)
    #     ]

    #     # Generate critique with llm
    #     chain = chat_model | JsonOutputParser()
    #     i = 0
    #     while i < max_retry: 
    #         try:
    #             plan_list = chain.invoke(message)
                
    #             break
    #         except Exception as e:
    #             i+=1
    #             if i == max_retry:
    #                 print(f"Error split due to: \n{e}")
    #                 raise  

    #     return {
    #         'splited_tasks':plan_list,
    #     }
    


    #----------------
    # Define conditional edges
    #----------------

    def router_is_plan_qualified(state:State):
        logger.debug("START router_is_plan_qualified")
        if state['n_iter'] < state['max_iter']:
            if state['critique_status'] == "APPROVED":
                logger.debug("Plan qualified, continue to human feedback.")
                return "continue"
            else:
                logger.debug("Plan not qualified, continue.") 
                return "regen"
        else:
            logger.debug("Max critique iteration reached, continue to human feedback.") 
            return "continue"
    
    def router_is_human_approve(state:State):
        logger.debug("START router_is_human_approve")
        if state["critique_status"] == "APPROVED":
            logger.debug("Plan approved, end agent.")
            return "end"
        else:
            logger.debug("Plan not approved, reversion.")
            return "regen"

    #----------------
    # Compile graph
    #----------------
    
    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("Guideline fetcher", node_guideline_fetcher)
    builder.add_node("Planner", node_planner)
    builder.add_node("Critique",node_criticism)
    builder.add_node("Feedback",node_user_feedback)
    # add edges
    builder.add_edge(START, "Guideline fetcher")
    builder.add_edge("Guideline fetcher", "Planner")
    builder.add_edge("Planner", "Critique")
    builder.add_conditional_edges(
        "Critique",
        router_is_plan_qualified,
        {
            "continue"   : "Feedback",
            "regen"      : "Planner"
        }
    )
    builder.add_conditional_edges(
        "Feedback",
        router_is_human_approve,
        {
            "end"   : END,
            "regen"      : "Planner"
        }
    )

    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )