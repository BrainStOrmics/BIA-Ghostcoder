#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BIA-Ghostcoder Input/Output Utilities
# Provides functions for file and directory management, code saving, and workspace
# organization. Essential for managing analysis workflows and generated code storage
# in bioinformatics analysis projects.

import os 
import shutil
import subprocess
from ghostcoder.config import *

#######################################
# Create and organize task-specific directory structure
# Globals:
#   DATA_INPUT_DIR, FIGURE_OUT_DIR, OUTPUT_DIR (from config)
# Arguments:
#   task_id (str): Unique identifier for the analysis task
# Returns:
#   None (creates directories and moves files)
#######################################
def file_management(task_id: str) -> None:
    """
    Create and organize a standardized directory structure for a bioinformatics analysis task.
    
    This function establishes the workspace organization for BIA-Ghostcoder analysis tasks,
    creating a hierarchical directory structure and organizing input data files. It ensures
    consistent project organization across different analysis workflows.
    
    Args:
        task_id (str): Unique identifier for the analysis task. Used as the base directory name
                      for organizing all task-related files and results.
    
    Returns:
        None: This function performs file system operations and doesn't return values.
    """
    # Define the base task folder using the provided task ID
    # This creates a unique workspace for each analysis task
    task_folder = f"{task_id}"
    
    # Check if task_id folder exists, create if it doesn't
    # Ensures we have a clean workspace for the analysis
    if not os.path.exists(task_folder):
        os.makedirs(task_folder)
    
    # Define standard subfolders for bioinformatics analysis workflow
    # These correspond to the typical stages of data analysis
    subfolders = [DATA_INPUT_DIR, FIGURE_OUT_DIR, OUTPUT_DIR]
    
    # Create subfolders if they don't exist
    # This establishes the standard directory structure for analysis organization
    for subfolder in subfolders:
        subfolder_path = os.path.join(task_folder, subfolder)
        if not os.path.exists(subfolder_path):
            os.makedirs(subfolder_path)
    
    # Move files from current directory's data folder to task_id/data
    # This organizes input data into the task-specific structure
    current_data_folder = 'DATA_INPUT_DIR'  # TODO(developer): This should use the config variable
    target_data_folder = os.path.join(task_folder, 'DATA_INPUT_DIR')
    
    # Only proceed if the source data folder exists
    if os.path.exists(current_data_folder):
        # Get all files in current data folder and move them to task directory
        for filename in os.listdir(current_data_folder):
            source_path = os.path.join(current_data_folder, filename)
            target_path = os.path.join(target_data_folder, filename)
            
            # Only move files, not directories to avoid nested directory issues
            if os.path.isfile(source_path):
                shutil.move(source_path, target_path)
                print(f"Moved {filename} to {target_data_folder}")
            else:
                print(f"Skipped {filename} (not a file)")
    

#######################################
# DIRECTORY MANAGEMENT UTILITY FUNCTIONS
# Basic functions for directory existence checking, creation, and file copying
#######################################

#######################################
# Check if directory exists with optional verbose output
# Globals:
#   None (uses local variables only)
# Arguments:
#   dir (str): Directory path to check
#   verbose (bool): Whether to print status messages
# Returns:
#   bool: True if directory exists, False otherwise
#######################################
def check_dir_exists(dir: str, verbose: bool = False) -> bool:
    """
    Check if a directory exists in the file system.
    
    This function verifies the existence of a directory and optionally provides
    verbose output for debugging purposes. Used throughout BIA-Ghostcoder for
    validating directory paths before performing file operations.
    
    Args:
        dir (str): The directory path to check. Can be relative or absolute path.
        verbose (bool, optional): Whether to print informative messages. 
                                 Defaults to False for quiet operation.
    
    Returns:
        bool: True if the directory exists and is accessible, False otherwise.
    """
    if not os.path.isdir(dir):
        if verbose:
            print(f"Directory does not exist: {dir}")
        # Note: Commented out exception raising for non-blocking behavior
        # raise FileNotFoundError(f"File dir not exists: {dir}")
        return False
    else:
        return True
    
#######################################
# Create directory with optional verbose output
# Globals:
#   None (uses local variables only)
# Arguments:
#   dir (str): Directory path to create
#   verbose (bool): Whether to print creation messages
# Returns:
#   None (creates directory)
#######################################
def create_dir(dir: str, verbose: bool = False) -> None:
    """
    Create a directory including any necessary parent directories.
    
    This function creates the specified directory and all intermediate directories
    if they don't exist. Used for setting up workspace structures in BIA-Ghostcoder
    analysis workflows.
    
    Args:
        dir (str): The directory path to create. Can include nested directory structure.
        verbose (bool, optional): Whether to print creation confirmation messages.
                                 Defaults to False for quiet operation.
    
    Returns:
        None: This function performs file system operations and doesn't return values.
    """
    os.makedirs(dir)
    if verbose:
        print(f"Created directory: {dir}")  # Fixed typo: "direction" -> "directory"

