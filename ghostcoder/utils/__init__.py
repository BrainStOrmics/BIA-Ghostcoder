import io
import re
import json
import copy
import builtins
import inspect
import numpy as np
import pandas as pd
from typing import Dict, Any
from scipy.sparse import csr_matrix
from anndata._core.anndata import AnnData
from pandas.core.frame import DataFrame
from contextlib import redirect_stdout, redirect_stderr
from langchain_unstructured import UnstructuredLoader

def compare_anndata(adata_1: AnnData, adata_2: AnnData) -> bool:
    """
    Compare two AnnData objects for equality across all key attributes.

    Attributes checked include:
    - obs: Observations DataFrame
    - var: Variables DataFrame
    - X: Data matrix (dense or sparse)
    - obsm: Observation matrices
    - varm: Variable matrices
    - obsp: Observation pairwise matrices
    - varp: Variable pairwise matrices
    - uns: Unstructured annotations

    Parameters:
        adata_1 (AnnData): First AnnData object to compare.
        adata_2 (AnnData): Second AnnData object to compare.

    Returns:
        bool: True if all attributes are equal, False otherwise.
    """
    checkpoints = []

    # Helper function to compare DataFrames
    def compare_dataframes(df1: DataFrame, df2: DataFrame) -> bool:
        if df1 is None and df2 is None:
            return True
        if df1 is None or df2 is None:
            return False
        return df1.equals(df2)

    # Helper function to compare matrices (dense or sparse)
    def compare_matrices(mat1, mat2) -> bool:
        if mat1 is None and mat2 is None:
            return True
        if mat1 is None or mat2 is None:
            return False
        if isinstance(mat1, csr_matrix) and isinstance(mat2, csr_matrix):
            return (mat1 != mat2).nnz == 0  # Efficient sparse matrix comparison
        return np.array_equal(mat1, mat2)

    # Helper function to compare dictionaries of arrays
    def compare_dicts(dict1: dict, dict2: dict) -> bool:
        if dict1.keys() != dict2.keys():
            return False
        return all(np.array_equal(dict1[key], dict2[key]) for key in dict1)

    if adata_1.shape != adata_2.shape:
        return False
    else:
        # Compare obs (observations)
        checkpoints.append(compare_dataframes(adata_1.obs, adata_2.obs))
        # Compare var (variables)
        checkpoints.append(compare_dataframes(adata_1.var, adata_2.var))
        # Compare X (data matrix)
        checkpoints.append(compare_matrices(adata_1.X, adata_2.X))
        # Compare obsm (observation matrices)
        checkpoints.append(compare_dicts(adata_1.obsm, adata_2.obsm))
        # Compare varm (variable matrices)
        checkpoints.append(compare_dicts(adata_1.varm, adata_2.varm))
        # Compare obsp (observation pairwise matrices)
        checkpoints.append(compare_dicts(adata_1.obsp, adata_2.obsp))
        # Compare varp (variable pairwise matrices)
        checkpoints.append(compare_dicts(adata_1.varp, adata_2.varp))
        # Compare uns (unstructured annotations)
        # Note: uns may contain nested structures, so we use a simple equality check here
        # For a more robust comparison, consider using a library like deepdiff
        checkpoints.append(adata_1.uns == adata_2.uns)

        # Return True only if all attributes match
        return all(checkpoints)

def compare_data(data_1: Any, data_2: Any) -> bool:
    """
    Compare two data objects for equality.

    If both objects are AnnData, they are compared using compare_anndata.
    For other types, a direct equality check is performed.

    Parameters:
        data_1 (Any): First data object to compare.
        data_2 (Any): Second data object to compare.

    Returns:
        bool: True if the objects are equal, False otherwise.
    """
    # Check if types match
    if type(data_1) != type(data_2):
        return False
    
    # Handle AnnData objects
    if isinstance(data_1, AnnData):
        return compare_anndata(data_1, data_2)
    
    # For other types, attempt direct comparison
    try:
        return data_1 == data_2
    except Exception:
        # If comparison fails (e.g., unsupported type), return False
        return False

