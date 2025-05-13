import re
import json
from langchain_unstructured import UnstructuredLoader

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
