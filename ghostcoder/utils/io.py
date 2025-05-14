import os 
import shutil
import subprocess
from ghostcoder.config import *

def file_management(task_id:str):
    # Define the base task folder
    task_folder = f"{task_id}"
    
    # Check if task_id folder exists, create if it doesn't
    if not os.path.exists(task_folder):
        os.makedirs(task_folder)
    
    # Define subfolders
    subfolders = [DATA_INPUT_DIR, FIGURE_OUT_DIR, OUTPUT_DIR]
    
    # Create subfolders if they don't exist
    for subfolder in subfolders:
        subfolder_path = os.path.join(task_folder, subfolder)
        if not os.path.exists(subfolder_path):
            os.makedirs(subfolder_path)
    
    # Move files from current directory's data folder to task_id/data
    current_data_folder = 'DATA_INPUT_DIR'
    target_data_folder = os.path.join(task_folder, 'DATA_INPUT_DIR')
    
    if os.path.exists(current_data_folder):
        # Get all files in current data folder
        for filename in os.listdir(current_data_folder):
            source_path = os.path.join(current_data_folder, filename)
            target_path = os.path.join(target_data_folder, filename)
            # Only move files, not directories
            if os.path.isfile(source_path):
                shutil.move(source_path, target_path)
                print(f"Moved {filename} to {target_data_folder}")
            else:
                print(f"Skipped {filename} (not a file)")
    

def check_dir_exists(dir, verbose = False):
    if not os.path.isdir(dir):
        if verbose:
            print(f"File dir not exists: {dir}")
        #raise FileNotFoundError(f"File dir not exists: {dir}")
        return False
    else:
        return True
    
def create_dir(dir, verbose = False):
    os.makedirs(dir)
    if verbose:
        print(f"Create direction: {dir}")

def copy_files(source_dir, destination_dir, verbose = False):
    items = []
    for item in os.listdir(source_dir):
        src_path = os.path.join(source_dir, item)
        dst_path = os.path.join(destination_dir, item)
        if os.path.isfile(src_path):
            shutil.copy2(src_path,dst_path)
            items.append(item)
            if verbose:
                print(f"File {item} successfully copied to task dir.")
        else:
            if verbose:
                print(f"{item} is not a file, it will not be copied to task dir.")

    return items 

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
