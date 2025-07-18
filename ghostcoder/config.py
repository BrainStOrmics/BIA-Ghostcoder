import os
import yaml
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings 
from langchain_community.embeddings import DashScopeEmbeddings

current_file_path  = os.path.abspath(__file__)

def initial_chatmodel(api_config:dict):
    api = api_config['api']
    url = api_config['url']
    model = api_config['model']
    type = api_config['type']

    if type.lower() == 'openai':
        llm = ChatOpenAI(
            api_key = api,
            base_url= url,
            model = model,
            temperature= 0,
            max_retries = 3,
            )
        
    return llm


def initial_embedmodel(api_config:dict):
    api = api_config['api']
    url = api_config['url']
    model = api_config['model']
    type = api_config['type']

    if type.lower() == 'openai':
        embedding = OpenAIEmbeddings(
            api_key=api,
            base_url=url,
            model = model
            )
    elif type.lower() == 'dashscope':
        embedding = DashScopeEmbeddings(
            model = model,
            dashscope_api_key=api)

    return embedding
        

def initial_visionmodel(api_config:dict):
    api = api_config['api']
    url = api_config['url']
    model = api_config['model']
    type = api_config['type']    

    #if type.lower() == 'openai':

    return None        

def initial_LLMs():
    llm_config.MODELS["chat_model"] = initial_chatmodel(llm_config.CHAT_MODEL_API)
    llm_config.MODELS["code_model"] = initial_chatmodel(llm_config.CODE_MODEL_API)
    llm_config.MODELS["embed_model"] = initial_embedmodel(llm_config.EMBED_MODEL_API)
    try:
        llm_config.MODELS["vision_model"] = initial_visionmodel(llm_config.VISION_MODEL_API)
    except:
        print("Vision model not set.")


def load_yaml_config(yaml_path):
    with open(yaml_path,'r') as f:
        config = yaml.safe_load(f)
    default_keys = ""
    for config_key, cls in config_mappings:
        for sub_key, sub_value in config[config_key].items():
            try:
                setattr(cls, sub_key, sub_value)
            except:
                default_keys += config_key + "\n"

    print("Following keys are using default:\n"+default_keys+"\n\n")
    

# For LLMs apis
class llm_config:
    CHAT_MODEL_API = {
        "api" : "",
        "url" : "",
        "model": "",
        "type": "openai",
    }
    CODE_MODEL_API = {
        "api" : "",
        "url" : "",
        "model": "",
        "type": "openai",
    }
    EMBED_MODEL_API = {
        "api" : "",
        "url" : "",
        "model": "",
        "type": "openai",
    }
    VISION_MODEL_API = {
        "api" : "",
        "url" : "",
        "model": "",
        "type": "openai",
    }
    MODELS = {
        "chat_model" : None,
        "code_model" : None,
        "embed_model" : None,
        "vision_model": None,
    }

# For Tavily
class tavily_config:
    API_KEY = ""
    MAX_RESULTS = 7


# For planner subgraph
class planner_config:
    MAX_CRITIQUE = 5

# For webcrawler subgraph
class crawler_config:
    PRINT_WEBSEARCH_RES = False
    PRINT_WEBPAGE = False
    N_QUERIES = 3
    N_TOP_RES = 5

# For docker
class docker_config:
    DOCKER_PROFILES_DIR = current_file_path[:-9]+'docker'
    DEFAULT_DOCKER_PROFILE = 'BIA_dockers.json'
    NEW_DOCKER_PROFILE = 'docker_images.json'

# For coder
class coder_config:
    MAX_CRITIQUE = 3
    MAX_ERROR = 7

# For file management 
class file_config:
    #TASK_ID = 'task_id_test'
    #WORK_DIR = './work'
    INPUT_DATA_DIR = 'data'
    # task file
    DATA_DIR = 'data'
    FIGURE_DIR = 'figures'
    OUTPUT_DIR = 'results'
    # Retry inter
    MAX_ITER = 3

# For main graph
class ghostcoder_config:
    DB_RETRIEVE = True  
    MAX_ITER = 5
    TASK_ID = "Test"
    SESSION_ID = "temp"

# For task spilt
class splitter_config:
    MAX_SPILT_ITER = 3

# For retiever subgraph
class retriever_config:
    DATABASES = [
        {
            "name":'web_crawler',
            "description": 'Web search performed by Tavily and then crawl web content. Code blocks can be retrieve by search query.',
        },
        {
            "name":'RefCodeDB',
            "description": 'A reference code vector database for tools used in bioinformatics analysis. Each code block is embedded according to its corresponding bioinformatics analysis task. Code blocks can be retrieve by task descriptions.',
        }]
    

# For YAML key mapping
config_mappings = [
    ('llm_config', llm_config),
    ('tavily_config', tavily_config),
    ('crawler_config', crawler_config),
    ('docker_config', docker_config),
    ('coder_config', coder_config),
    ('file_config', file_config),
    ('ghostcoder_config', ghostcoder_config),
    ('splitter_config', splitter_config),
    ('retriever_config', retriever_config),]