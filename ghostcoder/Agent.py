from typing import TypedDict, Annotated, Optional
#from anndata._core.anndata import AnnData
import operator 
#langchain
from langchain_openai.chat_models.base import ChatOpenAI
from langchain.prompts import  PromptTemplate
from langchain_core.output_parsers import  JsonOutputParser, StrOutputParser
#langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.pregel import RetryPolicy
from langgraph.types import Send
#from langgraph.types import interrupt
#plot graph
from IPython.display import Image, display
#for parallel
from functools import partial
from concurrent.futures import ThreadPoolExecutor, as_completed
#for prompt
from .prompts import load_prompt_template

#----------------------------------------------------------------
#Define state for graph
class GraphState(TypedDict):
    """
    Define the state of the graph
    """
