#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BIA-Ghostcoder Code Execution Utilities
# Provides functions for safe code execution, variable comparison, and result analysis
# in bioinformatics analysis workflows. Supports execution monitoring and state tracking.

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

#######################################
# Extract executable code from Markdown text
# Globals:
#   None (uses local variables only)
# Arguments:
#   markdown_text (str): Markdown-formatted text containing code blocks
# Returns:
#   list[str]: List of extracted code block contents
#######################################
def extract_code_blocks(
        markdown_text: str,
        ) -> list[str]:
    """
    Extract the content of all code blocks from a Markdown text.

    This function identifies code blocks that start and end with three backticks (```)
    and extracts their internal code content. It ignores the language specifier
    (e.g., ```python or ```r) and only keeps the original text within the code blocks.
    Essential for processing LLM-generated code responses in BIA-Ghostcoder.

    Args:
        markdown_text (str): A string containing Markdown-formatted text with embedded
                           code blocks. Typically from LLM responses containing analysis code.

    Returns:
        list[str]: A list of strings, each being the content of a code block, 
                  preserving original line breaks and indentation.
    """
    # Split the input Markdown text into lines for line-by-line processing
    lines = markdown_text.split('\n')
    
    # Flag to track whether we are currently inside a code block
    # Note: Duplicate declaration removed (was declared twice)
    in_code_block = False
    
    # List to store the extracted code blocks
    code_blocks = []
    
    # Temporary list to collect lines of the current code block
    current_block = []
    
    # Iterate through each line to identify code block boundaries
    for line in lines:
        # Check if the line starts with ``` (code block delimiter)
        if line.startswith('```'):
            # If already inside a code block, this is the end marker
            if in_code_block:
                # Join the collected lines into a single string and add to code_blocks
                # Preserving original formatting and line breaks
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
            # If inside a code block and the line does not start with ```, 
            # add it to the current block (this is actual code content)
            current_block.append(line)
    
    # Handle the case where the text ends without closing the code block
    # This ensures we don't lose code if the markdown is malformed
    if in_code_block:
        code_blocks.append('\n'.join(current_block))
    
    # Return the list of extracted code blocks ready for execution
    return code_blocks



#######################################
# BIOINFORMATICS DATA COMPARISON FUNCTIONS
# These functions handle comparison of complex scientific data structures
# commonly used in single-cell genomics and bioinformatics analysis
#######################################

