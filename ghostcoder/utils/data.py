import os
import pickle
import inspect
import pandas as pd
from anndata._core.anndata import AnnData

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
    


def permanent_input_vars(variables: list) -> dict:
    """
    Saves the given list of variables to a pickle file in a temporary directory.
    
    This function creates a 'temp' directory in the current working directory if it doesn't exist,
    and saves the list of variables to a file named 'input_vars.pkl' in that directory.
    
    Parameters:
    variables (list): The list of variables to save.
    
    Returns:
    str: The path to the pickle file.
    """

    # Create a temporary directory to store the pickle file if it doesn't exist
    current_dir = os.getcwd()
    temp_dir = os.path.join(current_dir, 'temp')
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)
    
    # Define the path for the pickle file
    pickle_file_path = os.path.join(temp_dir, 'input_vars.pkl')
    
    # Save the list of variables to the pickle file
    with open(pickle_file_path, 'wb') as f:
        pickle.dump(variables, f)
    
    # Return a dictionary with the variable names and the pickle file path
    return  pickle_file_path 


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

def data_observation(variables:list, var_names:list) -> str:
    """
    Generate descriptions for a list of variables.
    
    This function creates a string that describes each variable in the list,
    including its name, type, and additional details if it's a DataFrame or AnnData object.
    
    Parameters:
    variables (list): List of variables to describe.
    var_names (list): List of names corresponding to the variables.
    
    Returns:
    str: A string containing descriptions of each variable.
    """
    if len(variables) != len(var_names):
        return "Error with data observation, wrong paries"

    prcp = ""
    for i in range(len(variables)):
        var= variables[i]
        prcp += f"Variable '{var_names[i]}' is a {type(var).__name__}:\n"
        if isinstance(var, pd.DataFrame):
            prcp += describe_dataframe(var)
        elif isinstance(var, AnnData):
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



def input_variable_wrapper(variables):
    """
    Wraps the input variables by finding their names, saving them to a pickle file,
    and generating a description.
    
    This function uses introspection to find the names of the variables passed to it,
    saves them to a temporary pickle file, and generates a description using data_observation.
    
    Parameters:
    variables: List of variables to wrap.
    
    Returns:
    dict: A dictionary containing the variable names, the path to the pickle file,
          and the description of the variables.
    """

    # Get the caller's frame to access its local and global variables
    caller_frame = inspect.currentframe().f_back
    if caller_frame is None:
        raise RuntimeError("No caller frame found")
    
    caller_locals = caller_frame.f_locals
    caller_globals = caller_frame.f_globals
    
    # Initialize list to hold variable names and set to track used names
    var_names = []
    used_names = set()
    
    for value in variables:
        # First, look for unused names in caller's locals that match the value
        local_candidates = [name for name, var in caller_locals.items() if var is value and name not in used_names]
        if local_candidates:
            var_name = local_candidates[0]  # Pick the first matching name
        else:
            # If not found in locals, look in caller's globals
            global_candidates = [name for name, var in caller_globals.items() if var is value and name not in used_names]
            if global_candidates:
                var_name = global_candidates[0]
            else:
                var_name = "unknown"  # If no matching name is found
        var_names.append(var_name) 
        if var_name != "unknown":
            used_names.add(var_name)  # Mark the name as used

    # Create the wrapper dictionary
    wrap_dict = {}
    wrap_dict['var_names'] = var_names

    # Save variables to local file
    pickle_file_path = permanent_input_vars(variables)
    wrap_dict['persis_add'] = pickle_file_path

    # Get variable description
    perception  = data_observation(variables,var_names)
    wrap_dict['perception'] = perception

    return wrap_dict