from ..utils import *
from ..prompts import load_prompt_template
from .webcrawler import create_crawler_agent
from ..config import *

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



def create_taskspliter_agent(
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
        input_task: str
        
        #parameter
        n_iter: int 

        #generated
        guideline: str
        splitted_tasks: list[str]
        grade: str
        critique: str 
        

    #----------------
    # Define nodes
    #----------------
    
    def node_gen_guideline():
        """
        """

        # Pass inputs
        input_task = state['input_task']

        # Call prompt template
        prompt, input_vars = load_prompt_template('script_gen')

        # Load and parse all guidelines
        guidelines = load_all_guidelines()
        guidelines_str = ""
        for gl in guidelines:
            guidelines_str += 

        # Parse human input
        human_input = "## " + guidelines_str

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Select guideline by llm
        i = 0
        while i < max_retry: 
            try:
                response = chat_model.invoke(message)
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generate guideline due to: \n{e}")

        return {
            "guideline": response.content,
        }


    def node_task_splitter(state:State):
        """
        """

        # Pass inputs
        input_task = state['input_task']
        guideline = state['guideline']
        critique = state['critique']
        n_iter = state['n_iter']

        # Call prompt template
        prompt, input_vars = load_prompt_template('script_gen')
        
        # Parse human input
        human_input = "## " +

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Select guideline by llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                json_output = chain.invoke(message)
                splitted_tasks = json_output['splitted tasks']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating critique due to: \n{e}")

        # Update iteration count
        n_iter += 1

        return{
            'splitted_tasks': splitted_tasks,
            'n_iter': n_iter
        }

    def node_split_grader(state:State):
        """
        """

        # Pass inputs
        splitted_tasks = state['splitted_tasks']
        

        # Parse human input
        human_input = "## " + 

        # Call prompt template
        prompt, input_vars = load_prompt_template('script_gen')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Grade task split with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry:
            try:
                json_output = chain.invoke(message)
                grade = json_output['grade']
                critique = json_output['critique']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error grade task split due to: {e}")
            
        return {
            'grade':grade,
            'critique':critique
        }

    #----------------
    # Define conditional edges
    #----------------
    def router_maxiter(state:State):
        if state['n_iter'] > MAX_SPILT_ITER:
            return "end"
        else:
            return "continue"
            
    def router_grade(state:State):
        if state['grade']:
            return "end"
        else:
            return "resplit"
        
    #----------------
    # Compile graph
    #----------------

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("Gen Guideline", node_gen_guideline)
    builder.add_node("Task splitter", node_task_splitter)
    builder.add_node("Grader",node_split_grader)

    # add edges
    builder.add_edge(START, "Gen Guideline")
    builder.add_edge("Gen Guideline", "Task splitter")
    builder.add_conditional_edges(
        "Task splitter", 
        router_grade,
        {
            "end"       : END, 
            "continue"   : "Grader"}
        )
    builder.add_conditional_edges(
        "Grader", 
        router_grade,
        {
            "end"       : END, 
            "resplit"   : "Task splitter"}
        )
    
    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )
