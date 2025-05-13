from ghostcoder.utils import *
from ghostcoder.prompts import load_prompt_template
from ghostcoder.config import TAVILY_MAX_RESULTS
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
from langgraph.graph.graph import CompiledGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.pregel import RetryPolicy


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
    ) -> CompiledGraph:

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

        # Pass inputs
        query_context = state['query_context']

        # Parse human input
        human_input = "## The content of the search target is as follows:  \n" + query_context 

        # Call prompt template
        prompt, input_vars = load_prompt_template('gen_webquery')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Generate web search query with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                response = chain.invoke(message)
                query_list = response['queries']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating code: {e}")

        return {
            'query_list':query_list
        }


    def node_websearch(state:State):
        """
        This function performs web searches using the provided queries and collects results.
        """

        # Pass inputs
        query_list = state['query_list']

        # Call Tavily search 
        websearch = TavilySearch(
            max_results=TAVILY_MAX_RESULTS,
            topic="general",)

        # Get web query
        query_results = []
        for query in query_list:
            try:
                res = websearch.invoke({"query":query})
                query_results += res['results']
            except:
                print("Query with question '"+str(query)+"'... Failed.")
        
        if PRINT_WEBSEARCH_RES:
            print(query_results)

        return {
            'query_results':query_results
        }


    def node_filter_search(state:State):
        """
        This function filters the web search results using an LLM to select relevant pages.
        """

        # Pass inputs
        query_context = state['query_context']
        query_results = state['query_results']

        # Parse and index query results
        query_str = "## Queried web pages:  \n" 
        i = 0
        for qres in query_results:
            query_str+= '---\nIndex: ' + str(i) + '\n'
            query_str+= 'Title: ' + str(qres['title']) + '\n'
            query_str+= 'Web content: ' + str(qres['content']) + '\n---\n'
            i+=1

        # Parse human input
        human_input = "## The content of the search target is as follows:  \n" + query_context + '\n\n'
        human_input += query_str

        # Call prompt template
        prompt, input_vars = load_prompt_template('filter_webpage')
        
        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Filter web search with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                response = chain.invoke(message)
                query_index = response['selected_indexes']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error filter web search pages due to: {e}")
        
        # Parse filter index
        parsed_idx = []
        for idx in query_index:
            parsed_idx.append(int(idx))
        
        # Select useful results
        useful_results = []
        for idx in parsed_idx:
            useful_results.append(query_results[idx])

        return {
            'useful_results':useful_results
        }


    def node_crawler(state:State):
        """"""

        # Pass inputs 
        useful_results = state['useful_results']
        
        # Crawl from url
        crawled_webs = "## Web-based information on related issues:  \n---\n"
        j = 0
        for res in useful_results:
            i = 0 
            while i < max_retry:
                try:
                    web_content = webcontent_str_loader(res['url'])
                    if PRINT_WEBPAGE:
                        print(web_content)
                    res['fullpage_content'] = web_content
                    crawled_webs += "### Page "+str(j)+ ":  \n"
                    crawled_webs += web_content + '\n---\n'
                    j+=1
                    break
                except Exception as e:
                    i+=1
                    if i == max_retry:
                        print(f"Error crawling web pages due to: {e}")

        return {
            'useful_results':useful_results,
            'crawled_webs':crawled_webs
        }


    def node_conclude_search(state:State):
        """"""

        # Pass inputs
        query_context = state['query_context']
        crawled_webs = state['crawled_webs']
        
        # Parse human input
        human_input = "## The content of the search target is as follows: \n" + query_context + "\n\n"
        human_input += crawled_webs
        
        # Call prompt template
        prompt, input_vars = load_prompt_template('gen_websummary')
        
        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Generate web search query with llm
        i = 0
        while i < max_retry: 
            try:
                response = code_model.invoke(message)
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating code: {e}")

        return {
            'summary':response.content
        }

    #----------------
    # Define conditional edges
    #----------------

    def router_after_filter(state:State):
        # Pass inputs 
        useful_results = state['useful_results']
        
        # Router
        if len(useful_results) < 1:
            return "regen query"
        else:
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