#######################################
# Copy files from source to destination directory
# Globals:
#   None (uses local variables only)
# Arguments:
#   source_dir (str): Source directory containing files to copy
#   destination_dir (str): Target directory for copied files
#   verbose (bool): Whether to print copy operation messages
# Returns:
#   list[str]: List of successfully copied file names
#######################################
def copy_files(source_dir: str, destination_dir: str, verbose: bool = False) -> list[str]:
    """
    Copy files from source directory to destination directory.
    
    This function copies all files (not directories) from the source directory
    to the destination directory, preserving file metadata. Used for organizing
    input data and results in BIA-Ghostcoder analysis workflows.
    
    Args:
        source_dir (str): The source directory path containing files to copy.
                         Must be an existing directory with read permissions.
        destination_dir (str): The destination directory path where files will be copied.
                              Must be an existing directory with write permissions.
        verbose (bool, optional): Whether to print detailed copy operation messages.
                                 Defaults to False for quiet operation.
    
    Returns:
        list[str]: A list of file names that were successfully copied. Empty list
                  if no files were copied or source directory is empty.
    """
    # Initialize list to track successfully copied items
    items = []
    
    # Iterate through all items in the source directory
    for item in os.listdir(source_dir):
        src_path = os.path.join(source_dir, item)
        dst_path = os.path.join(destination_dir, item)
        
        # Only copy files, not directories to avoid complex nested operations
        if os.path.isfile(src_path):
            # Use copy2 to preserve file metadata (timestamps, permissions)
            shutil.copy2(src_path, dst_path)
            items.append(item)
            if verbose:
                print(f"File {item} successfully copied to destination directory.")
        else:
            if verbose:
                print(f"{item} is not a file, it will not be copied to destination directory.")

    return items 




#######################################
# CODE SAVING AND LANGUAGE MAPPING UTILITIES
# Functions for saving generated code with appropriate file extensions
#######################################

# Programming language to file extension mapping
# Used for determining appropriate file extensions when saving generated code
language_to_ext = {
    "python": ".py",        # Python scripts
    "r": ".R",             # R statistical computing scripts
    "java": ".java",       # Java source files
    "c": ".c",             # C source files
    "cpp": ".cpp",         # C++ source files
    "javascript": ".js",   # JavaScript files
    "html": ".html",       # HTML markup files
    "css": ".css",         # CSS stylesheet files
    "bash": ".sh",         # Bash shell scripts
    "sql": ".sql",         # SQL database scripts
    "markdown": ".md",     # Markdown documentation files
}


#######################################
# Save code block with appropriate file extension
# Globals:
#   file_config.WORK_DIR, ghostcoder_config.TASK_ID (from config)
# Arguments:
#   lang (str or None): Programming language identifier
#   code_lines (list[str]): List of code lines to save
# Returns:
#   None (writes code to file)
#######################################
def save_code(lang: str, code_lines: list[str]) -> None:
    """
    Save a code block to a file with appropriate extension based on programming language.
    
    This function takes a code block represented as a list of lines and saves it to a file
    in the task-specific directory. The file extension is determined by the programming
    language, ensuring proper syntax highlighting and tool recognition.
    
    Args:
        lang (str or None): Programming language identifier (e.g., 'python', 'r', 'bash').
                           If None or unrecognized, defaults to '.txt' extension.
        code_lines (list[str]): List of strings representing individual lines of code.
                               Will be joined with newlines to form complete code.
    
    Returns:
        None: This function writes to the file system and doesn't return values.
    """
    # Note: global counter variable referenced but not defined in this scope
    # TODO(developer): Remove or properly implement counter functionality
    
    # Join code lines into a complete code string
    # This reconstructs the original code structure with proper line breaks
    code = "\n".join(code_lines)
    
    # Determine file extension based on programming language
    # Falls back to .txt for unknown or unspecified languages
    if lang and lang in language_to_ext:
        ext = language_to_ext[lang]
    else:
        ext = ".txt"  # Default extension for unknown languages
    
    # Generate file path within the task-specific directory structure
    # Combines work directory, task ID, and appropriate file extension
    filename = os.path.join(file_config.WORK_DIR, ghostcoder_config.TASK_ID) + '/generated_code' + ext
    
    # Write the complete code to the file
    # Using default text encoding for broad compatibility
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)

def save_code_blocks(llm_output):
    """
    处理 LLM 输出，提取并保存所有代码块。
    
    :param llm_output: 包含 LLM 生成内容的字符串
    """
    lines = llm_output.split("\n")
    in_code_block = False
    current_lang = None
    current_code = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") and not in_code_block:
            # 代码块开始
            in_code_block = True
            # 提取语言（如果指定）
            after_backticks = stripped[3:].strip()
            if after_backticks:
                lang_part = after_backticks.split(None, 1)[0]
                current_lang = lang_part.lower()
            else:
                current_lang = None
            current_code = []
        elif stripped == "```" and in_code_block:
            # 代码块结束
            in_code_block = False
            # 保存当前代码块
            save_code(current_lang, current_code)
            current_code = []
        elif in_code_block:
            # 收集代码块内的行
            current_code.append(line)
    # 处理未关闭的代码块
    if in_code_block:
        print("警告：发现未关闭的代码块。")
        save_code(current_lang, current_code)