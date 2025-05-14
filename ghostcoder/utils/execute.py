import io
import copy
import builtins
import numpy as np
import pandas as pd
from typing import Dict, Any
from scipy.sparse import csr_matrix
from anndata._core.anndata import AnnData
from pandas.core.frame import DataFrame
from contextlib import redirect_stdout, redirect_stderr

def extract_code_blocks(markdown_text: str) -> list[str]:
    """
    Extract the content of all code blocks from a Markdown text.

    This function identifies code blocks that start and end with three backticks (```)
    and extracts their internal code content. It ignores the language specifier
    (e.g., ```python or ```r) and only keeps the original text within the code blocks.

    Args:
        markdown_text (str): A string containing Markdown-formatted text.

    Returns:
        list[str]: A list of strings, each being the content of a code block, preserving original line breaks.
    """
    # Split the input Markdown text into lines for easier processing
    lines = markdown_text.split('\n')
    in_code_block = False
    # Flag to track whether we are currently inside a code block
    in_code_block = False
    
    # List to store the extracted code blocks
    code_blocks = []
    
    # Temporary list to collect lines of the current code block
    current_block = []
    
    # Iterate through each line
    for line in lines:
        # Check if the line starts with ```
        if line.startswith('```'):
            # If already inside a code block, this is the end marker
            if in_code_block:
                # Join the collected lines into a single string and add to code_blocks
                code_blocks.append('\n'.join(current_block))
                # Reset the current block for the next code block
                current_block = []
                # Set the flag to False, indicating we are no longer in a code block
                in_code_block = False
            else:
                # If not inside a code block, this is the start marker
                # Set the flag to True, indicating we are now in a code block
                in_code_block = True
        elif in_code_block:
            # If inside a code block and the line does not start with ```, add it to the current block
            current_block.append(line)
    
    # Handle the case where the text ends without closing the code block
    # If still in a code block after processing all lines, add the last collected lines
    if in_code_block:
        code_blocks.append('\n'.join(current_block))
    
    # Return the list of extracted code blocks
    return code_blocks



"""OLD VERSION below, no longer in use"""
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
