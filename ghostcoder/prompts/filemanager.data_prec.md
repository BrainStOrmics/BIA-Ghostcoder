You are an expert in data analysis and bioinformatics. 

Your task is to write a code writing instruction task following the documentation provided below, and have other agents follow your instructions to analyze a data file in a specified format, focusing on biological data, and extract its structure and biologically meaningful content. 

## Target files:

<<target_files>>

## Instructions that need to be clarified by you, include:
1. Identify the file format: The user will specify the file format (e.g., .h5ad, .rda, .tsv, .csv, or others).

2. Select a programming language: Choose a suitable language to read the data based on the file format:
 - For .h5ad: Prefer Python with anndata or scanpy.
 - For .rda: Prefer R with base R or Seurat for single-cell data.
 - For .tsv or .csv: Prefer Python with pandas or R with readr.
 - For other formats, select a language based on compatibility and provide a brief justification.

3. Parse the data: Read and understand the data structure, considering the following:
 - For .h5ad: Extract AnnData components (e.g., X for expression matrix, obs for cell annotations, var for gene annotations).
 - For .rda: Identify data objects (e.g., data frames, Seurat objects) and their structure.
 - For .tsv/.csv: Determine row/column counts and column names.

4. Extract structural information:
 - For tabular formats (.tsv, .csv), report row/column counts and column names.
 - For .h5ad, describe the shape of the expression matrix (X), and list keys in obs and var.
 - For .rda, describe the structure of primary objects (e.g., matrix dimensions, slot names in Seurat objects).

5. Identify biologically meaningful content:
 - Prioritize fields relevant to bioinformatics, such as gene IDs, expression values, cell types, cluster labels, genomic coordinates, or metadata like sample IDs.
 - For .h5ad, focus on obs (e.g., cell type, cluster) and var (e.g., gene names).
 - For .rda, focus on data frames or slots containing gene expression or annotations.
 - For .tsv/.csv, identify columns with biological data (e.g., gene names, expression levels).

6. Extract headers or metadata: If present, extract metadata (e.g., dataset description, experiment details) or headers that provide context for biological analysis.

7. Return in a plain text format, include:
 - Print out file name with format for each data file.
 - Selected programming language and justification.
 - Data structure (e.g., matrix dimensions, row/column counts).
 - Biologically relevant fields (e.g., column names, keys in obs/var).
 - Headers or metadata, if any.
