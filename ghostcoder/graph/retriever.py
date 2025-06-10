from ..utils import *
from ..prompts import load_prompt_template
from .webcrawler import create_crawler_agent
from ..config import *

from typing import TypedDict, Optional, Type, Any
import operator 
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import  JsonOutputParser
#langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.graph import CompiledGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.pregel import RetryPolicy


def create_retriever_agent(
    chat_model: LanguageModelLike,
    code_model: LanguageModelLike,
    *,
    max_retry = 3,
    name: Optional[str] = "retriever_subgraph",
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
        task_description: str

        #generated
        db_use: str
        crawl_res: dict 
        ref_codeblocks: list


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
    # initial retrievers
    #----------------
    retrievers = []
    for db in retriever_config.DATABASES:
        if db['name'] != 'web_crawler':
            try:
                retriever =  setup_vdbs(db['name'])
                retrievers.append(retriever)
            except Exception as e:
                print(e)


    #----------------
    # Define nodes
    #----------------
    def node_chose_db(state:State):
        """
        This function generates web search queries based on the error summary using an LLM.
        """

        # Pass inputs
        task_description = state['task_description']
        
        # Load DB profiles, and convert to string
        db_profiles = retriever_config.DATABASES
        db_desc_str = "## Avaliable databases are:  \n---\n"
        for db in db_profiles:
            db_desc_str += "DB Name: " + db['name'] +"\n"
            db_desc_str += "DB description: " + db['description'] +"\n---\n"

        # Parse human input
        human_input = "## The content of the search target is as follows:  \n" + task_description + "\n"
        human_input += db_desc_str

        # Call prompt template
        prompt, input_vars = load_prompt_template('retriever.db_router')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Chose databases with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                response = chain.invoke(message)
                db_use = response['DB to use']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error select DB: {e}")

        return {
            'db_use':db_use
        }

    def node_webcrawler(state:State):
        """"""

        # Pass inputs
        task_description = state['task_description']
        
        # Parse input
        input_str = "I need to query the web and find a reference code block that I can use based on the following task content:\n" + task_description

        # Call subgraph to crawl web pages
        i = 0
        while i < max_retry: 
            try:
                res = crawler_subgraph.invoke({"query_context":input_str})
                crawl_res = res["useful_results"]
                break 
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error invoke web crawler: {e}")
                    raise
        
        # Call prompt template
        prompt, input_vars = load_prompt_template('retriever.parse_webpage')
        
        # Parse webpage content
        webpages = []
        for res in crawl_res:
            if 'fullpage_content' in res.keys():
                if len(res['fullpage_content']) < 100: #skip page with too few content
                    continue
                # Parse human input
                human_input = "## The original web page content:  \n" + res['fullpage_content'] + "\n"

                # Construct input message
                message = [
                    SystemMessage(content=prompt.format()),
                    HumanMessage(content=human_input)
                ]
                i = 0
                while i < max_retry: 
                    try:
                        response = chat_model.invoke(message)
                        parsed_page = response.content
                        break
                    except Exception as e:
                        i+=1
                        if i == max_retry:
                            print(f"Error parse web page due to: {e}")
                            raise

                webpages.append(parsed_page)

        return {
            "crawl_res": crawl_res,
            "ref_codeblocks": webpages
        }
    
    def node_vdb_retriever(state:State):
        """
        """

        # Pass inputs
        task_description = state['task_description']
        
        # Retrieve refcode 
        refcodes=[]
        for retriever in retrievers:
            docs = retriever.invoke(task_description)
            for doc in docs:
                code = doc.metadata["CodeBlock"]
                refcodes.apppend(code)

        return {
            "ref_codeblocks": refcodes
        }


    def node_filter(state:State):
        """"""

        # Pass inputs
        task_description = state['task_description']
        ref_codeblocks = state['ref_codeblocks']

        # Parse code blocks
        ref_code_str = "## Retrieved code blocks are:\n---\n"
        i = 0
        for blk in ref_codeblocks:
            ref_code_str += "Code block with index "+ str(i) +":\n"
            ref_code_str += str(blk) 
            ref_code_str += "\n---\n"
            i+=1

        # Parse human input
        human_input = "## The bioinformatic task is:  \n" + task_description + "\n\n"
        human_input += ref_code_str

        # Call prompt template
        prompt, input_vars = load_prompt_template('filter_retrieve')


        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Filter retrieve by llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry:
            try:
                json_output = chain.invoke(message)
                indexes = json_output['index']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error filter retrieve due to: {e}")
                    raise

        fin_codeblocks = []
        for idx in indexes:
            fin_codeblocks.append(ref_codeblocks[int(idx)])

        return {
            "ref_codeblocks": fin_codeblocks
        }

    #----------------
    # Define conditional edges
    #----------------
    def router_db(state:State):
        # Pass inputs 
        db_use = state['db_use']
        
        # Router
        if db_use.lower == 'web_crawler':
            return "webcrawler"
        else:
            return "vectordb"
        

    def router_tryagain(state:State):
        # Pass inputs 
        ref_codeblocks = state['ref_codeblocks']
        
        # Router
        if len(ref_codeblocks) < 1:
            return "webcrawler"
        else:
            return "filter"

    
    #----------------
    # Compile graph
    #----------------

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("DB router", node_chose_db)
    builder.add_node("Web Crawler", node_webcrawler)
    builder.add_node("Retriever", node_vdb_retriever)
    builder.add_node("Filter", node_filter)
    # add edges
    builder.add_edge(START, "DB router")
    builder.add_conditional_edges(
        "DB router", 
        router_db,
        {
            "webcrawler": "Web Crawler", 
            "vectordb"  : "Retriever"}
        )
    builder.add_conditional_edges(
        "Retriever", 
        router_tryagain,
        {
            "webcrawler": "Web Crawler", 
            "filter"    : "Filter"}
        )

    builder.add_edge("Filter", END)
    
    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )