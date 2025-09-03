import os 
import subprocess
from ghostcoder.config import *
from ghostcoder.utils import *
from ghostcoder.docker import get_docker_status


from langchain_postgres.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings 
from langchain_community.embeddings import DashScopeEmbeddings

#================================
# For LLMs
#================================

def setup_LLMs():
    try:
        chat_model = ChatOpenAI(
            api_key = llm_api_config.CHAT_MODEL_API['api'],
            base_url= llm_api_config.CHAT_MODEL_API['url'],
            model = llm_api_config.CHAT_MODEL_API['model'],
            temperature= 0,
            max_retries = 3,
            )
    except:
        chat_model = None

    llm_api_config.MODELS['chat_model'] = chat_model

    try:
        code_model = ChatOpenAI(
            api_key = llm_api_config.CODE_MODEL_API['api'],
            base_url= llm_api_config.CODE_MODEL_API['url'],
            model = llm_api_config.CODE_MODEL_API['model'],
            temperature= 0,
            max_retries = 3,
            )
    except:
        code_model = None

    llm_api_config.MODELS['code_model'] = code_model

    try:
        embed_model = DashScopeEmbeddings(
            dashscope_api_key = llm_api_config.EMBED_MODEL_API['api'],
            model = llm_api_config.EMBED_MODEL_API['model'],
            )
    except:
        try: 
            embed_model = OpenAIEmbeddings(
                api_key = llm_api_config.EMBED_MODEL_API['api'],
                base_url= llm_api_config.EMBED_MODEL_API['url'],
                model = llm_api_config.EMBED_MODEL_API['model'],
                )
        except:
            embed_model = None

    llm_api_config.MODELS['embed_model'] = embed_model

#================================
# For RAG system
#================================
    
def setup_RefCodeDB(
        emb_model, 
        port: int=6688,
        name: str="RefCodeDB",
        search_type: str = "mmr",
        n_res: int = 5,
        ):

    # Connect to Docker Postgres
    connection = "postgresql+psycopg://Refcodedb:Refcodedb@localhost:"+str(port)+"/RefCodeDB"  

    vector_store = PGVector(
        embeddings=emb_model,
        collection_name=name,
        connection=connection,
        use_jsonb=True,
    )

    retriever = vector_store.as_retriever(
        search_type=search_type, 
        search_kwargs={"k": n_res})
    
    return retriever

def setup_vdbs(name, emb_model):
    if name == "RefCodeDB":
        retriever = setup_RefCodeDB(emb_model)
    return retriever

#================================
# For running env 
#================================

def get_version(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        output = (result.stdout + result.stderr).strip()
        if output:
            return output.splitlines()[0]
        else:
            return "Unknown"
    except FileNotFoundError:
        return "Not installed"

def get_native_env_perception():
    languages = [
        {"name": "Python", "command": ["python", "--version"]},
        #{"name": "Python3", "command": ["python3", "--version"]},
        {"name": "R", "command": ["R", "--version"]},
        {"name": "Java", "command": ["java", "-version"]},
        {"name": "C++", "command": ["g++", "--version"]},
        {"name": "Node.js", "command": ["node", "--version"]},
        {"name": "Ruby", "command": ["ruby", "--version"]},
        {"name": "Go", "command": ["go", "version"]},
        {"name": "Rust", "command": ["rustc", "--version"]},
        {"name": "PHP", "command": ["php", "--version"]},
        {"name": "Perl", "command": ["perl", "-v"]}
    ]
    versions = {}
    for lang in languages:
        version = get_version(lang["command"])
        if version != "Not installed":
            versions[lang["name"]] = version
    return versions

def set_up_workdirs():
    # Get work home dir
    if len(file_config.WORK_HOME) > 0:
        workhome = file_config.WORK_HOME # User defined work home
    else:
        current_dir = os.getcwd() # Otherwise use current dir
        ssid = ghostcoder_config.SESSION_ID
        taskid = ghostcoder_config.TASK_ID
        workhome = os.path.join(current_dir,ssid,taskid)
    # Check input data dir
    if file_config.INPUT_DATA_DIR == "data": # If not use custom input data dir
        file_config.INPUT_DATA_DIR = os.path.abspath(file_config.INPUT_DATA_DIR)
    # Paser to config 
    file_config.WORK_HOME = workhome
    file_config.DATA_DIR = os.path.join(workhome,file_config.DATA_DIR)
    file_config.FIGURE_DIR = os.path.join(workhome,file_config.FIGURE_DIR)
    file_config.OUTPUT_DIR = os.path.join(workhome,file_config.OUTPUT_DIR)
    print("File dir path all set.")

def get_env_profiles():
    # Get running env profiles in dict format
    # Init dict
    env_profiles = {}
    # Get running dirs
    env_profiles['task_dirs'] = {
        "task_home": file_config.WORK_HOME,
        "data_dir": file_config.DATA_DIR,
        "figure_dir": file_config.FIGURE_DIR,
        "output_dir": file_config.OUTPUT_DIR
        }
    # Get running envs 
    env_profiles['docker status'] = get_docker_status()
    env_profiles['native env languages'] = get_native_env_perception()
    return env_profiles

def initial_setups():
    set_up_workdirs()
    initial_LLMs()