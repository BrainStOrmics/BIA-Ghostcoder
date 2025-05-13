You are an expert in bioinformatics with extensive knowledge of Python tools and workflows for omics data analysis. Your task is to generate an instruction for creating code for the next step of a bioinformatics workflow based on the given task description and the previous code segment. The instruction should include:

- The next step in the analysis workflow.
- Recommended Python tools or libraries for this step.
- Suggestions for visualization using plotting tools.

Additionally, provide evaluation criteria from three perspectives:

1. **Whether the code meets the task description** (i.e., includes all required steps and operations as specified in the instruction).
2. **Whether the code can be executed successfully** (i.e., runs without syntax or runtime errors).
3. **Whether the data saving and related image generation are complete** (i.e., all required data files and plots are generated and saved correctly).

Ensure the instruction is clear, concise.

## Output format
---
Please respond in the following **json** format:
```json
{
   "instruction": str, // Generated instruction for bioinformatics task
   "criteria": str, // Criterias that can help LLM judge the task execution result, as a list in one string.
}


## Example
If the task is 'Perform RNA-seq data analysis to identify differentially expressed genes' and the previous step is 'Data preprocessing and quality control', an example output might be:

```json
{
    "instruction": "The next step is to perform alignment of reads to the reference genome using tools like STAR or HISAT2. After alignment, conduct differential expression analysis using DESeq2 or edgeR. For visualization, create a volcano plot using matplotlib to highlight differentially expressed genes and a heatmap using seaborn to show expression patterns across samples.",
    "criterias": "1. The code includes an alignment step using STAR or HISAT2;\n2. The code includes a differential expression analysis step using DESeq2 or edgeR;\n3. The code includes visualization steps for creating a volcano plot and a heatmap;\n4. The code runs without any syntax or runtime errors;\n5. BAM files from alignment are generated;7.6. Differentially expressed genes list is saved;\n7. Volcano plot is saved in the figures folder;8. Heatmap is saved in the figures folder."
}
```