# Single-Cell RNA Sequencing Data Analysis Workflow Guide

This guide outlines a typical workflow for analyzing single-cell RNA sequencing (scRNA-seq) data, from raw data to downstream interpretation, aimed at extracting biological insights from tens of thousands to hundreds of thousands of cells. Many steps are iterative, especially when exploring cellular heterogeneity at different resolutions.

## 1. Raw Data Processing

### Purpose
Convert raw sequencing machine outputs (typically FASTQ files) into a molecule count matrix of genes per cell.

### Description
This is the starting point of the analysis. This step involves aligning/mapping sequencing reads to a reference genome or transcriptome, identifying and correcting cell barcodes (CB), and estimating molecule counts using unique molecular identifiers (UMIs). These steps address errors and biases that may occur during sequencing, such as index hopping and sequencing errors. Common tools include Cell Ranger (commercial software), zUMIs, alevin, kallisto|bustools, STARsolo, and alevin-fry. Some tools generate traditional alignment files (e.g., BAM), while others operate in memory or use more compact representations. Cell barcode correction is typically based on known whitelists or "knee"/"elbow" identification based on frequency distributions. UMI deduplication aims to distinguish PCR duplicates from original mRNA molecules, handling sequencing errors and multimapping reads.

### Personalizable Parts
- Choice of specific processing tool (e.g., alevin-fry is considered fast, accurate, and memory-efficient).
- Choice of reference genome/transcriptome and its version (recommend using splici reference, which includes spliced and unspliced sequences).
- Choice of barcode correction strategy (based on known lists, knee/elbow methods, expected cell numbers, or forced cell numbers).
- Whether to quantify unspliced and ambiguous read information (e.g., USA mode in alevin-fry), which is important for downstream analyses like RNA velocity.
- Strategies for handling doublets or empty droplets.

### Input
- Raw sequencing FASTQ files (typically lane-demultiplexed).
- Reference genome FASTA file and gene annotation GTF file.

### Output
- Cell-gene count matrix (or read matrix, if UMIs are not used).
- Possibly, count matrices for spliced and unspliced reads.
- Quality control metrics report for the raw data processing stage (e.g., mapping rate, UMI duplication rate, distribution of detected genes).

## 2. Quality Control (Count Matrix)

### Purpose
Identify and remove low-quality cells, ambient RNA contamination, and doublets to obtain a high-quality dataset where each observation represents a complete single cell.

### Description
After obtaining the count matrix, quality control is necessary. This includes assessing metrics such as sequencing depth (total counts), number of detected genes, and the percentage of mitochondrial gene counts. Low-quality cells (possibly due to membrane rupture or cell death) typically exhibit low total counts, low gene counts, and high mitochondrial count percentages. Additionally, ambient RNA contamination (extracellular mRNA mistakenly included in droplets) must be corrected using tools like SoupX or DecontX. Doublets (droplets containing multiple cells) must also be detected and handled, as they can distort downstream analyses. Common doublet detection tools include Scrublet, scDblFinder, DoubletDetection, and SOLO.

### Personalizable Parts
- Threshold selection for filtering low-quality cells: can be determined manually based on QC metric distributions or automatically using methods like median absolute deviation (MAD) filtering. Prefer more lenient thresholds to avoid losing rare cell populations.
- Choice of ambient RNA correction tool.
- Choice of doublet detection tool and whether to remove or only flag doublets.
- For multi-batch datasets, perform QC separately for each batch, as quality metric thresholds may differ.
- QC strategies can be reassessed after clustering or annotation.

### Input
- Cell-gene count matrix from raw data processing.

### Output
- Filtered cell-gene count matrix (containing only high-quality cells).
- Updated cell metadata, including QC metrics, ambient RNA correction information, and doublet scores/classifications.

## 3. Normalization

### Purpose
Adjust raw counts to correct for technical variations (e.g., library size, cell size), stabilize variance, and make gene expression comparable across cells.

### Description
Count differences in single-cell data may arise from sampling effects. Normalization aims to remove technical noise while preserving biological heterogeneity. Different normalization techniques have distinct goals and downstream applicability. Common methods include:
- Shifted logarithm: Scaling by library size (e.g., total counts or median counts) followed by adding a pseudo-count (usually 1) and log-transformation. This is a standard step in many workflows.
- scran normalization: Computes size factors based on cell clustering, then scales counts. Commonly used in the Bioconductor ecosystem.
- Analytic Pearson residuals: Fits a regularized negative binomial model to the relationship between count depth and variance, then computes Pearson residuals to better remove technical effects while preserving biological signals.
- SCTransform: An alternative in the Seurat ecosystem that models and stabilizes variance directly on raw UMI counts, replacing traditional normalization, scaling, and variable feature selection steps.

