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


def create_planner_agent(
    chat_model: LanguageModelLike,
    code_model: LanguageModelLike,
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

    #----------------
    # Define graph state
    #----------------

    class State(TypedDict):
        #input
        user_input: str
        guidelines: list 
        data_dir: str
        
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

    def node_guideline_webcrawler(state:State):
        # Pass inputs
        user_input = state['user_input']
        websearch = state['websearch']

        # Parse input
        query = "Please provide a guide line for "+user_input 

        subgraph_input = {
            "query_context": query
        }

        if websearch:
            # Get error fix web search solution by subgraph
            subgraph_states = crawler_subgraph.invoke(
                subgraph_input,
                config = config_schema
            )

            # Parse result
            summary = subgraph_states['summary']
        
        else: summary = ""

        return {
            "web_summary":summary
        }

    def planner(state:State):
        # Pass inputs
        user_input = state['user_input']
        web_summary = state['web_summary']
        guidelines = state['guidelines']
        data_dir = state['data_dir']
        try:
            critique = state['critique']
        except:
            critique = ""
        try:
            last_plan = state['plan'][-1]
        except:
            last_plan = ""

        try:
            n_iter = state['n_iter']
        except:
            n_iter = 0

        # Parse inputs
        guideline_str = ""
        if len(critique) >0: # if there is critique, no guideline needed
            human_input = "You've previously generated a plan, and now you want to iteratively optimize your previous plan based on others criticisms of your plan:"
            human_input += "## Previous plan:\n\n" + last_plan + "\n"
            human_input += "## Critique on your previous from others:\n\n" + critique + "\n"
            
        else:
            if len(guidelines) > 0:
                guideline_str += "## Reference guideline(s) for given objective.\n\n"
                for gdl in guidelines:
                    guideline_str+= gdl + '\n\n'
            if len(web_summary) > 0:
                guideline_str += "## Reference guideline(s) for given objective, from web search.\n\n"
                guideline_str+= web_summary + '\n\n'
            human_input = guideline_str


        data_files_str = "## Data files for given objective are:\n\n"
        for fn in os.listdir(data_dir):
            data_files_str += fn + "\n"
            data_files_str += "\n"

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
        
        # Generate bioinformatic analysis plan
        i = 0
        while i < max_retry: 
            try:
                response = chat_model.invoke(message)
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generate analysis pipeline: {e}")
                    raise
    
        # Update iteration 
        n_iter += 1

        return {
            'plan': [response.content] ,
            'n_iter': n_iter
        }


    def node_criticism(state:State):
        """
        """
        # Pass inputs
        user_input = state['user_input']
        plan = state['plan'][-1]
        
        # Parse human input
        human_input = "## Plan to be reviewed\n\n" + plan + "\n"

        # Call prompt template
        prompt, input_vars = load_prompt_template('planer.critisim')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(objective = user_input)),
            HumanMessage(content=human_input)
        ]

        # Generate critique with llm
        chain = chat_model | JsonOutputParser()
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


    def node_splitter(state:State):
        """
        """
        # Pass inputs
        plan = state['plan'][-1]
        
        # Parse human input
        human_input = "## Plan to be splitted\n\n" + plan + "\n"

        # Call prompt template
        prompt, input_vars = load_prompt_template('planer.split')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Generate critique with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                plan_list = chain.invoke(message)
                
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error split due to: \n{e}")
                    raise  

        return {
            'splited_tasks':plan_list,
        }
    


    #----------------
    # Define conditional edges
    #----------------

    def router_is_plan_qualified(state:State):
        if state['n_iter'] < planner_config.MAX_CRITIQUE:
            if state['critique_status']:
                return "continue"
            else:
                return "regen"
        else: 
            return "continue"
        
    #----------------
    # Compile graph
    #----------------
    
    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("Web crawl", node_guideline_webcrawler)
    builder.add_node("Gen plan", planner)
    builder.add_node("Critique",node_criticism)
    builder.add_node("Split",node_splitter)
    # add edges
    builder.add_edge(START, "Web crawl")
    builder.add_edge("Web crawl", "Gen plan")
    builder.add_edge("Gen plan", "Critique")
    builder.add_conditional_edges(
        "Critique",
        router_is_plan_qualified,
        {
            "continue"   : "Split",
            "regen"      : "CGen plan"
        }
    )
    builder.add_edge("Split", END)

    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )