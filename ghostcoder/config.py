import os

# Tool configuration
TAVILY_MAX_RESULTS = 7
MAX_SPILT_ITER = 8
TASK_ID = 'task_id_test'

current_file_path  = os.path.abspath(__file__)

# For docker
DOCKER_PROFILES_DIR = current_file_path[:-9]+'docker'
DEFAULT_DOCKER_PROFILE = 'BIA_dockers.json'
NEW_DOCKER_PROFILE = 'docker_images.json'

# For file management 
WORK_DIR = './work'
INPUT_DATA_DIR = 'data'
# task file
DATA_DIR = 'data'
FIGURE_DIR = 'figures'
OUTPUT_DIR = 'results'

# For env perception

# For main graph
DB_RETRIEVE = True  

# For webcrawler subgraph
PRINT_WEBSEARCH_RES = False
PRINT_WEBPAGE = False

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