### Personalizable Parts
- Choice of normalization method, as different methods suit different downstream tasks (e.g., Pearson residuals for feature selection).
- For scaling-based methods, choice of size factor calculation (e.g., total counts, median counts, CP10k, CPM).
- For methods like SCTransform, option to regress out covariates (e.g., mitochondrial count percentage).
- Multiple methods can be tested, with results stored as different layers in AnnData objects or different Assay/Layer in Seurat objects for comparison.

### Input
- Filtered cell-gene count matrix from quality control.

### Output
- Normalized gene expression matrix.
- Raw counts are typically retained in a separate layer.

## 4. Feature Selection

### Purpose
Select a subset of genes with the highest information content or variability from normalized data to reduce dimensionality and noise, focusing downstream analyses.

### Description
Most single-cell datasets contain many genes with low expression or minimal variation across cells, which contribute little to distinguishing cell types or states and may introduce noise. Feature selection identifies genes with significant variation, often called highly variable genes (HVGs). Different algorithms (e.g., Seurat, Cell Ranger, Seurat v3 implementations) calculate mean expression and variance to determine HVGs.

### Personalizable Parts
- Choice of HVG selection algorithm or "flavor."
- Number of genes to retain (typically hundreds to thousands, e.g., 500–2000, depending on dataset size and complexity).
- Consideration of normalization method’s impact on HVG selection.
- Methods like SCTransform integrate normalization and HVG selection.

### Input
- Normalized gene expression matrix.

### Output
- List of genes selected as features or markers in the AnnData object’s variables (var).
- Subsequent analyses typically use a matrix containing only these selected features.

## 5. Dimensionality Reduction & Graph Construction

### Purpose
Project high-dimensional gene expression data into a lower-dimensional space for visualization, denoising, and as input for tasks like clustering, while constructing a cell neighborhood graph.

### Description
Single-cell data suffers from the "curse of dimensionality," where noise and redundancy in high dimensions can obscure true signals. Dimensionality reduction creates a new set of informative variables:
- PCA (Principal Component Analysis): A linear method identifying principal components that explain the most variance, used for denoising and initial low-dimensional representation.
- t-SNE (t-Distributed Stochastic Neighbor Embedding) / UMAP (Uniform Manifold Approximation and Projection): Nonlinear methods preserving cell similarities (local and/or global topology) for visualization in 2D or 3D.
- Nearest Neighbor Graph (KNN Graph): Computes distances between cells in the reduced space, constructing a graph where similar cells are connected by edges, serving as the basis for subsequent analyses like clustering or trajectory inference.

### Personalizable Parts
- Choice of dimensionality reduction method (PCA is often the first step, followed by UMAP or t-SNE for visualization; LSI for ATAC data).
- Number of principal components to retain (e.g., determined by elbow plots, explained variance, or biological signal assessment).
- UMAP/t-SNE parameter settings (e.g., perplexity, spread).
- Number of neighbors (k) in the KNN graph, affecting local structure.
- Visualization can assess prior QC results (e.g., viewing QC metrics on UMAP plots).

### Input
- Gene expression matrix from feature selection (or normalized matrix if feature selection is skipped).

### Output
- Low-dimensional embedding coordinates (e.g., X_pca, X_umap in AnnData’s obsm).
- Nearest neighbor graph (e.g., distances, connectivities in AnnData’s obsp).

## 6. Data Integration (Optional)

### Purpose
Remove technical differences (batch effects) when analyzing datasets from different batches, donors, conditions, or technologies, enabling comparison and integration of biological signals.

### Description
Batch effects are a major challenge in scRNA-seq analysis. Integration methods align cells in similar biological states across batches. Integration can occur at various stages, such as after normalization, dimensionality reduction, or as part of clustering. Methods include:
- Linear embedding methods: Mutual Nearest Neighbors (MNN), Seurat’s CCA integration, Harmony, finding similar cells across batches in low-dimensional space.
- Graph-based methods: BBKNN (Batch Balanced KNN), modifying KNN graph construction to enforce cross-batch connections.
- Deep learning methods: scVI, scANVI, scGen, using variational autoencoders (VAEs) to learn batch-corrected low-dimensional representations; scANVI leverages cell labels to preserve biological differences.
- Reference mapping methods: ingest, scArches, Symphony, Seurat’s reference mapping, training models on annotated reference datasets and mapping new (query) data to the reference space.
- Integration quality assessment: Tools like scIB provide metrics to evaluate batch effect removal and biological variation retention.

### Personalizable Parts
- Choice of integration method, depending on batch effect complexity, availability of cell labels, desired output format (corrected embeddings or expression matrices), and computational resources. Benchmarks suggest Harmony and Seurat for simple tasks, deep learning and Scanorama for complex tasks.
- Choice of batch covariates (e.g., sample, donor, dataset), depending on analysis goals; finer batch resolution removes more effects but may confound biological signals.
- Method-specific parameter tuning.
- For labeled data, label harmonization may be needed first.