def compare_vars(
        original: Dict[str, Any],
        final: Dict[str, Any]
        ) -> Dict[str, Any]:
    """
    Compare two dictionaries and return their differences.

    Identifies:
    - Modified keys: Present in both dictionaries but with different values.
    - New keys: Present only in the final dictionary.
    - Removed keys: Present only in the original dictionary.

    Parameters:
        original (Dict[str, Any]): The original dictionary.
        final (Dict[str, Any]): The final dictionary.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'modified': Dict of modified keys and their new values.
            - 'new': Set of keys added in final.
            - 'removed': Set of keys removed from original.
    """
    # Convert keys to sets for efficient comparison
    initial_keys = set(original.keys())
    final_keys = set(final.keys())

    # Identify modified keys (present in both but with different values)
    modified = {k: final[k] for k in final_keys & initial_keys 
                if not compare_data(original[k],final[k])}
    # Identify new keys (only in final)
    new = final_keys - initial_keys
    # Identify removed keys (only in original)
    removed = initial_keys - final_keys
    return {
        'modified': modified,
        'new': new,
        'removed': removed
    }

def trial_run(
        script: str,
        local_env: Dict[str, Any] = None,
        ) -> Dict[str, Any]:
    """
    Attempts to run the generated code, returning the original variable, how the variable has changed, the execution output, the execution result, and an exception message.

    Parameters:
        code (str): The code to be executed.
        local_env (Dict[str, Any], optional): A dictionary of local variables to be used in the execution. Defaults to None.
    Returns:
        Dict[str, Any]: A dictionary containing the original variable, how the variable has changed, the execution output, the execution result, and an exception message.
            - 'output' (str): The output of the code execution.
            - 'error' (str): The error message if an exception occurred.
            - 'backup_vars' (Dict[str, Any]): A backup of the original variables before execution.
            - 'output_var' (Dict[str, Any]): A dictionary containing the variables after execution.
            - 'var_status' (Dict[str, Any]): A dictionary containing the status of the variables after execution.
                - 'modified' (Dict[str, Any]): The variables that were modified during execution.
                - 'new' (Dict[str, Any]): The new variables that were created during execution.
                - 'removed' (Dict[str, Any]): The variables that were removed during execution.
    """


    # Ensure local_env is a dictionary; use an empty one if None
    local_env = local_env or {}
    # Create a backup of the original variables
    try:
        input_vars = copy.deepcopy(local_env)
    except Exception as e:
        raise ValueError(f"Failed to create a backup of the local environment: {e}")
    # Initialize the output and error messages
    output = "" 
    error = None

    # Execute the code and capture the output/error
    with io.StringIO() as f:
        with redirect_stdout(f):
            with redirect_stderr(f):
                global_env = builtins.__dict__.copy()
                try:
                    exec(
                        script,
                        global_env,
                        local_env
                        )
                except Exception as e:
                    error = f"{type(e).__name__}: {str(e)}"
                output = f.getvalue().strip()

    # Get final env variables
    final_env = local_env
    var_status = compare_vars(input_vars, final_env)

    # Prepare the result dictionary
    result = {
        'output': output,
        'error': error,
        'input_vars': input_vars,
        'output_vars': final_env, #output_var,
        'var_status': var_status
        }
    return result


