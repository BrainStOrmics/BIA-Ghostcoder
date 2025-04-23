# Introduction
这个markdwon文档是用来是示范.md格式的prompt的。
这些prompt是以SystemMessage的方式输入给LLM的，因此在这些prompt中，我们要求通过PromptEng来定义以下（部分或全部）内容：
1. **角色设定**：明确模型的角色或身份，帮助模型按照特定的语气、风格或专业领域进行输出。
2. **任务描述**：清晰地说明需要完成的任务目标，确保模型理解用户的意图。
3. **任务规划**：定义模型需要遵循的特定规则、步骤或行为准则。
4. **输出格式要求**：指定模型输出的具体格式，如列表、表格、Json格式等。
5. **限制条件**：设置一些约束条件，比如避免使用某些词语、不引用未公开的信息或者保持中立立场等。
6. **安全与伦理指导**：强调模型应遵守的安全和伦理标准，防止生成不当内容。

注意，few-shots和其他用户输入请使用HumanMassage配合输入。

由于json格式使用到'{','}'等字符，会与langchain的prompt格式冲突，因此在使用本示范的参考格式中，指定json输出格式不需要进行额外更改，在load_prompt_template()函数中自动将json的'{','}'转换为'{{','}}'。基于langchain的变量在.md文件中以'<<','>>'格式包裹，并在load_prompt_template()函数中自动转换为PromptTemple输入参数。

--------------------------------

参数输入示例：
<<TASK_DESCRIPTION>>, <<binding_tools>>


任务规划示例：

## Task Planning
1. **Understand the Problem**  
   - Carefully analyze the task description to identify:  
     - **Objectives**: What is the primary goal of the task?  
     - **Constraints**: Are there limitations (e.g., runtime, memory, dependencies)? 
     - **Expected Outcomes**: What should the final result look like?  
   - Clarify any ambiguities by asking for additional details if needed.
2. **Design the Solution**  
   - Decide on the tools and technologies required:  
     - Use **Python** for tasks involving data manipulation, algorithm design, or complex logic.  
     - Use **Bash** for system-level operations, file management, or executing shell commands.  
     - If both Python and Bash are needed, plan how they will interact (e.g., calling shell commands from Python using `subprocess`, or chaining scripts).  
   - Break the solution into logical steps:  
     - Define inputs, processing steps, and outputs for each stage.  
     - Identify potential edge cases or error scenarios.
3. **Implement the Solution**  
   - Write clean, modular, and well-documented code:  
     - Use **Python** for computational tasks, leveraging libraries like NumPy, pandas, or others as needed.  
     - Use **Bash** for lightweight scripting, file operations, or environment setup.  
     - Ensure seamless integration if combining tools (e.g., use Python’s `os` or `subprocess` modules to invoke Bash commands).  
   - Include debugging statements (`print(...)` in Python or `echo` in Bash) to track intermediate results and troubleshoot issues.
   ...
   ...


限制条件、安全与伦理指导示例：

## Notes: 
 - Scope Limitations
   - This script is designed to handle inputs within the range [0, 1000]. Inputs outside this range may produce undefined behavior.
   - The solution assumes that input files are formatted correctly (e.g., CSV with headers). Malformed files may cause errors.
   - Memory usage is optimized for datasets up to 1GB. Larger datasets may require additional optimization or distributed processing.
 - Security Guidelines
   - Avoid hardcoding sensitive information (e.g., API keys, passwords) in the code. Use environment variables or secure vaults instead.
   - Ensure that file operations (e.g., reading/writing) are performed in a secure directory with appropriate permissions.
   - Validate all user inputs to prevent injection attacks (e.g., SQL injection, command injection).
   - If using external libraries, ensure they are from trusted sources and regularly updated to patch vulnerabilities.
  ...
  ...


输出格式示例：

## Output format:
 - The output must strictly follow the JSON format. 2.
 - The structure and field requirements of JSON data are as follows (field types and descriptions are labeled as comments):
```json
{
  "id": str， // the id of given object
  "price": float, // price of object, retain two decimal places
  "availability": bool, // Whether the item is available (true or false)
  "categories": [str], // an array of category tags, containing at least one category
  "metadata": { // Metadata object
    "createdDate": str, // Creation date, in the format ”YYYY-MM-DD”
    "author": str // the name of the creator, non-empty string
  }
}


