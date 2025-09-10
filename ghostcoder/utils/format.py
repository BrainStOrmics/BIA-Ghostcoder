#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BIA-Ghostcoder Format Processing Utilities
# Provides functions for code extraction, JSON parsing, markdown conversion,
# and web content loading. Essential for processing LLM responses and formatting
# output in bioinformatics analysis workflows.

import re
import json
from langchain_unstructured import UnstructuredLoader

#######################################
# Extract Python code blocks from text content
# Globals:
#   None (uses local variables only)
# Arguments:
#   context (str): Input string containing potential Python code blocks
# Returns:
#   str: Merged Python code from all extracted blocks
#######################################
def extract_python_codeblock(context: str) -> str:
    """
    Extracts Python code blocks from a given string.

    This function identifies and returns Python code blocks enclosed in triple backticks (```),
    optionally prefixed with 'python'. It handles multi-line code blocks and strips unnecessary
    whitespace from the results. Essential for processing LLM responses containing Python code
    in BIA-Ghostcoder workflows.

    Args:
        context (str): The input string containing potential Python code blocks. Typically
                      from LLM responses that include code snippets in markdown format.

    Returns:
        str: A merged string containing all extracted Python code blocks joined with newlines.
             Returns empty string if no code blocks are found.
             
    Note:
        Return type annotation was corrected from 'list' to 'str' to match actual implementation.
    """
    # Define the regex pattern to match Python code blocks
    # Pattern breakdown:
    # - ``` matches the opening triple backticks
    # - (?:python)? optionally matches 'python' without capturing it (non-capturing group)
    # - \s*\n? allows optional whitespace or a newline after the opening backticks
    # - (.*?) captures the code block content non-greedily (minimal matching)
    # - \n?``` matches an optional newline and the closing triple backticks
    pattern = r'```(?:python)?\s*\n?(.*?)\n?```'

    # Find all matching code blocks in the input string
    # re.DOTALL flag ensures '.' matches newline characters for multi-line code blocks
    # This is crucial for extracting complete Python functions and classes
    code_blocks = re.findall(pattern, context, re.DOTALL)

    # Clean up each code block by removing leading and trailing whitespace
    # This ensures clean, executable Python code without formatting artifacts
    code_blocks = [block.strip() for block in code_blocks]

    # Merge all code blocks into a single string with newline separators
    # This creates a single executable Python script from multiple code blocks
    merged_code = "\n".join(code_blocks)

    # Return the merged code ready for execution
    return merged_code


#######################################
# Parse JSON content from markdown code blocks
# Globals:
#   None (uses local variables only)
# Arguments:
#   s (str): Input string containing JSON code block
# Returns:
#   dict: Parsed JSON data as Python dictionary
# Raises:
#   ValueError: If no JSON block found or invalid JSON format
#######################################
def parse_json(s: str) -> dict:
    """
    Extracts and parses JSON content from a string containing a JSON code block.

    This function identifies JSON content enclosed within triple backticks (```), optionally labeled with 'json'.
    It extracts the JSON string, parses it into a dictionary, and returns the result. Essential for processing
    structured responses from LLMs in BIA-Ghostcoder, particularly for configuration and parameter data.

    Args:
        s (str): The input string containing the JSON code block (e.g., from an LLM response).
                Typically includes markdown formatting with ```json blocks.

    Returns:
        dict: The parsed JSON data as a Python dictionary, ready for use in the application.

    Raises:
        ValueError: If no JSON code block is found in the input string.
        ValueError: If the JSON format is invalid and cannot be parsed.
    """
    # Define the regex pattern to match JSON code blocks
    # Pattern matches ```json (optional) followed by content and closing ```
    # \s* allows for optional whitespace around the JSON content
    pattern = r'```(?:json)?\s*(.*?)\s*```'
    
    # Search for the JSON code block in the input string
    # re.DOTALL ensures multiline JSON objects are captured correctly
    json_match = re.search(pattern, s, re.DOTALL)
    
    # Validate that a JSON code block was found
    if not json_match:
        raise ValueError("No valid JSON code block found in the input string.")
    
    # Extract the JSON string from the matched content and remove leading/trailing whitespace
    # group(1) contains the first captured group (the JSON content)
    json_str = json_match.group(1).strip()
    
    try:
        # Parse the JSON string into a dictionary using standard library
        # This handles all valid JSON types (objects, arrays, primitives)
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        # Provide detailed error information for debugging invalid JSON
        raise ValueError(f"Invalid JSON format: {str(e)}")
    
    return data

