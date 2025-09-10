#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BIA-Ghostcoder Data Processing Utilities
# Provides functions for variable persistence, data observation, and input wrapping
# for bioinformatics analysis workflows.

import os
import pickle
import inspect
import pandas as pd
from anndata._core.anndata import AnnData

#######################################
# LEGACY CODE - DEPRECATED
# This is the original implementation of permanent_input_vars
# Kept for reference but should not be used in production
# TODO(developer): Remove this commented code after migration is complete
#######################################
# def permanent_input_vars(variables: list) -> dict:
#     """"""
#     global_vars = globals()
#     locala_vars = locals()

#     # Initialize the result list
#     var_names = []

#     # Iterate through the list of input variable values
#     for value in variables:
#         var_name = None # Initial with None
#         # First check the local scope of the caller
#         for name, var in locala_vars.items():
#             if var is value:
#                 var_name = name
#         # If not found in local scope, check global scope.
#         if var_name is None:
#             for name, var in global_vars.items():
#                 if var is value:
#                     var_name = name
#                     break
#         var_names.append(var_name)

#     current_dir = os.getcwd()
#     temp_dir = os.path.join(current_dir,'temp')
#     if not os.path.exists(temp_dir):
#         os.mkdir(temp_dir)
    
#     pickle_file_dir = temp_dir+'/input_vars.pkl'

#     with open(pickle_file_dir, 'wb') as f:
#         pickle.dump(variables, f)

#     input_wrap = {"var_names": var_names,
#                      "persis_add": }

#     return input_wrap
    


#######################################
# Persist variables to temporary pickle file
# Globals:
#   None (uses local variables only)
# Arguments:
#   variables (list): List of Python objects to serialize and save
# Returns:
#   str: Absolute path to the created pickle file
# Raises:
#   OSError: If directory creation or file writing fails
#######################################
def permanent_input_vars(variables: list) -> str:
    """
    Saves the given list of variables to a pickle file in a temporary directory.
    
    This function creates a 'temp' directory in the current working directory if it doesn't exist,
    and saves the list of variables to a file named 'input_vars.pkl' in that directory.
    Used primarily for persisting analysis input variables across different execution contexts.
    
    Parameters:
    variables (list): The list of variables to save. Can contain any picklable Python objects
                     including pandas DataFrames, AnnData objects, and basic data types.
    
    Returns:
    str: The absolute path to the created pickle file.
    
    Raises:
    OSError: If the temporary directory cannot be created or the file cannot be written.
    """

    # Create a temporary directory to store the pickle file if it doesn't exist
    # Using current working directory as base to ensure accessibility
    current_dir = os.getcwd()
    temp_dir = os.path.join(current_dir, 'temp')
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)
    
    # Define the path for the pickle file
    # Using standardized filename for consistency across the application
    pickle_file_path = os.path.join(temp_dir, 'input_vars.pkl')
    
    # Save the list of variables to the pickle file using binary mode
    # This preserves all Python object types including complex scientific data structures
    with open(pickle_file_path, 'wb') as f:
        pickle.dump(variables, f)
    
    # Return the absolute path for use by other components
    return pickle_file_path 


#######################################
# Generate comprehensive DataFrame description
# Globals:
#   None (uses local variables only)
# Arguments:
#   var (pd.DataFrame): DataFrame object to analyze and describe
# Returns:
#   str: Multi-line string containing DataFrame structure and content summary
#######################################
def describe_dataframe(var: pd.DataFrame) -> str:
    """
    Generate a natural language description of a pandas DataFrame.
    
    Creates a comprehensive description including dimensions, column information,
    data types, summary statistics, and sample data. This is particularly useful
    for bioinformatics data analysis where understanding data structure is critical.

    Parameters:
    var (pd.DataFrame): The DataFrame to describe. Should be a valid pandas DataFrame
                       with at least basic structure (rows and columns).

    Returns:
    str: A multi-line string describing the DataFrame's structure and content,
         including dimensions, column names, data types, statistics, and sample rows.
    """
    desc = ""
    
    # Basic dimensional information - essential for understanding data scale
    desc += f"\nIt has {var.shape[0]} rows and {var.shape[1]} columns."
    
    # Column information - critical for understanding available features
    desc += f"\nColumn names: {', '.join(var.columns)}"
    
    # Data type information - important for downstream analysis planning
    desc += f"\nData types:\n{var.dtypes.to_string()}"
    
    # Statistical summary - provides insight into data distribution and quality
    desc += f"\nSummary statistics:\n{var.describe().to_string()}"
    
    # Sample data - allows quick verification of data format and content
    desc += f"\nFirst few rows:\n{var.head().to_string()}"
    
    return desc

