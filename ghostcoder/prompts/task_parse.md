Generate an instruction to guide another agent in performing the next step of a bioinformatics workflow based on the given task description and the previous code segment. The instruction should include:

 - The next step in the analysis workflow.
 - Recommended Python tools for this step.
 - Suggestions for visualization using plotting tools.
 - Ensure the instruction is clear, concise, and in English.

For example, if the task is 'Perform RNA-seq data analysis to identify differentially expressed genes' and the previous step is 'Data preprocessing and quality control', the instruction could be: 'The next step is to perform alignment using tools like STAR or HISAT2, and then conduct differential expression analysis using DESeq2 or edgeR. For visualization, use matplotlib to create volcano plots or seaborn for heatmaps to illustrate the results.'