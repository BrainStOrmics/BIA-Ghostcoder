import logging
from ghostcoder.utils import *
from ghostcoder.prompts import load_prompt_template
from ghostcoder.config import tavily_config, crawler_config
from ..config import *


from typing import TypedDict, Optional, Type, Any
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

#----------------
# Initial logging
#----------------
logger = logging.getLogger(__name__)

#----------------
# Agent orchestration
#----------------
def create_crawler_agent(
    chat_model: LanguageModelLike,
    code_model: LanguageModelLike,
    *,
    max_retry = 3,
    name: Optional[str] = "crawler_subgraph",
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
        query_context: str

        #generated
        query_list: list[str]
        query_results: list[dict]
        useful_results: list[dict]
        crawled_webs: str
        summary: str

    #----------------
    # Define nodes
    #----------------

    def node_generate_query(state:State):
        """
        This function generates web search queries based on the error summary using an LLM.
        """
        logger.debug("START node_generate_query")
        logger.info("============web crawler============\nStarting web crawler subagent...\n")

        # Pass inputs
        query_context = state['query_context']
        logger.debug("Given inputs:\n"+str(query_context))

        # Parse human input
        human_input = "##  The content of the search purpose:  \n" + query_context 
        logger.debug("Human input:\n"+str(human_input))

        # Call prompt template
        prompt, input_vars = load_prompt_template('crawler.gen_webquery')
        logger.debug("Prompt:\n"+str(prompt))

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(
                n_queries = int(crawler_config.N_QUERIES)
                )
                ),
            HumanMessage(content=human_input)
        ]

        # Generate web search query with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                response = chain.invoke(message)
                query_list = response['queries']
                logger.info("Generated web search queries:\n"+str(query_list))
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception when generating web search queries:")
                    raise
                else:
                    logger.debug("Get exception when generating web search queries:\n"+str(e))
        
        logger.debug("END node_generate_query")
        return {
            'query_list':query_list
        }


    def node_websearch(state:State):
        """
        This function performs web searches using the provided queries and collects results.
        """
        logger.debug("START node_websearch")   

        # Pass inputs
        query_list = state['query_list']
        logger.debug("Given inputs:\n"+str(query_list))

        # Set up Tavily key
        os.environ["TAVILY_API_KEY"] = tavily_config.API_KEY
        logger.debug("Tavily API key set as:"+tavily_config.API_KEY)

        # Call Tavily search 
        logger.info("Start web search using Tavily...")
        websearch = TavilySearch(
            max_results=tavily_config.MAX_RESULTS,
            topic="general",)
        logger.info("Queried Tavily search results.")

        # Get web query
        query_results = []
        for query in query_list:
            try:
                logger.debug("Query with question '"+str(query)+"'...")
                res = websearch.invoke({"query":query})
                if 'results' in res.keys():
                    query_results += res['results']
                    logger.debug("Get "+str(len(res['results']))+" results.")
            except Exception as e:
                logger.exception("Get exception when querying with Tavily.")
                raise
        
        if crawler_config.PRINT_WEBSEARCH_RES:
            logger.debug("Print query results")
            print(query_results)

        logger.debug("END node_websearch")
        return {
            'query_results':query_results
        }


    def node_filter_search(state:State):
        """
        This function filters the web search results using an LLM to select relevant pages.
        """
        logger.debug("START node_filter_search")

        # Pass inputs
        query_context = state['query_context']
        query_results = state['query_results']

        # Parse and index query results
        logger.info("Parsing query results")
        query_str = "## Queried web pages:  \n" 
        i = 0
        for qres in query_results:
            query_str+= '---\nIndex: ' + str(i) + '\n'
            query_str+= 'Title: ' + str(qres['title']) + '\n'
            query_str+= 'Web content: ' + str(qres['content']) + '\n---\n'
            i+=1

        # Parse human input
        human_input = "## The content of the search purpose:  \n" + query_context + '\n\n'
        human_input += query_str
        logger.debug("Human input:\n"+str(human_input))

        # Call prompt template
        prompt, input_vars = load_prompt_template('crawler.filter_webpage')
        logger.debug("Prompt:\n"+str(prompt))

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(
                n_top_res = str(crawler_config.N_TOP_RES))),
            HumanMessage(content=human_input)
        ]

        # Filter web search with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                response = chain.invoke(message)
                query_index = response['selected_indexes']
                logger.info("Filtered web search results, selected indexes:\n"+str(query_index))
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception when filtering web search pages:")
                    raise
                else:
                    logger.debug("Get exception when filtering web search pages:\n"+str(e))
        
        # Parse filter index
        parsed_idx = []
        logger.debug("Filtered web search results, selected indexes:\n"+str(query_index))
        for idx in query_index:
            parsed_idx.append(int(idx))
        
        # Select useful results
        useful_results = []
        logger.debug("Selected indexes:\n"+str(parsed_idx))
        for idx in parsed_idx:
            useful_results.append(query_results[idx])
        logger.info("Selected web search results:\n"+str(useful_results))

        logger.debug("END node_filter_search")
        return {
            'useful_results':useful_results
        }


    def node_crawler(state:State):
        """
        """
        logger.debug("START node_crawler")

        # Pass inputs 
        useful_results = state['useful_results']

        # Crawl from url
        logger.info("Start crawling web pages...")
        crawled_webs = "## Crawled web pages:  \n---\n"
        j = 0
        for res in useful_results:
            i = 0 
            while i < max_retry:
                try:
                    web_content = webcontent_str_loader(res['url'])
                    if crawler_config.PRINT_WEBPAGE:
                        print(web_content)
                    res['fullpage_content'] = web_content
                    crawled_webs += "### Page "+str(j)+ ":  \n"
                    crawled_webs += web_content + '\n---\n'
                    j+=1
                    logger.debug("Crawled web page "+str(j)+":\n"+web_content)
                    break
                except Exception as e:
                    i+=1
                    if i == max_retry:
                        logger.exception("Get exception when crawling web pages:")
                        raise
                    else:
                        logger.debug("Get exception when crawling web pages:\n"+str(e))

        logger.info("Crawled total "+str(j)+" web pages.")

        logger.debug("END node_crawler")

        return {
            'useful_results':useful_results,
            'crawled_webs':crawled_webs
        }


    def node_conclude_search(state:State):
        """
        """
        logger.debug("START node_conclude_search")

        # Pass inputs
        query_context = state['query_context']
        crawled_webs = state['crawled_webs']
        
        # Parse human input
        human_input = "## The content of the search purpose: \n" + query_context + "\n\n"
        human_input += crawled_webs
        logger.debug("Human input:\n"+str(human_input))
        
        # Call prompt template
        prompt, input_vars = load_prompt_template('crawler.gen_websummary')
        logger.debug("Prompt:\n"+str(prompt))

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Generate web search query with llm
        logger.info("Start generating web search summary...")
        i = 0
        while i < max_retry: 
            try:
                response = chat_model.invoke(message)
                logger.info("Generated web search summary:\n"+str(response.content))
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    logger.exception("Get exception when generating web search summary:")
                    raise
                else:
                    logger.debug("Get exception when generating web search summary:\n"+str(e))
        
        logger.debug("END node_conclude_search")
        return {
            'summary':response.content
        }

    #----------------
    # Define conditional edges
    #----------------

    def router_after_filter(state:State):
        logger.debug("START router_after_filter")
        # Pass inputs 
        useful_results = state['useful_results']
        logger.debug("useful_results:\n"+str(useful_results))
        # Router
        if len(useful_results) < 1:
            logger.info("No useful results, regen query.")
            logger.debug("END router_after_filter")
            return "regen query"
        else:
            logger.info("Has useful results, continue to crawl.")
            logger.debug("END router_after_filter")
            return "continue"
        
    #----------------
    # Compile graph
    #----------------
    
    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("Generate query", node_generate_query)
    builder.add_node("Web search", node_websearch)
    builder.add_node("Filter search",node_filter_search)
    builder.add_node("Crawl webpage",node_crawler)
    builder.add_node("Conclude",node_conclude_search)
    # add edges
    builder.add_edge(START, "Generate query")
    builder.add_edge("Generate query", "Web search")
    builder.add_edge("Web search", "Filter search")
    builder.add_conditional_edges(
        "Filter search",
        router_after_filter,
        {
            "regen query"   : "Generate query",
            "continue"      : "Crawl webpage"
        }
    )
    builder.add_edge("Crawl webpage", "Conclude")
    builder.add_edge("Conclude", END)

    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )