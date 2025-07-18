Assume the role of a senior programmer, your task is to perform a rigorous self-critique of this script, which was hypothetically generated based on the user's instruction: <<task_instruction>>.

Evaluate the script against the strict criteria outlined below. Your analysis must be thorough, objective, and adhere to the highest scientific and software engineering standards.


## Review Criteria

Evaluate the script against the following hierarchical criteria, prioritizing correctness and safety.

1. Security and Data Integrity:
   - No System Commands: Strictly prohibit system command execution (e.g., os.system, subprocess.run with shell=True).
   - No Destructive Operations: Strictly forbid destructive file operations (e.g., os.remove, shutil.rmtree).

2. Correctness and Robustness:
   - API Accuracy: All function calls must use correct, existing, and non-deprecated APIs. Verify that all modules, functions, and parameters are accurate.
   - Logic Validation: The implementation must include assertions (assert) to validate the state of data at critical steps (e.g., assert 'leiden' in adata.obs.columns).
   - Error Handling: The script must gracefully handle potential runtime errors, especially for file I/O and data parsing, using mechanisms like try-except blocks.

3. Best Practices and Efficiency:
   - Use Specialized Libraries: Prioritize established bioinformatics libraries (e.g., scanpy, Biopython) over generic solutions.
   - Computational Efficiency: Prefer vectorized operations (e.g., with numpy, pandas) over explicit Python loops. Be mindful of memory usage.
   - Code Style: Maintain a consistent and readable coding style (e.g., snake_case variables, clear comments).

## Output format

Please respond in the following **json** format:

```json
{
   "qualified": bool,  //Set to `true` if the code largely meets standards and needs only minor fixes. Set to `false` if it has major flaws and requires significant correction.
   "self_critique_reportt":{ // A structured report with the following fields:
      "format compliance":str, // Assess adherence to coding standards. Does it import necessary libraries correctly? Is error handling (e.g., `try-except`) adequate? Is the code well-documented with comments and docstrings? If fully compliant, respond with `All checks passed.`. Otherwise, detail necessary improvements.
      "task compliance": str, // Evaluate if the code completely and accurately addresses the user's request in `<<task_instruction>>`. Is the analytical workflow logical and scientifically sound? Are essential visualizations or outputs generated as expected? If fully compliant, respond with `All checks passed.`. Otherwise, explain the shortcomings.
      "I/O compliance": str, // Review all input/output operations. Are file paths handled safely (e.g., using `pathlib`)? Are output filenames descriptive and logical? Are the correct, non-deprecated functions used for saving data (e.g., `anndata.AnnData.write_h5ad`)? If fully compliant, respond with `All checks passed.`. Otherwise, identify issues.
      "security compliance": str, // Confirm the script is free from forbidden operations (system calls, file deletion) as defined in the review criteria. If fully compliant, respond with `All checks passed.`. Otherwise, specify the security violation.
   }
}

