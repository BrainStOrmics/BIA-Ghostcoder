import os

# For Tavily
class tavily_config:
    API_KEY = ""
    MAX_RESULTS = 7

# For webcrawler subgraph
class crawler_config:
    PRINT_WEBSEARCH_RES = False
    PRINT_WEBPAGE = False
    N_TOP_RES = 5

MAX_SPILT_ITER = 8

current_file_path  = os.path.abspath(__file__)

# For docker
class docker_config:
    DOCKER_PROFILES_DIR = current_file_path[:-9]+'docker'
    DEFAULT_DOCKER_PROFILE = 'BIA_dockers.json'
    NEW_DOCKER_PROFILE = 'docker_images.json'


# For file management 
class file_config:
    #TASK_ID = 'task_id_test'
    WORK_DIR = './work'
    INPUT_DATA_DIR = 'data'
    # task file
    DATA_DIR = 'data'
    FIGURE_DIR = 'figures'
    OUTPUT_DIR = 'results'


# For main graph
DB_RETRIEVE = True  



# For retiever subgraph
DATABASES = [
    {
        "name":'web_crawler',
        "description": 'Web search performed by Tavily and then crawl web content. Code blocks can be retrieve by search query.',
    },
    {
        "name":'BIAdb_python',
        "description": 'A reference code vector database for Python code used in bioinformatics analysis. Each code block is embedded according to its corresponding bioinformatics analysis task. Code blocks can be retrieve by task descriptions.',
    }]