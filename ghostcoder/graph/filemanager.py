from ..utils import *
from ..prompts import load_prompt_template
from ..config import *
from .coder import create_coder_agent
from ..docker import *

import docker

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
    ) -> CompiledGraph:

    #----------------
    # Define graph state
    #----------------

    class State(TypedDict):
        #input
        task_id: str
        docker_files_dir: str
        
        #parameter
        n_iter: int
        max_iter: int

        #generated
        data_files: list[str]
        env_profiles: dict
        data_perc_task: Annotated[list[str], operator.add]
        data_perc_codes: Annotated[list[str], operator.add]
        data_perc: str
        data_perc_reflex: str
        data_perc_status: str

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

    #----------------
    # Define nodes
    #----------------

    def node_file_management(state:State):
        """
        """

        # Pass input 
        task_id = state['task_id']

        # Check work dir
        work_data_dir = os.path.join(file_config.WORK_DIR,file_config.INPUT_DATA_DIR)

        task_dir = os.path.join(file_config.WORK_DIR,task_id)
        if not check_dir_exists(task_dir):
            create_dir(task_dir)
        task_data_dir = os.path.join(task_dir, file_config.DATA_DIR)
        task_fig_dir = os.path.join(task_dir, file_config.FIGURE_DIR)
        task_output_dir = os.path.join(task_dir, file_config.OUTPUT_DIR)
        for dir_ in [task_data_dir, task_fig_dir, task_output_dir]:
            if not check_dir_exists(dir_):
                create_dir(dir_)

        # Construct env profiles
        env_profiles = {}
        env_profiles['task_dirs'] = {
            "task_dir": task_dir,
            "data_dir": task_data_dir,
            "figure_dir": task_fig_dir,
            "output_dir": task_output_dir,
        }

        # Copy data 
        data_files = copy_files(work_data_dir,task_data_dir)

        return {
            "data_files": data_files,
            "env_profiles": env_profiles,
        }
    
    def env_perception(state:State):
        """"""

        # Pass input
        env_profiles = state['env_profiles']
        
        # Get docker status perception 
        docker_status_str = "Loaded dockers are:\n"
        docker_profiles = load_docker_profiles()
        docker_images = docker.from_env().images.list()
        all_loaded_tags = []
        for img in docker_images:
            all_loaded_tags.append(img.tags[0]) 
        for profile in docker_profiles['Docker images']:
            profile_tags = profile['name']+':'+profile['tag']
            profile_str = "docker name: " + profile_tags + "\n"
            profile_str += "docker description: " + profile['description'] + "\n"
            profile_str += "supported language: " + profile['languages'] + "\n"
            profile_str += "pre-installed packages: " + profile['packages'] + "\n"
            if profile_tags in all_loaded_tags:
                docker_status_str += profile_str
        # Pass to env_profiles 
        env_profiles['docker status'] = docker_status_str

        # Get native env profiles 
        native_env_profile = get_native_env_perception()
        # Pass to env_profiles 
        env_profiles['native env languages'] = "Language installed in native env and their versions are:\n"+str(native_env_profile) + "\n"

        return {
            "env_profiles": env_profiles,
            "data_prec_reflex": "",  # initial data precept reflection 
            "data_prec_codes": [""], # initial data preception 
        }


    def node_data_perception_tasking(state:State):
        """
        """

        # Pass inputs
        try:
            data_perc_reflex = state['data_perc_reflex'][:-1]
        except:
            data_perc_reflex = ""
        env_profiles = state['env_profiles']
        data_files = state['data_files']
        try:
            n_iter = state['n_iter']
        except:
            n_iter = 0

        # Parse reflex
        if len(data_perc_reflex) > 0:
            reflex_str = "### Code for data perception, executed in the previous round:  \n" + data_perc_reflex
            reflex_str += "### With following reflection note:  \n" + data_perc_reflex
        else:
            reflex_str = ""

        # Parse human input
        human_input = "## Data files:  \n" + str(data_files) + "\n" + reflex_str

        # # Parse data file description
        # data_desc_file_path =  os.path.join(env_profiles['task_dirs']['data_dir'],'data_description.txt')
        # if os.path.exists(data_desc_file_path):
        #     with open(data_desc_file_path,"r", encoding="utf-8-sig") as f:
        #         data_desc = f.read()
        #     human_input += "### The description of (some of the) above data files as follow:  \n" + data_desc

        # Call prompt template
        prompt, input_vars = load_prompt_template('filemanager.data_prec')

        # Construct input message
        message = [
            SystemMessage(content=prompt.format(target_files = data_files)),
            HumanMessage(content=human_input)
        ]

        # Generate critique with llm
        i = 0
        while i < max_retry: 
            try:
                response = chat_model.invoke(message)
                data_perc_task = response.content
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error generating data perception task due to: \n{e}")

        n_iter += 1

        return {
            'data_perc_task':[data_perc_task], 
            'n_iter': n_iter,
        }
    

    async def node_subgraph_coder(state:State):
        """"""

        # Pass inputs
        data_perc_task = state['data_perc_task'][-1]
        env_profiles = state['env_profiles']

        # Invoke coder subgraph to get data perception
        coder_fin_state = await coder_subgraph.ainvoke(
            {
                "task_instruction" : data_perc_task, 
                "data_perception": "Your task is to percept input data.",
                "previous_codeblock" : "",
                "ref_codeblocks" : [],
                "env_profiles" : env_profiles,
            })
            
        
        # Parse data perception
        data_perc = coder_fin_state['execution_results']
        data_perc_code = coder_fin_state['generated_codeblock']
        return {
            "data_perc": data_perc,
            "data_perc_codes" : [data_perc_code],  
        }


    def node_dataperc_reflection(state:State):
        """"""

        # Pass inputs
        data_perc_task = state['data_perc_task'][-1]
        env_profiles = state['env_profiles']
        data_files = state['data_files'] 

        # Call prompt template
        prompt, input_vars = load_prompt_template('filemanager.data_reflex')

        message = [
            SystemMessage(content=prompt.format(target_files = data_files)),
        ]

        # Generate critique with llm
        chain = chat_model | JsonOutputParser()
        i = 0
        while i < max_retry: 
            try:
                response = chain.invoke(message)
                data_perc_status = response['qualified']
                data_perc_reflex = response['self-critique']
                break
            except Exception as e:
                i+=1
                if i == max_retry:
                    print(f"Error critque data perception due to: \n{e}")

        return {
            "data_perc_reflex": data_perc_reflex,
            "data_perc_status": data_perc_status,
        }

    #----------------
    # Define conditional edges
    #----------------

    def router_reflection(state:State):
        if state['n_iter'] > state['max_iter']:
            return "end"
        else:
            if state['critique_status']:
                return "end"
            else:
                return "regen"
        
        
    #----------------
    # Compile graph
    #----------------

    # initial builder
    builder = StateGraph(State, config_schema = config_schema)
    # add nodes
    builder.add_node("File management", node_file_management)
    builder.add_node("Env perception", env_perception)
    builder.add_node("Data perc tasking",node_data_perception_tasking)
    builder.add_node("Coder",node_subgraph_coder)
    builder.add_node("Data perc reflection",node_dataperc_reflection)

    # add edges
    builder.add_edge(START, "File management")
    builder.add_edge("File management","Env perception")
    builder.add_edge("Env perception", "Data perc tasking")
    builder.add_edge("Data perc tasking", "Coder")
    builder.add_conditional_edges(
        "Data perc reflection", 
        router_reflection,
        {
            "end"   : END, 
            "regen" : "Data perc tasking"}
        )
    
    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
        )
