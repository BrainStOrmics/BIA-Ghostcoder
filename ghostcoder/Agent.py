import ghostcoder
from ghostcoder.utils import *
from ghostcoder.graph import create_ghostcoder_agent
from ghostcoder.config import *



from typing import Type, Optional, Any
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_tavily  import TavilySearch
#langgraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
#from langgraph.types import interrupt
#plot graph
from IPython.display import Image, display
from langgraph.types import Checkpointer

class GhostCoder:
    """
    Define the state of the graph
    """
    def __init__(
        self,
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
        ) -> CompiledStateGraph:
        
        """
        
        """

        # Pass parameters 
        self.chat_model = chat_model
        self.code_model = code_model
        self.max_try = max_retry
        self.name = name
        self.config_schema = config_schema
        self.checkpointer = checkpointer
        self.store = store
        self.interrupt_before = interrupt_before
        self.interrupt_after = interrupt_after
        self.debug = debug
        
        # Initial Tavily search 
        try:
            websearch = TavilySearch(
                max_results=TAVILY_MAX_RESULTS,
                topic="general",)
        except Exception as e:
            print(f'Tavily search failed to initiate due to:\n{e}')

        # Initial agent graph
        try:
            self.graph = create_ghostcoder_agent(
                chat_model = self.chat_model,
                code_model = self.code_model,
                max_retry = self.max_try,
                name = self.name,
                config_schema = self.config_schema,
                checkpointer = self.checkpointer,
                store = self.store,
                interrupt_before = self.interrupt_before,
                interrupt_after = self.interrupt_after,
                debug = self.debug,
                )
        except Exception as e:
            print(f'GhostCoder failed to initiate dueWW to:\n{e}')
        
    
    def Run(
        self,
        task: str,
        input_wrap: dict,
        task_id: str = "test",
        update_to: str = "Global", # or local
        previous_codeblock: str = "",
        use_reg: bool = True,
        ):
        """
        """

        # Pass parameters
        self.task = task
        self.task_id = task_id
        ghostcoder.config.TASK_ID = self.task_id
        self.inputvar_names = input_wrap['var_names']
        self.persis_add = input_wrap['persis_add']
        self.data_perception = input_wrap['perception']
        self.update_to = update_to
        self.previous_codeblock = previous_codeblock
        self.use_reg = use_reg

        # Pass agent input
        agent_input = {
            "task_description": self.task,
            "inputvar_names": self.inputvar_names,
            "presis_add": self.persis_add,
            "data_perception": self.data_perception,
            "previous_codeblock": self.previous_codeblock,
            "update_to": self.update_to,
            "use_reg": self.use_reg,
            }
        
        # Run agent
        output_state = self.graph.invoke(agent_input)

        # Parse result
        codeblock = output_state['generated_codeblock']
        exe_out = output_state['execution_outstr']

        return codeblock, exe_out
    
    def draw_graph(self):
        i = 0 
        while i < self.max_try:
            try:
                display(Image(self.graph.get_graph(xray=1).draw_mermaid_png()))
                break
            except Exception as e:
                i += 1
                if i == self.max_try:
                    print(f"Error draw agent due to: \n{e}")