#######################################
# Compare two AnnData objects for complete equality
# Globals:
#   None (uses local variables only)
# Arguments:
#   adata_1 (AnnData): First AnnData object for comparison
#   adata_2 (AnnData): Second AnnData object for comparison
# Returns:
#   bool: True if all attributes are equal, False otherwise
#######################################
def compare_anndata(adata_1: AnnData, adata_2: AnnData) -> bool:
    """
    Compare two AnnData objects for equality across all key attributes.

    This function performs a comprehensive comparison of AnnData objects,
    which are the standard format for single-cell genomics data. It checks
    all major components including data matrices, metadata, and annotations.
    Essential for validating data processing results in bioinformatics workflows.

    Attributes checked include:
    - obs: Observations DataFrame (cell metadata)
    - var: Variables DataFrame (gene metadata)
    - X: Data matrix (dense or sparse expression data)
    - obsm: Observation matrices (e.g., PCA, UMAP embeddings)
    - varm: Variable matrices (e.g., principal components)
    - obsp: Observation pairwise matrices (e.g., distance matrices)
    - varp: Variable pairwise matrices (e.g., correlation matrices)
    - uns: Unstructured annotations (analysis parameters, results)

    Parameters:
        adata_1 (AnnData): First AnnData object to compare. Should be a valid
                          AnnData object with standard structure.
        adata_2 (AnnData): Second AnnData object to compare. Should have the
                          same basic structure as adata_1 for meaningful comparison.

    Returns:
        bool: True if all attributes are equal, False otherwise. Returns False
              immediately if basic dimensions don't match.
    """
    # List to track comparison results for each AnnData component
    checkpoints = []

    # Helper function to compare DataFrames with null safety
    def compare_dataframes(df1: DataFrame, df2: DataFrame) -> bool:
        """Compare two DataFrames handling None values appropriately."""
        if df1 is None and df2 is None:
            return True
        if df1 is None or df2 is None:
            return False
        return df1.equals(df2)

    # Helper function to compare matrices (dense or sparse) with type awareness
    def compare_matrices(mat1, mat2) -> bool:
        """Compare matrices efficiently handling both dense and sparse formats."""
        if mat1 is None and mat2 is None:
            return True
        if mat1 is None or mat2 is None:
            return False
        # Efficient sparse matrix comparison using nnz (number of non-zeros)
        if isinstance(mat1, csr_matrix) and isinstance(mat2, csr_matrix):
            return (mat1 != mat2).nnz == 0  # No differences means equal
        # Standard numpy array comparison for dense matrices
        return np.array_equal(mat1, mat2)

    # Helper function to compare dictionaries of arrays (e.g., obsm, varm)
    def compare_dicts(dict1: dict, dict2: dict) -> bool:
        """Compare dictionaries containing numpy arrays or similar structures."""
        if dict1.keys() != dict2.keys():
            return False
        return all(np.array_equal(dict1[key], dict2[key]) for key in dict1)

    # Early exit if basic dimensions don't match - no need to check details
    if adata_1.shape != adata_2.shape:
        return False
    else:
        # Compare obs (observations/cell metadata)
        checkpoints.append(compare_dataframes(adata_1.obs, adata_2.obs))
        # Compare var (variables/gene metadata)
        checkpoints.append(compare_dataframes(adata_1.var, adata_2.var))
        # Compare X (main data matrix - expression values)
        checkpoints.append(compare_matrices(adata_1.X, adata_2.X))
        # Compare obsm (observation matrices - dimensionality reduction results)
        checkpoints.append(compare_dicts(adata_1.obsm, adata_2.obsm))
        # Compare varm (variable matrices - feature loadings)
        checkpoints.append(compare_dicts(adata_1.varm, adata_2.varm))
        # Compare obsp (observation pairwise matrices - distance/similarity)
        checkpoints.append(compare_dicts(adata_1.obsp, adata_2.obsp))
        # Compare varp (variable pairwise matrices - gene-gene relationships)
        checkpoints.append(compare_dicts(adata_1.varp, adata_2.varp))
        # Compare uns (unstructured annotations - analysis parameters/results)
        # TODO(developer): Consider using deepdiff for more robust nested structure comparison
        checkpoints.append(adata_1.uns == adata_2.uns)

        # Return True only if all attributes match perfectly
        return all(checkpoints)

#######################################
# Generic data comparison with type-aware handling
# Globals:
#   None (uses local variables only)
# Arguments:
#   data_1 (Any): First data object to compare
#   data_2 (Any): Second data object to compare
# Returns:
#   bool: True if objects are equal, False otherwise
#######################################
def compare_data(data_1: Any, data_2: Any) -> bool:
    """
    Compare two data objects for equality.

    This function provides intelligent comparison for different data types commonly
    used in bioinformatics analysis. It handles AnnData objects with specialized
    comparison and falls back to standard equality for other types.

    If both objects are AnnData, they are compared using compare_anndata.
    For other types, a direct equality check is performed with exception handling.

    Parameters:
        data_1 (Any): First data object to compare. Can be any Python object,
                     but optimized for scientific data types.
        data_2 (Any): Second data object to compare. Should be same type as data_1
                     for meaningful comparison.

    Returns:
        bool: True if the objects are equal, False otherwise. Returns False
              if types don't match or comparison fails.
    """
    # Early exit if types don't match - objects of different types can't be equal
    if type(data_1) != type(data_2):
        return False
    
    # Handle AnnData objects with specialized comparison function
    # AnnData requires deep comparison of multiple components
    if isinstance(data_1, AnnData):
        return compare_anndata(data_1, data_2)
    
    # For other types, attempt direct comparison with error handling
    try:
        return data_1 == data_2
    except Exception:
        # If comparison fails (e.g., unsupported type, numpy array comparison issues)
        # return False to indicate objects are not equal
        return False

