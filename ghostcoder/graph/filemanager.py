import logging
from ..utils import *
from ..prompts import load_prompt_template
from ..config import *
from .coder import create_coder_agent, ghostcoder_config
from ..docker import *
#from venv import logger

from typing import TypedDict, Annotated, Optional, Type, Any
import operator 
#langchain
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
#langgraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.pregel import RetryPolicy
#from langgraph.types import interrupt

#----------------
# Initial logging
#----------------
logger = logging.getLogger(__name__)


#----------------
# Agent orchestration
#----------------
def create_filemanager_agent(
    chat_model: LanguageModelLike,
    code_model: LanguageModelLike,
    *,
    max_retry = 3,
    name: Optional[str] = "filemanager_subgraph",
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
        session_id: str
        task_id: str
        # docker_files_dir: str # Moved to config
        
        #parameter
        n_iter: int
        max_iter: int

        #generated
        env_profiles: dict 
        data_files: list[str] 
        # data_perc_task: Annotated[list[str], operator.add] # Removed function
        # data_perc_code: str # Removed function
        # data_perc: str # Removed function
        # qualified: str # Removed function
        # reflex: str # Removed function

    #----------------
    # Define nodes
    #----------------

    def node_file_management(state:State):
        """
        """
        logger.debug("START node_file_management")
        logger.info("============file manager============\nStarting filemanager subagent...\n")
        # Pass input 
        try:
            task_home = file_config.WORK_HOME
        except:
            task_home = ''

        try:
            input_data_dir = file_config.INPUT_DATA_DIR
        except:
            input_data_dir = ''

        try:
            session_id = state['session_id']
            ghostcoder_config.SESSION_ID = session_id
        except:
            session_id = ''

        try:
            task_id = state['task_id']
            ghostcoder_config.TASK_ID = task_id
        except:
            session_id = ''

            
        if len(task_home) < 1: # When use default TASK_HOME
            task_home = os.path.join(os.getcwd(),session_id,task_id) # Default to current dir
            file_config.WORK_HOME = task_home

        if len(input_data_dir) < 1: # When use default INPUT_DATA_DIR
            input_data_dir = os.path.join(os.getcwd(), 'data') # Default to current dir
            file_config.INPUT_DATA_DIR = input_data_dir

        logger.debug(
            "Given inputs:\n----------------\n"+
            "task_home"+str(task_home)+
            "session_id:"+str(session_id)+
            "\ntask_id:"+str(task_id)+
            "\n----------------",
            )

        # Check work dir
        logger.info(
            "Creating file paths..."
            )
        if not check_dir_exists(task_home):
            create_dir(task_home)
            logger.info(
            "Created work home path as"+str(task_home)
            )
        file_config.DATA_DIR = os.path.join(task_home,file_config.DATA_FILENAME)
        file_config.FIGURE_DIR = os.path.join(task_home,file_config.FIGURE_FILENAME)
        file_config.OUTPUT_DIR = os.path.join(task_home,file_config.OUTPUT_FILENAME)
        for fname in [
            file_config.DATA_DIR, 
            file_config.FIGURE_DIR, 
            file_config.OUTPUT_DIR]:
            if not check_dir_exists(dir_):
                create_dir(dir_)
                logger.info(
                "Created sub path"+str(dir_)
                )
        
        # Copy data 
        logger.info(
        "Copying data files to task dir..."
        )
        data_files = copy_files(file_config.INPUT_DATA_DIR,file_config.DATA_DIR, )
        logger.info(
        "Copied data files to task "+str(data_files)
        )
        
        logger.info(
        "File management done."
        )

        logger.debug("END node_file_management")
        return {
            "data_files": data_files,
            "env_profiles": env_profiles,
        }
    
    def env_perception(state:State):
        """
        """
        logger.debug("START env_perception")
        

        env_profiles = get_env_profiles()
        logger.debug(
            "Detailed env profiles:\n--------env profiles--------\n"+
            str(env_profiles)+
            "\n----------------",
            )
        
        logger.info(
        "Perceived env profiles..."
        )

        # Check docker status perception 
        docker_status_str = get_docker_status()
        env_profiles['docker status'] = docker_status_str
        logger.debug("Docker status:"+str(docker_status_str))

        # Check native env profiles 
        native_env_profile = get_native_env_perception()
        # Pass to env_profiles 
        env_profiles['native env languages'] = "Language installed in native env and their versions are:\n"+str(native_env_profile) + "\n"
        logger.debug("Native env status:"+str(native_env_profile))

        logger.info(
        "Env perception done."
        )
        logger.info("End filemanager subagent...\n============file manager============\n")

        logger.debug("END env_perception")
        return {
            "env_profiles": env_profiles,
        }

        
    #----------------
    # Compile graph
    #----------------

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("File management", node_file_management)
    builder.add_node("Env perception", env_perception)


    # add edges
    builder.add_edge(START, "File management")
    builder.add_edge("File management",END)

    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )