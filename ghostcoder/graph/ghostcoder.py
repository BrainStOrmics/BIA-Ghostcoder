from ..utils import *
from ..prompts import load_prompt_template
from .coder import create_coder_agent
from .rager import create_rag_agent

from typing import TypedDict, Optional, Type, Any
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
#langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.graph import CompiledGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
from langgraph.pregel import RetryPolicy


def create_ghostcoder_agent(
    chat_model: LanguageModelLike,
    code_model: LanguageModelLike,
    *,
    max_retry = 3,
    name: Optional[str] = "ghostcoder",
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    store: Optional[BaseStore] = None,
    interrupt_before: Optional[list[str]] = None,
    interrupt_after: Optional[list[str]] = None,
    debug: bool = False,
    ) -> CompiledGraph:

    #----------------
    # TODO: Optimize agent framework
    #----------------

    #----------------
    # Define graph state
    #----------------

    class State(TypedDict):
        #input
        task_description: str
        inputvar_names: list[str]
        presis_add: str
        data_perception: str
        previous_codeblock: str
        update_to: str
        presis_add: str

        #parameter
        use_reg: bool
        
        #generated
        task_instruction: str
        ref_codeblocks: str
        generated_codeblock: str
        execution_outstr: dict


    #----------------
    # Load subgraphs
    #----------------

    # Get crawler subgraph 
    coder_subgraph = create_coder_agent(
        chat_model = chat_model, 
        code_model = code_model,
        max_retry = max_retry,
        name =  "coder_subgraph",
        config_schema = config_schema,
        checkpointer = checkpointer,
        store = store,
        interrupt_before = interrupt_before,
        interrupt_after = interrupt_after,
        debug = debug,
        )

    rager_subgraph = create_rag_agent(
        chat_model = chat_model, 
        code_model = code_model,
        max_retry = max_retry,
        name =  "reg_subgraph",
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

    def node_task_parser(state:State):
        """"""

        # Pass inputs
        task_description = state['task_description']
        previous_codeblock = state['previous_codeblock']

        # Parse human input
        human_input = "## Analysis task:  \n" + task_description + '\n\n'
        if len(previous_codeblock) > 1:
            human_input += "## Codes for previous step:  \n---------\n" + previous_codeblock + '\n---------\n'

        # Call prompt template
        prompt, input_vars = load_prompt_template('task_parse')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format()),
            HumanMessage(content=human_input)
        ]

        # Generate task instruction with llm
        i = 0
        while i < max_retry:
            try:
                response = chat_model.invoke(message)
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating task instruction: {e}")
        
        # Parse output
        task_instruction = response.content

        return {
            "task_instruction": task_instruction,
            }


    def node_ref_retriever(state:State):
        """"""

        # Pass inputs
        rager_input = {
            "task_description": state['task_description']
            }

        # Get reference using RAGer subgraph
        rager_states = rager_subgraph.invoke(
            rager_input,
            config = config_schema)
        
        # Pass output
        ref_codeblocks = rager_states['ref_codeblocks']

        return {
            "ref_codeblocks":ref_codeblocks,
            }
    
    def node_coding(state:State):
        """"""

        # Pass inputs
        coder_input = {
            "task_instruction"  : state['task_instruction'],
            "ref_codeblocks"    : state['ref_codeblocks'],
            "previous_codeblock": state['previous_codeblock'],
            "inputvar_names"    : state['inputvar_names'],
            "presis_add"        : state['presis_add'],
            "data_perception"   : state['data_perception'],
            }

        # Generate bioinformatics code with coder subgraph
        coder_state = coder_subgraph.invoke(
            coder_input,
            config = config_schema
            )

        # Pass output
        generated_codeblock = coder_state['generated_codeblock'][-1]
        execution_outstr = coder_state['execution_outstr']
        
        return {
            "generated_codeblock":generated_codeblock,
            "execution_outstr": execution_outstr
            }

    # def node_update_env(state:State)
    #     """
    #     Updates the environment with the output variables from the code execution.
    #     If obj.update_to is 'Global', updates the global scope.
    #     Otherwise, attempts to update the local scope, but this needs clarification.
    #     """
        
    #     # Pass inputs
    #     update_to = state['update_to']
    #     generated_codeblock = state['generated_codeblock']

    #     # Run code 
    #     res = trial_run(generated_codeblock, inputvars)
    #     output_vars = res['output_var']

    #     # Update env 
    #     if update_to == 'Global':
    #         globals().update(output_vars)
    #         print('Update variables and packages in global environment.')
    #     else:
    #         locals('Update variables and packages in agent runtime environment.').update(output_vars)

    #----------------
    # Define conditional edges
    #----------------
    
    def router_use_RAG(state:State):
        if state['use_reg']:
            return "RAG"
        else:
            return "continue"
        
    #----------------
    # Compile graph
    #----------------

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("Task parser", node_task_parser)
    builder.add_node("Retriever", node_ref_retriever)
    builder.add_node("Coding",node_coding)
    # builder.add_node("Update env",node_update_env)
    # add edges
    builder.add_edge(START, "Task parser")
    builder.add_conditional_edges(
        "Task parser", 
        router_use_RAG,
        {
            "RAG"       : "Retriever", 
            "continue"  : "Coding"}
        )
    builder.add_edge("Retriever","Coding")
    # builder.add_edge("Coding", "Update env")
    # builder.add_edge("Update env", END)
    builder.add_edge("Coding",END)


    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )