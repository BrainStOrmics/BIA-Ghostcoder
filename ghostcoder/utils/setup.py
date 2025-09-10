#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BIA-Ghostcoder System Setup and Initialization Utilities
# Provides functions for system initialization, LLM configuration, vector database setup,
# and environment detection. Essential for preparing the BIA-Ghostcoder system for
# bioinformatics analysis workflows with proper model and database configurations.

import os 
import subprocess
from ghostcoder.config import *
from ghostcoder.utils import *
from ghostcoder.docker import get_docker_status

# LangChain components for vector storage and embeddings
from langchain_postgres.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings 
from langchain_community.embeddings import DashScopeEmbeddings

#######################################
# LARGE LANGUAGE MODEL CONFIGURATION
# Functions for initializing and configuring various LLM models used in BIA-Ghostcoder
#######################################

#######################################
# Initialize all LLM models for BIA-Ghostcoder system
# Globals:
#   llm_api_config.MODELS (modified to store initialized models)
#   llm_api_config.CHAT_MODEL_API, CODE_MODEL_API, EMBED_MODEL_API (read config)
# Arguments:
#   None (uses global configuration)
# Returns:
#   None (stores models in global configuration)
#######################################
def setup_LLMs() -> None:
    """
    Initialize and configure all Large Language Models for the BIA-Ghostcoder system.
    
    This function sets up three types of models essential for bioinformatics analysis:
    - Chat model: For natural language understanding and task interpretation
    - Code model: For generating bioinformatics analysis code
    - Embedding model: For vector similarity search in code retrieval
    
    The function handles multiple embedding providers (DashScope, OpenAI) with fallback
    mechanisms to ensure robust model initialization even if some services are unavailable.
    
    Returns:
        None: Models are stored in the global llm_api_config.MODELS dictionary.
    """
    # Initialize chat model for natural language processing and task understanding
    try:
        chat_model = ChatOpenAI(
            api_key=llm_api_config.CHAT_MODEL_API['api'],
            base_url=llm_api_config.CHAT_MODEL_API['url'],
            model=llm_api_config.CHAT_MODEL_API['model'],
            temperature=0,  # Deterministic output for consistent behavior
            max_retries=3,  # Robust error handling for network issues
        )
    except Exception as e:
        # Graceful degradation - system can still function without chat model
        print(f"Warning: Failed to initialize chat model: {e}")
        chat_model = None

    # Store chat model in global configuration for system-wide access
    llm_api_config.MODELS['chat_model'] = chat_model

    # Initialize code model specifically for generating bioinformatics analysis code
    try:
        code_model = ChatOpenAI(
            api_key=llm_api_config.CODE_MODEL_API['api'],
            base_url=llm_api_config.CODE_MODEL_API['url'],
            model=llm_api_config.CODE_MODEL_API['model'],
            temperature=0,  # Deterministic code generation for reproducibility
            max_retries=3,  # Robust error handling for network issues
        )
    except Exception as e:
        # Graceful degradation - system can still function without code model
        print(f"Warning: Failed to initialize code model: {e}")
        code_model = None

    # Store code model in global configuration
    llm_api_config.MODELS['code_model'] = code_model

    # Initialize embedding model with fallback mechanism
    # Try DashScope first (Chinese AI service with good performance)
    try:
        embed_model = DashScopeEmbeddings(
            dashscope_api_key=llm_api_config.EMBED_MODEL_API['api'],
            model=llm_api_config.EMBED_MODEL_API['model'],
        )
    except Exception as e:
        # Fallback to OpenAI embeddings if DashScope fails
        print(f"Warning: Failed to initialize DashScope embeddings: {e}")
        try: 
            embed_model = OpenAIEmbeddings(
                api_key=llm_api_config.EMBED_MODEL_API['api'],
                base_url=llm_api_config.EMBED_MODEL_API['url'],
                model=llm_api_config.EMBED_MODEL_API['model'],
            )
        except Exception as e:
            # Final fallback - system can work without embeddings but with reduced functionality
            print(f"Warning: Failed to initialize OpenAI embeddings: {e}")
            embed_model = None

    # Store embedding model in global configuration
    llm_api_config.MODELS['embed_model'] = embed_model

#######################################
# RETRIEVAL-AUGMENTED GENERATION (RAG) SYSTEM SETUP
# Functions for configuring vector databases and retrieval systems
#######################################

#######################################
# Setup Reference Code Database for bioinformatics code retrieval
# Globals:
#   None (uses local variables only)
# Arguments:
#   emb_model: Embedding model for vector similarity search
#   port (int): PostgreSQL database port
#   name (str): Collection name in vector database
#   search_type (str): Type of similarity search algorithm
#   n_res (int): Number of results to return
# Returns:
#   retriever: Configured vector database retriever object
#######################################
def setup_RefCodeDB(
        emb_model, 
        port: int = 6688,
        name: str = "RefCodeDB",
        search_type: str = "mmr",
        n_res: int = 5,
        ):
    """
    Setup the Reference Code Database for bioinformatics code retrieval.
    
    This function configures a PostgreSQL-based vector database containing
    bioinformatics code snippets. It uses PGVector extension for efficient
    similarity search and supports various search algorithms including MMR
    (Maximal Marginal Relevance) for diverse result retrieval.
    
    Args:
        emb_model: Pre-initialized embedding model for converting text to vectors.
                  Should be compatible with the embeddings used to populate the database.
        port (int, optional): PostgreSQL database port. Defaults to 6688.
        name (str, optional): Collection name in the vector database. Defaults to "RefCodeDB".
        search_type (str, optional): Similarity search algorithm. Defaults to "mmr" for
                                   diverse results. Other options include "similarity".
        n_res (int, optional): Number of similar code snippets to retrieve. Defaults to 5.
    
    Returns:
        retriever: Configured LangChain retriever object for code similarity search.
    """
    # Construct PostgreSQL connection string for Docker-based database
    # Uses standard credentials and database name for BIA-Ghostcoder deployment
    connection = f"postgresql+psycopg://Refcodedb:Refcodedb@localhost:{port}/RefCodeDB"

    # Initialize PGVector store with embedding model and database connection
    vector_store = PGVector(
        embeddings=emb_model,           # Embedding model for vector conversion
        collection_name=name,           # Table/collection name in database
        connection=connection,          # PostgreSQL connection string
        use_jsonb=True,                # Use JSONB for metadata storage (better performance)
    )

    # Create retriever with specified search configuration
    # MMR search provides diverse results by balancing relevance and diversity
    retriever = vector_store.as_retriever(
        search_type=search_type,        # Search algorithm (mmr, similarity, etc.)
        search_kwargs={"k": n_res}      # Number of results to retrieve
    )
    
    return retriever

#######################################
# Generic vector database setup dispatcher
# Globals:
#   None (uses local variables only)
# Arguments:
#   name (str): Name of the vector database to setup
#   emb_model: Embedding model for the database
# Returns:
#   retriever: Configured retriever for the specified database
#######################################
def setup_vdbs(name: str, emb_model):
    """
    Generic dispatcher for setting up different vector databases.
    
    This function serves as a factory method for initializing different types
    of vector databases used in BIA-Ghostcoder. Currently supports RefCodeDB
    but can be extended to support additional specialized databases.
    
    Args:
        name (str): Name identifier for the vector database type.
                   Currently supports "RefCodeDB".
        emb_model: Pre-initialized embedding model compatible with the target database.
    
    Returns:
        retriever: Configured retriever object for the specified database type.
    
    Raises:
        ValueError: If the specified database name is not supported.
    """
    if name == "RefCodeDB":
        retriever = setup_RefCodeDB(emb_model)
    else:
        # TODO(developer): Add support for additional vector databases
        raise ValueError(f"Unsupported vector database: {name}")
    
    return retriever

#######################################
# RUNTIME ENVIRONMENT DETECTION AND SETUP
# Functions for detecting available programming languages and setting up execution environments
#######################################

#######################################
# Get version information for a programming language or tool
# Globals:
#   None (uses local variables only)
# Arguments:
#   command (list[str]): Command to execute for version checking
# Returns:
#   str: Version string or status message
#######################################
def get_version(command: list[str]) -> str:
    """
    Execute a version command and return the version string.
    
    This function runs a command to check the version of a programming language
    or tool, handling various error conditions gracefully. Used for detecting
    available runtime environments in the BIA-Ghostcoder system.
    
    Args:
        command (list[str]): Command and arguments to execute for version checking.
                           Example: ["python", "--version"] or ["R", "--version"]
    
    Returns:
        str: Version string from the first line of output, "Unknown" if output
             is empty, or "Not installed" if the command is not found.
    """
    try:
        # Execute the version command with output capture
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        
        # Combine stdout and stderr (some tools output version to stderr)
        output = (result.stdout + result.stderr).strip()
        
        if output:
            # Return the first line of output (usually contains version info)
            return output.splitlines()[0]
        else:
            return "Unknown"
            
    except FileNotFoundError:
        # Command not found - language/tool is not installed
        return "Not installed"
    except subprocess.TimeoutExpired:
        # Command took too long - likely hung or unresponsive
        return "Timeout"
    except Exception as e:
        # Other unexpected errors
        return f"Error: {str(e)}"

#######################################
# Detect available programming languages and their versions
# Globals:
#   None (uses local variables only)
# Arguments:
#   None (uses predefined language list)
# Returns:
#   dict[str, str]: Dictionary mapping language names to version strings
#######################################
def get_native_env_perception() -> dict[str, str]:
    """
    Detect available programming languages and tools in the native environment.
    
    This function checks for the availability and versions of common programming
    languages and tools used in bioinformatics analysis. It provides environment
    awareness for the BIA-Ghostcoder system to determine execution capabilities.
    
    Returns:
        dict[str, str]: Dictionary mapping language/tool names to their version strings.
                       Only includes languages that are actually installed and accessible.
    
    Note:
        Python3 is commented out to avoid duplicate Python detection.
        The function focuses on languages commonly used in bioinformatics.
    """
    # Define programming languages and tools to detect
    # Each entry specifies the name and version command
    languages = [
        {"name": "Python", "command": ["python", "--version"]},
        # {"name": "Python3", "command": ["python3", "--version"]},  # Avoid duplicates
        {"name": "R", "command": ["R", "--version"]},               # Statistical computing
        {"name": "Java", "command": ["java", "-version"]},          # Platform for some tools
        {"name": "C++", "command": ["g++", "--version"]},           # Compiled tools
        {"name": "Node.js", "command": ["node", "--version"]},      # JavaScript runtime
        {"name": "Ruby", "command": ["ruby", "--version"]},         # Scripting language
        {"name": "Go", "command": ["go", "version"]},               # Modern systems language
        {"name": "Rust", "command": ["rustc", "--version"]},        # Systems programming
        {"name": "PHP", "command": ["php", "--version"]},           # Web scripting
        {"name": "Perl", "command": ["perl", "-v"]}                 # Bioinformatics legacy
    ]
    
    # Dictionary to store detected versions
    versions = {}
    
    # Check each language and store version if available
    for lang in languages:
        version = get_version(lang["command"])
        
        # Only include languages that are actually installed
        if version != "Not installed":
            versions[lang["name"]] = version
    
    return versions

#######################################
# WORKSPACE AND DIRECTORY MANAGEMENT
# Functions for setting up analysis workspace and directory structures
#######################################