#######################################
# Convert dictionary to structured markdown format
# Globals:
#   None (uses local variables only)
# Arguments:
#   d (dict): Dictionary to convert to markdown
#   level (int): Current header level for markdown formatting
# Returns:
#   str: Markdown-formatted string representation
# Raises:
#   ValueError: If input is not a valid non-empty dictionary
#######################################
def critique_report_2md(d: dict, level: int = 1) -> str:
    """
    Convert a dictionary to a markdown string with proper indentation and error handling.

    This function recursively converts a dictionary into a markdown-formatted string. It handles nested dictionaries
    by increasing the header level and indenting the content accordingly. Non-dictionary values are formatted as
    list items with bold keys. Essential for generating readable reports from analysis results in BIA-Ghostcoder.

    Parameters:
        d (dict): The dictionary to convert. Must be a non-empty dictionary containing
                 analysis results, critique information, or structured data.
        level (int): The current header level for markdown formatting. Defaults to 1 for top-level headers.
                    Automatically incremented for nested structures.

    Returns:
        str: The markdown string representation of the dictionary, properly formatted
             with headers, lists, and bold text for readability.

    Raises:
        ValueError: If the input is not a dictionary or if the dictionary is empty.

    Example:
        >>> sample_dict = {
        ...     "Analysis Results": {"Genes Found": 1500, "Cells Analyzed": 2000},
        ...     "Quality Metrics": {"Pass Rate": "95%"}
        ... }
        >>> print(critique_report_2md(sample_dict))
        # Analysis Results
        - **Genes Found**: 1500
        - **Cells Analyzed**: 2000
        # Quality Metrics
        - **Pass Rate**: 95%
    """
    # Validate input parameters - ensure we have a proper dictionary to process
    if not isinstance(d, dict):
        raise ValueError("Input must be a dictionary.")
    if not d:
        raise ValueError("Dictionary cannot be empty.")

    # Initialize the markdown string accumulator
    md = ""
    
    # Process each key-value pair in the dictionary
    for key, value in d.items():
        if isinstance(value, dict):
            # Handle nested dictionaries as subsections
            # Add a header for nested dictionaries, adjusting level dynamically
            # The number of '#' characters determines the header level in markdown
            md += f"{'#' * level} {key}\n"
            
            # Recursively process the nested dictionary with an increased level
            # This creates a hierarchical structure in the markdown output
            md += critique_report_2md(value, level + 1)
        else:
            # Format non-dictionary values as list items with bold keys
            # This creates readable bullet points for individual data items
            md += f"- **{key}**: {value}\n"
    
    return md


#######################################
# Load and extract content from web URLs with retry mechanism
# Globals:
#   None (uses local variables only)
# Arguments:
#   web_url (str): URL to load content from
# Returns:
#   str: Concatenated page content from all loaded documents
#######################################
def webcontent_str_loader(web_url: str) -> str:
    """
    Loads content from a web URL using UnstructuredLoader.
    
    This function attempts to load web content with a robust retry mechanism to handle
    network issues and temporary failures. It processes the loaded documents and concatenates
    their content into a single string. Essential for the web crawler functionality in
    BIA-Ghostcoder's retrieval system.

    Attempts to load the content up to three times if exceptions occur.
    Concatenates the page_content of each document into a single string.

    Args:
        web_url (str): The URL to load content from. Should be a valid HTTP/HTTPS URL
                      pointing to a web page with extractable content.

    Returns:
        str: The concatenated page content from all loaded documents. Returns an empty 
             string if all attempts fail or if no content is found.
    """
    # Initialize the UnstructuredLoader with the provided web URL
    # UnstructuredLoader handles various document formats and web content extraction
    loader = UnstructuredLoader(web_url=web_url)
    
    # Initialize an empty string to store the concatenated page content
    page_content = ''
    
    # Attempt to load the content up to 3 times for reliability
    # This handles temporary network issues and server unavailability
    for attempt in range(3):
        try:
            # Load the content from the web URL
            # The loader processes the page and extracts structured content
            res = loader.load()
            
            # Check if the result is not empty before processing
            if res:
                # Iterate through each document in the result
                # UnstructuredLoader may return multiple document objects
                for doc in res:
                    # Ensure the page_content is a string before concatenating
                    # This prevents type errors and ensures clean text output
                    if isinstance(doc.page_content, str):
                        page_content += doc.page_content + '\n'
                
                # Exit the retry loop if content is successfully loaded
                break
            else:
                # Log when no content is loaded but no exception occurred
                print(f"Attempt {attempt + 1}: No content loaded.")
        
        except Exception as e:
            # Log the error for the current attempt with detailed information
            print(f"Attempt {attempt + 1} failed: {e}")
            
            # If this is the last attempt (attempt 2, since we start from 0)
            # notify the user that all attempts have been exhausted
            if attempt == 2:
                print("All attempts failed. Returning empty string.")
    
    # Return the concatenated page content (empty string if all attempts failed)
    return page_content