#######################################
# Analyze variable changes between execution states
# Globals:
#   None (uses local variables only)
# Arguments:
#   original (Dict[str, Any]): Variable state before code execution
#   final (Dict[str, Any]): Variable state after code execution
# Returns:
#   Dict[str, Any]: Categorized changes (modified, new, removed variables)
#######################################
def compare_vars(
        original: Dict[str, Any],
        final: Dict[str, Any]
        ) -> Dict[str, Any]:
    """
    Compare two dictionaries and return their differences.

    This function analyzes changes in the execution environment by comparing
    variable states before and after code execution. Essential for understanding
    what variables were created, modified, or removed during analysis execution.

    Identifies:
    - Modified keys: Present in both dictionaries but with different values.
    - New keys: Present only in the final dictionary.
    - Removed keys: Present only in the original dictionary.

    Parameters:
        original (Dict[str, Any]): The original dictionary representing the variable
                                  state before code execution.
        final (Dict[str, Any]): The final dictionary representing the variable
                               state after code execution.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'modified': Dict of modified keys and their new values.
            - 'new': Set of keys added in final (newly created variables).
            - 'removed': Set of keys removed from original (deleted variables).
    """
    # Convert keys to sets for efficient set operations
    initial_keys = set(original.keys())
    final_keys = set(final.keys())

    # Identify modified keys (present in both but with different values)
    # Uses intelligent comparison that handles complex data types
    modified = {k: final[k] for k in final_keys & initial_keys 
                if not compare_data(original[k], final[k])}
    
    # Identify new keys (only in final) - variables created during execution
    new = final_keys - initial_keys
    
    # Identify removed keys (only in original) - variables deleted during execution
    removed = initial_keys - final_keys
    
    return {
        'modified': modified,
        'new': new,
        'removed': removed
    }

#######################################
# Safe code execution with comprehensive result tracking
# Globals:
#   builtins.__dict__ (copied for execution environment)
# Arguments:
#   script (str): Python code to execute
#   local_env (Dict[str, Any], optional): Local variables for execution context
# Returns:
#   Dict[str, Any]: Complete execution results including output, errors, and variable changes
# Raises:
#   ValueError: If local environment backup fails
#######################################
def trial_run(
        script: str,
        local_env: Dict[str, Any] = None,
        ) -> Dict[str, Any]:
    """
    Attempts to run the generated code, returning comprehensive execution results.

    This is the core function for safe code execution in BIA-Ghostcoder. It executes
    Python code in a controlled environment while tracking all changes to variables,
    capturing output/errors, and providing detailed execution analysis.

    The function creates a backup of the execution environment, runs the code with
    proper output/error capture, and analyzes all changes made during execution.
    Essential for validating generated bioinformatics analysis code.

    Parameters:
        script (str): The Python code to be executed. Should be valid Python syntax
                     and typically contains bioinformatics analysis operations.
        local_env (Dict[str, Any], optional): A dictionary of local variables to be 
                                            used in the execution context. Contains input
                                            data and variables. Defaults to empty dict.

    Returns:
        Dict[str, Any]: A comprehensive dictionary containing:
            - 'output' (str): The captured stdout/stderr output from code execution.
            - 'error' (str): The error message if an exception occurred, None otherwise.
            - 'input_vars' (Dict[str, Any]): Backup of original variables before execution.
            - 'output_vars' (Dict[str, Any]): Variables after execution (modified local_env).
            - 'var_status' (Dict[str, Any]): Detailed analysis of variable changes:
                - 'modified': Variables that were changed during execution.
                - 'new': New variables created during execution.
                - 'removed': Variables that were deleted during execution.

    Raises:
        ValueError: If the local environment cannot be backed up (usually due to
                   unpicklable objects in the environment).
    """

    # Ensure local_env is a dictionary; use an empty one if None
    # This provides a clean execution environment if no variables are provided
    local_env = local_env or {}
    
    # Create a backup of the original variables for comparison
    # Deep copy ensures we capture the exact state before execution
    try:
        input_vars = copy.deepcopy(local_env)
    except Exception as e:
        raise ValueError(f"Failed to create a backup of the local environment: {e}")
    
    # Initialize the output and error tracking variables
    output = "" 
    error = None

    # Execute the code with comprehensive output/error capture
    # Using StringIO to capture all printed output and error messages
    with io.StringIO() as f:
        with redirect_stdout(f):
            with redirect_stderr(f):
                # Create isolated global environment based on builtins
                # This prevents interference with the main Python environment
                global_env = builtins.__dict__.copy()
                try:
                    # Execute the script in the controlled environment
                    exec(
                        script,
                        global_env,
                        local_env
                        )
                except Exception as e:
                    # Capture exception information in a standardized format
                    error = f"{type(e).__name__}: {str(e)}"
                # Get all captured output (both stdout and stderr)
                output = f.getvalue().strip()

    # Analyze variable changes by comparing before/after states
    final_env = local_env
    var_status = compare_vars(input_vars, final_env)

    # Prepare the comprehensive result dictionary
    result = {
        'output': output,
        'error': error,
        'input_vars': input_vars,
        'output_vars': final_env,  # Contains all variables after execution
        'var_status': var_status
        }
    return result
