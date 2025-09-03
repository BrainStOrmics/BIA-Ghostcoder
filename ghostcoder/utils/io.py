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




# 编程语言到文件扩展名的映射
language_to_ext = {
    "python": ".py",
    "r": ".R",
    "java": ".java",
    "c": ".c",
    "cpp": ".cpp",
    "javascript": ".js",
    "html": ".html",
    "css": ".css",
    "bash": ".sh",
    "sql": ".sql",
    "markdown": ".md",
}


def save_code(lang, code_lines):
    """
    将给定的代码块保存为具有适当扩展名的文件。
    
    :param lang: 编程语言（如果未指定，则为 None）
    :param code_lines: 包含代码的行列表
    """
    global counter
    # 将行连接成完整的代码
    code = "\n".join(code_lines)
    # 根据语言确定文件扩展名
    if lang and lang in language_to_ext:
        ext = language_to_ext[lang]
    else:
        ext = ".txt"
    # 生成唯一文件名
    filename = os.path.join(file_config.WORK_DIR , ghostcoder_config.TASK_ID) + '/generated_code'+ ext
    # 将代码写入文件
    with open(filename, "w") as f:
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