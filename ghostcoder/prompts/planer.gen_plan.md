Create a comprehensive bioinformatics analysis plan in natural language based on the following details:

## Analysis Objective: 

<<objective>>

## Data Files: 

List the data files with brief descriptions here.
<<data_files>>

## The plan should include:

1. A step-by-step description of the analysis workflow.
2. For each step, recommend the software or tools to be used.
3. Ensure that the workflow is tailored to the characteristics of the provided data files (e.g., file formats, sequencing type, etc.) and aligns with the analysis objective.
4. If applicable, mention any key considerations or decisions that need to be made during the analysis, such as quality control thresholds, parameter settings, or handling of specific data types.
5. Recommended 4-6 ploting for visualizing results.
6. Present the plan in a clear, structured format, such as a numbered list of steps, with each step including a description and the tools required.


## Example Structure of the Output Plan:

"""

## 🧬 1. Analysis Objective:

Starting from the original FASTQ sequencing files, comparative, quantitative, normalization and differential expression analyses were performed to identify genes that were significantly differentially expressed under different experimental conditions.

## 📁 2. Input files:

data/
├── sample1_R1.fastq.gz
├── sample1_R2.fastq.gz
...

## 🧪 3. Analytical pipeline

### Step 1. Data preparation 

Ensure that fastq.gz files are organized for all samples.
Prepare reference genome index (Genome index) and annotation files (GTF/GFF3).

### Step 2. Quality Control

QC using FastQC and MultiQC.

### Step 3. ...

... ...


"""