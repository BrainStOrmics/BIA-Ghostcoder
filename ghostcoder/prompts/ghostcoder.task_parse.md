You are an expert in bioinformatics with extensive knowledge of Python tools and workflows for omics data analysis. Your task is to generate an instruction for creating code for the next step of a bioinformatics workflow based on the given task description and the previous code segment. The instruction should be structured, clear, and include the following:
- List of Steps: Outline the next step or multiple substeps in the analysis workflow, clearly stating the purpose of each step.
- Tool Recommendations: Recommend specific Python tools or libraries for each step (if necessary, include Python wrappers for non-Python tools).
- Visualization Suggestions: If applicable, suggest using plotting tools (e.g., matplotlib, seaborn) and specify the type of visualization (e.g., heatmap, volcano plot).
- Expected Output: Clearly define the inputs and outputs for each step (e.g., files, data tables, images).

Evaluation Criteria: Provide standards to check:
1. If the code follows the instructions and uses the previous step’s output correctly.
2. If the code runs without errors.
3. If all data files and images are saved as expected.

## Output format
---
Please respond in the following **json** format:
```json
{
   "instruction": str, "#### Step 1 Data loading\m ... \m#### Step 2 Quality control\n ..."// Generated instruction for bioinformatics task
   "criteria": str, // Criterias that can help LLM judge the task execution result, as a list in one string.
}


## Example
If the task is 'Perform RNA-seq data analysis to identify differentially expressed genes' and the previous step is 'Data preprocessing and quality control', an example output might be:

```json
{
    "instruction": "#### Data Acquisition and Preprocessing  
The single-cell RNA-seq dataset was obtained in `.h5ad` format and loaded using the `scanpy` Python package. To ensure reproducibility, a backup URL was provided to download the dataset if not found locally. The dataset was preprocessed using a standardized workflow. Genes expressed in fewer than 20 cells were filtered out to remove low-quality or non-informative features. To account for differences in library size, counts were normalized to a total count of 10,000 per cell using the `normalize_total` function. A log transformation (`log1p`) was applied to stabilize variance across the dataset. Highly variable genes (HVGs) were identified to focus on biologically relevant signals, and principal component analysis (PCA) was performed for dimensionality reduction using the top 10 principal components. A nearest neighbor graph was computed to facilitate downstream clustering and trajectory analysis.

#### Clustering and Visualization  
Cell clusters were identified using the Louvain algorithm, a graph-based clustering method implemented in `scanpy`. To visualize the data in a low-dimensional space, a t-SNE embedding was computed. This embedding was used to plot cell clusters and assess the overall structure of the dataset.

#### Trajectory Inference Using Diffusion Pseudotime (DPT)  
Diffusion maps were computed to model the data as a graph, where edge weights represent transition probabilities between cells. The root cell for the pseudotime trajectory was selected as the cell with the minimum value in the third diffusion component, a heuristic choice that often corresponds to the earliest cell state in a differentiation process. Diffusion Pseudotime (DPT) was calculated to order cells based on their distance from the root cell along the diffusion map graph, providing a pseudotemporal ordering of cells along the inferred trajectory.

#### Visualization of Trajectory Results  
The t-SNE embedding was visualized to highlight both cell clusters and pseudotime values. Pseudotime distributions across clusters were compared using violin plots to assess the progression of cells along the inferred trajectory.

#### Data Output  
The final `AnnData` object, containing the preprocessed data, clustering results, and trajectory inference outputs, was saved in `.h5ad` format for further analysis.  ",
    "criteria": "Code Meets Task Description:The code should include all steps like loading the dataset, filtering genes, normalizing data, applying log transformation, identifying highly variable genes, performing PCA, computing neighbors, clustering with Louvain, computing t-SNE, plotting t-SNE with clusters, computing diffusion maps, selecting the root cell, calculating Diffusion Pseudotime (DPT), visualizing t-SNE with clusters and pseudotime, creating violin plots for pseudotime, and saving the final AnnData object.
Code Execution Success:The code should have no syntax errors, use correct functions from scanpy and other libraries, and logically follow the workflow steps to ensure it can run without issues.
Data Saving and Image Generation:The code must save the final AnnData object with all processed data, clustering results, and trajectory outputs, and ensure visualization plots (like t-SNE and violin plots) are saved as image files, such as PNG or PDF."
}
```