### Input
- Gene expression data after normalization or feature selection.
- Preliminary dimensionality reduction and graph construction results, if applicable.
- Cell metadata column indicating batch information.
- Cell labels for label-aware methods or reference mapping.

### Output
- Integrated data representation (e.g., batch-corrected low-dimensional embeddings or expression matrices).
- Integrated nearest neighbor graph.

## 7. Clustering

### Purpose
Group cells with similar gene expression patterns into clusters, representing potential cell types or states.

### Description
Clustering is a common unsupervised machine learning task. In single-cell analysis, a nearest neighbor graph is built in the reduced space, and graph-based clustering algorithms (e.g., Leiden, Louvain) identify communities by optimizing modularity. Clustering forms the basis for subsequent cell type annotation.

### Personalizable Parts
- Choice of clustering algorithm (Leiden is recommended for well-connected communities).
- Resolution parameter, controlling cluster granularity (higher values yield more, smaller clusters; optimal resolution depends on dataset size).
- Input for clustering: unintegrated or integrated dimensionality reduction embeddings and graphs.
- Sub-clustering to further subdivide cell populations of interest.

### Input
- Nearest neighbor graph from dimensionality reduction or data integration.
- Corresponding low-dimensional embeddings (for visualizing clustering results).

### Output
- Cluster labels for each cell (typically stored in AnnData’s obs).

## 8. Annotation

### Purpose
To assign biological meaning to the identified cell clusters, labeling them as specific cell types or states. For identification of malignant cells in cancer samples, features of Copy Number Variation (CNV) can be leveraged.

### Description
Cell type definition is based on specific marker genes, typically robust across datasets. Annotation can be:
- Manual annotation: Based on known marker genes, visualizing their expression across clusters to identify cell types. This is intuitive but may be subjective without unique markers or in complex datasets.
- Automated annotation: Using pre-trained classifiers to predict cell types based on gene expression patterns, leveraging machine learning for speed and existing high-quality annotations.
- Reference mapping: Mapping the dataset to a well-annotated reference atlas and transferring labels to query cells, dependent on reference quality and dataset similarity. Cell types can be further subdivided into subtypes or states, with some researchers using "cell identity" to avoid this distinction.
- Inference of Copy Number Variation (CNV): For tumor samples, malignant cells often exhibit significant CNVs. Tools like infercnv and copycat can infer CNVs from single-cell RNA sequencing data, thereby aiding in the identification of malignant cell populations. These tools work by analyzing the average expression levels of genes across chromosomes and comparing them to normal cells to identify regions of copy number gain or loss.

### Personalizable Parts
- Choice of annotation strategy: manual, automated classifier, or reference mapping.
- For manual annotation, selection of marker gene sets, validated with biological expertise and specific to the tissue and experiment.
- For automated or reference mapping, selection of appropriate pre-trained models or reference atlases, ensuring technical and biological similarity to query data.
- When using infercnv or copycat for CNV inference, a set of known normal cells must be provided as a reference. The selection of these reference cells is crucial and can be based on annotated non-malignant cell types or single-cell data from healthy individuals.
- Annotation granularity (e.g., broad cell types vs. finer subtypes/states).

### Input
- Cell cluster labels from clustering.
- Normalized gene expression matrix.
- Low-dimensional embeddings from dimensionality reduction or data integration (for visualizing marker gene expression).
- Pre-trained classifier models or annotated reference datasets for automated or reference mapping methods.
- For infercnv/copycat: Requires the specification of a normal cell population (based on initial annotation or other prior knowledge).

### Output
- Biological labels for each cell or cluster (e.g., stored in AnnData’s obs).

## 9. Iterative Subpopulation Definition and Analysis Loop

### Purpose
Identify and analyze finer subpopulations or cell states at higher resolution.

### Description
After identifying broad cell types through initial clustering and annotation (step 8), deeper analysis of specific cell populations is often needed to reveal finer subpopulation structures or cell states. This is an iterative process that may be repeated multiple times.