def extract_python_codeblock(context: str) -> list:
    """
    Extracts Python code blocks from a given string.

    This function identifies and returns Python code blocks enclosed in triple backticks (```),
    optionally prefixed with 'python'. It handles multi-line code blocks and strips unnecessary
    whitespace from the results.

    Args:
        context (str): The input string containing potential Python code blocks.

    Returns:
        list: A list of strings, each representing a Python code block. Returns an empty list if
              no code blocks are found.
    """
    # Define the regex pattern to match Python code blocks
    # - ``` matches the opening triple backticks
    # - (?:python)? optionally matches 'python' without capturing it
    # - \s*\n? allows optional whitespace or a newline after the opening backticks
    # - (.*?) captures the code block content non-greedily
    # - \n?``` matches an optional newline and the closing triple backticks
    pattern = r'```(?:python)?\s*\n?(.*?)\n?```'

    # Find all matching code blocks in the input string
    # re.DOTALL ensures '.' matches newline characters for multi-line code blocks
    code_blocks = re.findall(pattern, context, re.DOTALL)

    # Clean up each code block by removing leading and trailing whitespace
    code_blocks = [block.strip() for block in code_blocks]

    # Merge all code blocks into a single string with newline separators
    merged_code = "\n".join(code_blocks)

    # Return the list of extracted code blocks
    return merged_code


def parse_json(s: str) -> dict:
    """
    Extracts and parses JSON content from a string containing a JSON code block.

    This function identifies JSON content enclosed within triple backticks (```), optionally labeled with 'json'.
    It extracts the JSON string, parses it into a dictionary, and returns the result.

    Args:
        s (str): The input string containing the JSON code block (e.g., from an LLM response).

    Returns:
        dict: The parsed JSON data.

    Raises:
        ValueError: If no JSON code block is found or if the JSON format is invalid.
    """
    # Define the regex pattern to match JSON code blocks
    # Matches ```json (optional) followed by content and closing ```
    pattern = r'```(?:json)?\s*(.*?)\s*```'
    
    # Search for the JSON code block in the input string
    json_match = re.search(pattern, s, re.DOTALL)
    
    if not json_match:
        raise ValueError("No valid JSON code block found in the input string.")
    
    # Extract the JSON string from the matched content and remove leading/trailing whitespace
    json_str = json_match.group(1).strip()
    
    try:
        # Parse the JSON string into a dictionary
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {str(e)}")
    
    return data

def critique_report_2md(d: dict, level: int = 1) -> str:
    """
    Convert a dictionary to a markdown string with proper indentation and error handling.

    This function recursively converts a dictionary into a markdown-formatted string. It handles nested dictionaries
    by increasing the header level and indenting the content accordingly. Non-dictionary values are formatted as
    list items with bold keys.

    Parameters:
        d (dict): The dictionary to convert. Must be a non-empty dictionary.
        level (int): The current header level for markdown formatting. Defaults to 1 for top-level headers.

    Returns:
        str: The markdown string representation of the dictionary.

    Raises:
        ValueError: If the input is not a dictionary or if the dictionary is empty.

    Example:
        >>> sample_dict = {
        ...     "Section1": {"Key1": "Value1", "Key2": "Value2"},
        ...     "Section2": {"Key3": "Value3"}
        ... }
        >>> print(critique_report_2md(sample_dict))
        # Section1
        - **Key1**: Value1
        - **Key2**: Value2
        # Section2
        - **Key3**: Value3
    """
    # Check if the input is a valid non-empty dictionary
    if not isinstance(d, dict):
        raise ValueError("Input must be a dictionary.")
    if not d:
        raise ValueError("Dictionary cannot be empty.")

    md = ""  # Initialize the markdown string
    for key, value in d.items():
        if isinstance(value, dict):
            # Add a header for nested dictionaries, adjusting level dynamically
            md += f"{'#' * level} {key}\n"
            # Recursively process the nested dictionary with an increased level
            md += critique_report_2md(value, level + 1)
        else:
            # Format non-dictionary values as list items with bold keys
            md += f"- **{key}**: {value}\n"
    return md


