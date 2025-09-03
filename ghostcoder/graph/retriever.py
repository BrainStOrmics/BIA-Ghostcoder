import logging
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
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.pregel import RetryPolicy

#----------------
# Initial logging
#----------------
logger = logging.getLogger(__name__)

#----------------
# Agent orchestration
#----------------
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
    ) -> CompiledStateGraph:
    
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
    logger.info("============retriever============\nStarting retriever subagent...\n")
    logger.info("Initializing retrievers...")
    logger.debug(
        "Totally"+str(len(retriever_config.DATABASES))+" vdbs to add, they are:\n"+
        str(retriever_config.DATABASES)
        )
    for db in retriever_config.DATABASES:
        if db['name'] != 'web_crawler':
            try:
                retriever =  setup_vdbs(db['name'])
                retrievers.append(retriever)
                logger.info("Successfully add vector db:"+str(db['name']))
            except Exception as e:
                logger.exception("Get exception when adding vdb:")


    #----------------
    # Define nodes
    #----------------
    def node_chose_db(state:State):
        """
        This function generates web search queries based on the error summary using an LLM.
        """
        logger.debug("START node_chose_db")
        
        # Pass inputs
        task_description = state['task_description']
        logger.info("Input task description:\n"+str(task_description))

        # Load DB profiles, and convert to string
        db_profiles = retriever_config.DATABASES
        db_desc_str = "## Avaliable databases are:  \n---\n"
        for db in db_profiles:
            db_desc_str += "DB Name: " + db['name'] +"\n"
            db_desc_str += "DB description: " + db['description'] +"\n---\n"
        logger.debug("DB description:\n"+db_desc_str)

        # Parse human input
        human_input = "## The content of the search target is as follows:  \n" + task_description + "\n"
        human_input += db_desc_str
        logger.debug("Human input:\n"+human_input)

        # Call prompt template
        prompt, input_vars = load_prompt_template('retriever.db_router')
        logger.debug("Prompt:\n"+str(prompt))

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Chose databases with llm
        logger.info("Calling LLM to chose database...")
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                response = chain.invoke(message)
                db_use = response['DB to use']
                logger.info("LLM chose "+db_se+ "to use.")
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception when calling LLM:")
                else:
                    logger.debug("Get exception when calling LLM:\n"+str(e))

        logger.debug("END node_chose_db")
        return {
            'db_use':db_use
        }


    def node_webcrawler(state:State):
        """"""
        logger.debug("START node_webcrawler")

        # Pass inputs
        task_description = state['task_description']
        logger.debug("Given inputs:\n"+str(task_description))
        
        # Parse input
        input_str = "I need to query the web and find a reference code block that I can use based on the following task content:\n" + task_description
        logger.debug("Input to crawler subagent:\n"+input_str)

        # Call subgraph to crawl web pages
        i = 0
        logger.info("Calling crawler subagent from retriever subagent")
        while i < max_retry: 
            try:
                res = crawler_subgraph.invoke({"query_context":input_str})
                crawl_res = res["useful_results"]
                logger.info("Get "+str(len(crawl_res))+" results from crawler subagent")
                logger.debug(
                    "Crawler subgraph return:\n----------------\n"
                    +str(crawl_res)+
                    "\n----------------")
                break 
            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception when calling web crawler:")
                    raise
                else:
                    logger.debug("Get exception when calling web crawler:\n"+str(e))
        
        # Call prompt template
        prompt, input_vars = load_prompt_template('retriever.parse_webpage')
        logger.debug("Prompt:\n"+str(prompt))
        
        # Parse webpage content
        logger.info("Parsing crawled web pages.")
        webpages = []
        n_pages = 0
        for res in crawl_res:
            if 'fullpage_content' in res.keys():
                if len(res['fullpage_content']) < 100: #skip page with too few content
                    logger.debug("Parsing #"+str(n_pages+1)+" web page.")
                    continue
                # Parse human input
                logger.info("Parsing #"+str(n_pages+1)+" web page using LLM.")
                human_input = "## The original web page content:  \n" + res['fullpage_content'] + "\n"
                logger.debug("Human input:\n"+human_input)

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
                        logger.info("Successfully parse #"+str(n_pages+1)+" web page.")
                        logger.debug("Parsed content:\n"+parsed_page)
                        break
                    except Exception as e:
                        i+=1
                        if i == max_retry:
                            logger.exception("Get exception when parsing web page with LLM:")
                            raise
                        else:
                            logger.debug("Get exception when parsing web page with LLM:\n"+str(e))

                n_pages += 1
                webpages.append(parsed_page)
        logger.info("Totally parsed "+str(parsed_page)+" web pages.")

        logger.debug("END node_webcrawler")
        return {
            "crawl_res": crawl_res,
            "ref_codeblocks": webpages
        }
    
    def node_vdb_retriever(state:State):
        """
        """
        logger.debug("START node_vdb_retriever")

        # Pass inputs
        task_description = state['task_description']
        logger.debug("Given inputs:\n"+str(task_description))

        # Retrieve refcode 
        logger.info("Retrieving ref code blocks from vdbs.")
        refcodes=[]
        for retriever in retrievers:
            docs = retriever.invoke(task_description)
            logger.info("Get "+str(len(docs))+" results from"+str(retriever['name']))
            for doc in docs:
                code = doc.metadata["CodeBlock"]
                refcodes.apppend(code)
        
        logger.debug("Retrived code blocks:\n"+str(refcodes))
        logger.debug("END node_vdb_retriever")
        return {
            "ref_codeblocks": refcodes
        }


    def node_filter(state:State):
        """"""
        logger.debug("START node_filter")
        logger.info("Filtering retrieved ref code blocks.")

        # Pass inputs
        task_description = state['task_description']
        ref_codeblocks = state['ref_codeblocks']
        logger.debug("Given inputs:\n"+str(task_description))
        logger.debug("Given inputs:\n"+str(ref_codeblocks))


        # Parse code blocks
        logger.debug("Parsing ref code blocks to one str.")
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
        logger.debug("Human input:\n"+human_input)

        # Call prompt template
        prompt, input_vars = load_prompt_template('filter_retrieve')
        logger.debug("Prompt:\n"+str(prompt))

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Filter retrieve by llm
        logger.info("Calling LLM to filter retrieved code blocks...")
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry:
            try:
                json_output = chain.invoke(message)
                indexes = json_output['index']
                logger.info("Get "+str(len(indexes))+" results from LLM.")
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception when calling LLM to filter retrieved code blocks:")
                    raise
                else:
                    logger.debug("Get exception when calling LLM to filter retrieved code blocks:\n"+str(e))

        logger.info("Filtering done.")
        fin_codeblocks = []
        for idx in indexes:
            fin_codeblocks.append(ref_codeblocks[int(idx)])

        logger.debug("END node_filter")

        return {
            "ref_codeblocks": fin_codeblocks
        }

    #----------------
    # Define conditional edges
    #----------------
    def router_db(state:State):
        logger.debug("START router_db")
        # Pass inputs 
        db_use = state['db_use']
        logger.debug("Given inputs:\n"+str(db_use))
        # Router
        if db_use.lower == 'web_crawler':
            logger.debug("Router to web crawler.")
            logger.debug("END router_db")
            return "webcrawler"
        else:
            logger.debug("Router to vdb retriever.")
            logger.debug("END router_db")
            return "vectordb"
        

    def router_tryagain(state:State):
        logger.debug("START router_tryagain")
        # Pass inputs 
        ref_codeblocks = state['ref_codeblocks']
        logger.debug("Given inputs:\n"+str(ref_codeblocks))
        # Router
        if len(ref_codeblocks) < 1:
            logger.debug("No code blocks retrieved, try web crawler.")
            logger.debug("END router_tryagain")
            return "webcrawler"
        else:
            logger.debug("Code blocks retrieved, go to filter.")
            logger.debug("END router_tryagain")
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