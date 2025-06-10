import os

current_file_path  = os.path.abspath(__file__)

# For LLMs apis
class llm_api_config:
    CHAT_MODEL_API = {
        "api" : "",
        "url" : "",
        "model": "",
    }
    CODE_MODEL_API = {
        "api" : "",
        "url" : "",
        "model": "",
    }
    EMBED_MODEL_API = {
        "api" : "",
        "url" : "",
        "model": "",
    }
    MODELS = {
        "chat_model" : None,
        "code_model" : None,
        "embed_model" : None,
    }

# For Tavily
class tavily_config:
    API_KEY = ""
    MAX_RESULTS = 7

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
    WORK_DIR = './work'
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
    