def webcontent_str_loader(web_url):
    """
    Loads content from a web URL using UnstructuredLoader.
    Attempts to load the content up to three times if exceptions occur.
    Concatenates the page_content of each document into a single string.

    Args:
        web_url (str): The URL to load content from.

    Returns:
        str: The concatenated page content. Returns an empty string if all attempts fail.
    """
    # Initialize the loader with the provided web URL
    loader = UnstructuredLoader(web_url=web_url)
    
    # Initialize an empty string to store the concatenated page content
    page_content = ''
    
    # Attempt to load the content up to 3 times
    for attempt in range(3):
        try:
            # Load the content from the web URL
            res = loader.load()
            
            # Check if the result is not empty before processing
            if res:
                # Iterate through each document in the result
                for doc in res:
                    # Ensure the page_content is a string before concatenating
                    if isinstance(doc.page_content, str):
                        page_content += doc.page_content + '\n'
                # Exit the loop if content is successfully loaded
                break
            else:
                print(f"Attempt {attempt + 1}: No content loaded.")
        
        except Exception as e:
            # Log the error for the current attempt
            print(f"Attempt {attempt + 1} failed: {e}")
            
            # If this is the last attempt, notify the user
            if attempt == 2:
                print("All attempts failed. Returning empty string.")
    
    # Return the concatenated page content (empty if all attempts failed)
    return page_content


def get_variable_names(variables: list) -> list:
    """
    Returns a list of corresponding variable names in the global scope, based on the list of variable values entered.
    If a value does not have a corresponding variable name in the global scope, None is returned.

    Parameters:
    variables (list): list containing the values of the variable.

    Returns:
    var_names: List containing the names of the variables. If a value has no corresponding variable name, then None.
    """
    # Get the local scope of the caller
    caller_frame = inspect.currentframe().f_back
    caller_locals = caller_frame.f_locals

    # Getting global scopes
    global_vars = globals()

    print(global_vars)

    # Initialize the result list
    var_names = []

    # Iterate through the list of input variable values
    for value in variables:
        var_name = None # Initial with None
        # First check the local scope of the caller
        for name, var in caller_locals.items():
            if var is value:
                var_name = name
        # If not found in local scope, check global scope.
        if var_name is None:
            for name, var in global_vars.items():
                if var is value:
                    var_name = name
                    break
        var_names.append(var_name)

    return var_names

def describe_dataframe(var: pd.DataFrame) -> str:
    """
    Generate a natural language description of a pandas DataFrame.

    Parameters:
    var (pd.DataFrame): The DataFrame to describe.

    Returns:
    str: A string describing the DataFrame's structure and content.
    """
    desc = ""
    desc += f"\nIt has {var.shape[0]} rows and {var.shape[1]} columns."
    desc += f"\nColumn names: {', '.join(var.columns)}"
    desc += f"\nData types:\n{var.dtypes.to_string()}"
    desc += f"\nSummary statistics:\n{var.describe().to_string()}"
    desc += f"\nFirst few rows:\n{var.head().to_string()}"
    return desc

def data_observation(var_names: list[str]) -> str:
    """
    Generate natural language descriptions for variables based on their names.

    This function loads variables from the global scope using the provided names
    and generates descriptions for them. For DataFrames and AnnData objects,
    it provides detailed structural information.

    Parameters:
    var_names (list[str] or str): The name(s) of the variable(s) to describe.
                                  If a single string is provided, it will be
                                  treated as a list with one element.

    Returns:
    str: A string containing descriptions of all specified variables.
    """
    if isinstance(var_names, str):
        var_names = [var_names]

    prcp = ""
    for name in var_names:
        try:
            var = globals()[name]
        except KeyError:
            prcp += f"Variable '{name}' cannot be allocated from global environment.\n"
            continue

        prcp += f"Variable '{name}' is a {type(var).__name__}:\n"
        if isinstance(var, pd.DataFrame):
            prcp += describe_dataframe(var)
        elif isinstance(var, ad.AnnData):
            prcp += f"\nIt has {var.n_obs} observations and {var.n_vars} variables."
            if var.obs is not None and not var.obs.empty:
                prcp += "\nFor its .obs:"
                prcp += describe_dataframe(var.obs)
            if var.var is not None and not var.var.empty:
                prcp += "\nFor its .var:"
                prcp += describe_dataframe(var.var)
            if var.uns:
                prcp += f"\nIts unstructured annotation (.uns): {list(var.uns.keys())}"
        else:
            prcp += f"{var}\n"

    return prcp