#######################################
# Generate comprehensive descriptions for multiple variables
# Globals:
#   None (uses local variables only)
# Arguments:
#   variables (list): List of Python objects to describe
#   var_names (list): Corresponding names for each variable
# Returns:
#   str: Formatted string containing detailed descriptions of all variables
# Raises:
#   ValueError: If variables and var_names lists have different lengths
#######################################
def data_observation(variables: list, var_names: list) -> str:
    """
    Generate descriptions for a list of variables.
    
    This function creates a comprehensive string that describes each variable in the list,
    including its name, type, and additional details if it's a DataFrame or AnnData object.
    Particularly useful for bioinformatics workflows where understanding input data
    structure is crucial for analysis planning.
    
    Parameters:
    variables (list): List of variables to describe. Can contain pandas DataFrames,
                     AnnData objects, or any other Python objects.
    var_names (list): List of names corresponding to the variables. Must have the
                     same length as variables list.
    
    Returns:
    str: A formatted string containing descriptions of each variable, with detailed
         information for supported data types (DataFrame, AnnData) and basic
         representation for other types.
         
    Raises:
    ValueError: If the lengths of variables and var_names lists don't match.
    """
    # Validate input parameters - ensure lists have matching lengths
    if len(variables) != len(var_names):
        return "Error with data observation, wrong paries"  # TODO(developer): Fix typo in error message

    prcp = ""
    
    # Iterate through each variable and generate appropriate description
    for i in range(len(variables)):
        var = variables[i]
        prcp += f"Variable '{var_names[i]}' is a {type(var).__name__}:\n"
        
        # Handle pandas DataFrame objects with comprehensive description
        if isinstance(var, pd.DataFrame):
            prcp += describe_dataframe(var)
            
        # Handle AnnData objects (common in single-cell genomics)
        elif isinstance(var, AnnData):
            # Basic AnnData structure information
            prcp += f"\nIt has {var.n_obs} observations and {var.n_vars} variables."
            
            # Describe observation metadata if available
            if var.obs is not None and not var.obs.empty:
                prcp += "\nFor its .obs (observation metadata):"
                prcp += describe_dataframe(var.obs)
                
            # Describe variable metadata if available  
            if var.var is not None and not var.var.empty:
                prcp += "\nFor its .var (variable metadata):"
                prcp += describe_dataframe(var.var)
                
            # List unstructured annotations if present
            if var.uns:
                prcp += f"\nIts unstructured annotation (.uns): {list(var.uns.keys())}"
                
        # Handle all other data types with basic string representation
        else:
            prcp += f"{var}\n"

    return prcp



#######################################
# Comprehensive input variable processing and wrapping
# Globals:
#   None (uses caller frame inspection)
# Arguments:
#   variables (list): List of Python objects to wrap and process
# Returns:
#   dict: Complete wrapper containing variable names, persistence path, and descriptions
# Raises:
#   RuntimeError: If caller frame cannot be accessed for introspection
#######################################
def input_variable_wrapper(variables):
    """
    Wraps the input variables by finding their names, saving them to a pickle file,
    and generating a description.
    
    This function uses introspection to find the names of the variables passed to it,
    saves them to a temporary pickle file, and generates a description using data_observation.
    This is the main entry point for preparing input variables for bioinformatics analysis
    workflows in the BIA-Ghostcoder system.
    
    Parameters:
    variables (list): List of variables to wrap. Can contain any Python objects,
                     typically pandas DataFrames, AnnData objects, or other analysis inputs.
    
    Returns:
    dict: A dictionary containing:
          - 'var_names': List of discovered variable names
          - 'persis_add': Path to pickle file containing serialized variables
          - 'perception': Detailed description of all variables
          
    Raises:
    RuntimeError: If the caller frame cannot be accessed for variable name introspection.
    """

    # Get the caller's frame to access its local and global variables
    # This introspection allows us to discover the original variable names
    caller_frame = inspect.currentframe().f_back
    if caller_frame is None:
        raise RuntimeError("No caller frame found")
    
    caller_locals = caller_frame.f_locals
    caller_globals = caller_frame.f_globals
    
    # Initialize list to hold variable names and set to track used names
    # The used_names set prevents duplicate name assignment for identical objects
    var_names = []
    used_names = set()
    
    # Iterate through each variable to discover its name through introspection
    for value in variables:
        # First, look for unused names in caller's locals that match the value
        # Local scope takes precedence as it's more specific to the calling context
        local_candidates = [name for name, var in caller_locals.items() 
                          if var is value and name not in used_names]
        if local_candidates:
            var_name = local_candidates[0]  # Pick the first matching name
        else:
            # If not found in locals, look in caller's globals
            # Global scope is checked as fallback for module-level variables
            global_candidates = [name for name, var in caller_globals.items() 
                               if var is value and name not in used_names]
            if global_candidates:
                var_name = global_candidates[0]
            else:
                # If no matching name is found, use placeholder
                var_name = "unknown"  # TODO(developer): Consider generating unique names
                
        var_names.append(var_name) 
        if var_name != "unknown":
            used_names.add(var_name)  # Mark the name as used to prevent duplicates

    # Create the comprehensive wrapper dictionary
    wrap_dict = {}
    wrap_dict['var_names'] = var_names

    # Save variables to persistent storage for cross-execution access
    pickle_file_path = permanent_input_vars(variables)
    wrap_dict['persis_add'] = pickle_file_path

    # Generate detailed description of all variables for analysis planning
    perception = data_observation(variables, var_names)
    wrap_dict['perception'] = perception

    return wrap_dict