#######################################
# Setup working directories for analysis tasks
# Globals:
#   file_config (modified to set directory paths)
#   ghostcoder_config (read for session and task IDs)
# Arguments:
#   None (uses global configuration)
# Returns:
#   None (modifies global file_config)
#######################################
def set_up_workdirs() -> None:
    """
    Setup and configure working directories for BIA-Ghostcoder analysis tasks.
    
    This function establishes the directory structure for analysis workflows,
    including workspace home, data directories, figure output, and results storage.
    It supports both user-defined workspace locations and automatic directory
    generation based on session and task identifiers.
    
    Returns:
        None: Directory paths are stored in the global file_config object.
    """
    # Determine work home directory based on configuration
    if len(file_config.WORK_HOME) > 0:
        # Use user-defined work home directory if specified
        workhome = file_config.WORK_HOME
    else:
        # Generate workspace path from current directory + session + task IDs
        current_dir = os.getcwd()
        ssid = ghostcoder_config.SESSION_ID
        taskid = ghostcoder_config.TASK_ID
        workhome = os.path.join(current_dir, ssid, taskid)
    
    # Configure input data directory path
    if file_config.INPUT_DATA_DIR == "data":  # Default relative path
        # Convert to absolute path for reliable access
        file_config.INPUT_DATA_DIR = os.path.abspath(file_config.INPUT_DATA_DIR)
    
    # Update global configuration with resolved directory paths
    file_config.WORK_HOME = workhome
    file_config.DATA_DIR = os.path.join(workhome, file_config.DATA_DIR)
    file_config.FIGURE_DIR = os.path.join(workhome, file_config.FIGURE_DIR)
    file_config.OUTPUT_DIR = os.path.join(workhome, file_config.OUTPUT_DIR)
    
    print("File directory paths configured successfully.")

#######################################
# Get comprehensive environment profile information
# Globals:
#   file_config (read for directory paths)
# Arguments:
#   None (uses global configuration and system detection)
# Returns:
#   dict: Complete environment profile including directories, Docker, and languages
#######################################
def get_env_profiles() -> dict:
    """
    Collect comprehensive environment profile information for analysis execution.
    
    This function gathers information about the current execution environment,
    including directory paths, Docker availability, and native programming language
    support. Used by the BIA-Ghostcoder system to determine execution capabilities
    and configure appropriate analysis strategies.
    
    Returns:
        dict: Environment profile containing:
            - 'task_dirs': Dictionary of analysis directory paths
            - 'docker status': Docker availability and configuration
            - 'native env languages': Available programming languages and versions
    """
    # Initialize environment profile dictionary
    env_profiles = {}
    
    # Collect task-specific directory information
    env_profiles['task_dirs'] = {
        "task_home": file_config.WORK_HOME,      # Main workspace directory
        "data_dir": file_config.DATA_DIR,        # Input data directory
        "figure_dir": file_config.FIGURE_DIR,    # Generated figures directory
        "output_dir": file_config.OUTPUT_DIR     # Analysis results directory
    }
    
    # Get Docker environment status and available images
    env_profiles['docker status'] = get_docker_status()
    
    # Detect available native programming languages and tools
    env_profiles['native env languages'] = get_native_env_perception()
    
    return env_profiles

#######################################
# SYSTEM INITIALIZATION MASTER FUNCTION
# Coordinates all system setup operations
#######################################

#######################################
# Perform initial system setup for BIA-Ghostcoder
# Globals:
#   Multiple config objects (modified through called functions)
# Arguments:
#   None (coordinates other setup functions)
# Returns:
#   None (initializes system components)
#######################################
def initial_setups() -> None:
    """
    Perform comprehensive initial setup for the BIA-Ghostcoder system.
    
    This master initialization function coordinates all necessary setup operations
    to prepare the BIA-Ghostcoder system for bioinformatics analysis workflows.
    It ensures proper directory structure and model initialization.
    
    Returns:
        None: System is configured and ready for analysis tasks.
    """
    # Setup workspace directories and file paths
    set_up_workdirs()
    
    # Initialize all Large Language Models
    # Note: Function name should be setup_LLMs() for consistency
    # TODO(developer): Rename initial_LLMs() to setup_LLMs()
    setup_LLMs()