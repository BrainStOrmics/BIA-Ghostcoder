Extract all steps from the provided bioinformatics analysis plan. For each step, extract task description, including the step name and any subsequent details. Output all such description as a list.

## Example:
If the plan is:

```
## 🧪 3. Analytical pipeline

### Step 1. Data preparation 

Ensure that fastq.gz files are organized for all samples.
Prepare reference genome index (Genome index) and annotation files (GTF/GFF3).

### Step 2. Quality Control

QC using FastQC and MultiQC.
```

Then the output should be:

```json
[
  "Data preparation \n\nEnsure that fastq.gz files are organized for all samples.\nPrepare reference genome index (Genome index) and annotation files (GTF/GFF3).",
  "Quality Control \n\nQC using FastQC and MultiQC.",
  ... ...
]
```