#### Process
- **Select Subpopulation for In-depth Analysis**: Based on initial annotations (step 8) and your biological research questions, select specific cell types or clusters for detailed analysis. The choice should align with the biological story you aim to explore or validate, ensuring analysis relevance. Consider which downstream analyses (e.g., trajectory inference for cell state changes, cell-cell communication, or differential expression under specific conditions) are relevant and valuable for the selected subpopulations and research questions, guiding subsequent steps.
- **Subset-specific Feature Selection**: Re-identify highly variable genes or informative features within the selected cell subset, as HVGs in the full dataset may differ from those in specific subpopulations, capturing subset-specific variation.
- **Subset-specific Dimensionality Reduction & Graph Construction**: Using the subset data (based on re-selected features), recompute dimensionality reduction embeddings (e.g., PCA, UMAP/t-SNE) and build a new nearest neighbor graph to better visualize and analyze subpopulation structure.
- **Subset-specific Clustering**: Apply clustering algorithms (e.g., Leiden) on the new nearest neighbor graph to identify finer groupings within the subpopulation.
- **Subset-specific Annotation**: Assign biological labels to new subpopulations (sub-clusters), typically by identifying subpopulation-specific marker genes, possibly requiring differential gene expression analysis to find significantly differentially expressed genes.
- **Perform Subpopulation-specific Downstream Analysis**: Once subpopulations are defined at the desired resolution, perform analyses such as differential gene expression between subpopulations or conditions, trajectory inference (pseudotime, RNA velocity) for continuous processes, cell-cell communication, gene set enrichment and pathway analysis, gene regulatory network inference, perturbation response analysis, or relative abundance changes across conditions.

#### Optional: Re-assess QC
Based on clustering or annotation results (overall or subpopulation-specific), revisit initial QC filtering parameters if necessary (e.g., if clusters show signs of doublets or low-quality cells). This may require rerunning the workflow from step 2.

## 10. Further Downstream Analysis (Advanced)

### Purpose
After preprocessing and core analysis, use processed and annotated single-cell data to explore specific biological questions in depth.

### Description
The core analysis pipeline provides a foundational dataset for advanced analyses, tailored to experimental design and research questions. Covered analyses include:
- **Differential Gene Expression (DGE) Analysis**: Compare gene expression differences between cell populations (e.g., different cell types or conditions). Methods include pseudobulk approaches (edgeR, DESeq2) and single-cell-specific methods (MAST, glmmTMB).
- **Compositional Analysis**: Analyze changes in cell type proportions across conditions, using methods like scCODA, tascCODA, or KNN-based approaches (DA-seq, Milo, MELD).
- **Gene Set Enrichment and Pathway Analysis**: Identify enriched gene sets (e.g., biological processes, signaling pathways) in specific cell populations or conditions, using gene set testing (GSEA, fry, camera) or pathway activity inference (AUCell, Pagoda2, PROGENy, DoRothEA).
- **Pseudotemporal Ordering / Trajectory Inference**: Reconstruct dynamic cell trajectories during development or differentiation based on gene expression similarity, using methods like DPT, Palantir, Slingshot, and PAGA.
- **RNA Velocity**: Infer instantaneous rates and directions of gene expression changes using spliced and unspliced mRNA abundances to predict short-term cell state transitions, analyzed with tools like scVelo.
- **Cell-cell Communication (CCC)**: Infer interactions between cell types based on gene expression, typically via ligand-receptor interactions, using tools like CellPhoneDB, LIANA, and NicheNet (which also considers downstream signaling effects).
- **Gene Regulatory Networks (GRN) Inference**: Model how transcription factors (TFs) regulate target gene expression, using tools like SCENIC to infer regulons via TF-target gene co-expression.
- **Perturbation Modeling**: Analyze or predict cell responses to experimental perturbations (e.g., gene knockouts, drug treatments), using methods like Augur (identifying most affected cell types) and scGen (predicting perturbation responses).
- **Lineage Tracing**: Reconstruct ancestral-descendant relationships and proliferation history using molecular markers (e.g., CRISPR/Cas9 edits), with tools like Cassiopeia and CoSpar. Note: This often requires specialized experimental design and raw data processing, differing from standard scRNA-seq workflows.

### Personalizable Parts
- Choice of downstream analyses depends on specific biological questions and experimental design.
- Each analysis domain offers multiple methods, selected based on data type, question nature, tool characteristics (e.g., speed, accuracy, prior knowledge requirements, multimodal data support).
- Many methods have specific input requirements (e.g., DGE needs normalized counts and condition labels, RNA velocity needs unspliced counts, NicheNet needs gene sets of interest).
- Interpretation of results requires integration with biological context.

### Input
- Processed, integrated (if needed), clustered, and annotated single-cell data from annotation.
- Depending on analysis, may require raw counts, normalized counts, low-dimensional embeddings, graph structures, cell labels, marker genes, experimental conditions, time points, or perturbation information.
- Some analyses (e.g., lineage tracing) require specially processed raw data.
- External databases or knowledge bases (e.g., pathway, ligand-receptor, TF-target gene databases).

### Output
- Analysis-specific results (e.g., differentially expressed gene lists, pathway enrichment scores, cell type proportion changes, pseudotime values, velocity vectors, predicted cell interactions, inferred regulatory networks).