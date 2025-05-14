You are tasked with filtering code blocks from a mixed set of search results, which includes both database and web search content. The goal is to identify and retain only those results that contain useful code blocks relevant to the given query task, while filtering out web content that does not contain code blocks.

## Instructions
1. Identify Code Blocks:
Examine each content item to determine if it contains a code block. A code block is typically enclosed in triple backticks (```), <code> tags, or other code formatting indicators. Discard any content item that does not contain a code block.

2. Relevance Check:
For each identified code block, assess its relevance to the query task. Evaluate:
The programming language (e.g., Python for a Python-specific task).
The functionality described in the code (e.g., does it perform the task required?).
How well it matches the query task’s requirements.

3. Filter Results:
Retain only those content items that contain at least one relevant code block. Exclude:
Items with no code blocks (e.g., plain text web pages).
Items with code blocks that are irrelevant to the query task.

4. Output Format:
Return the indices of the retained content items in following JSON format. If no content items contain relevant code blocks, return an empty list.

## Output format
---
Please respond in the following **json** format:
```json
{
   "index":[ // if no useful retrieve provieded, return empty list.
    "index_1",
    "index_2",
    ... 
   ]
}