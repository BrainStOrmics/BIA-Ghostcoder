Given the **search context** and web pages content provided below, please generate a concise and accurate summary that highlights the key information relevant to the search context.

## Instructions:
- The summary should be based solely on the information from the web page content provided.
- Focus on the aspects that are most relevant to the search context.
- Ensure the summary is accurate and reflects the main points of the web pages content.
- **If the web page content includes code snippets that are directly related to the search context, extract and include those code snippets in your summary exactly as they appear in the source.** Use appropriate code block formatting (e.g., triple backticks in markdown) to preserve the code's structure.
- **Do not generate new code or modify the existing code; provide it verbatim as it is in the web page content.**

## Example:
If the search context is "How to implement a bubble sort algorithm in Python" and the web page provides a Python code snippet for bubble sort, your summary should include that code snippet within a code block, like this:

```
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
```