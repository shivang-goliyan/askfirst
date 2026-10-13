#!/usr/bin/env bash
# Prints where each dataset comes from and under what terms. It deliberately does not download
# anything on your behalf: read the licence, then fetch what you need into its own directory
# under data/ so that nothing from a download can shadow a module in this project.
set -euo pipefail

cat <<'TXT'
DDXPlus          CC-BY
                 https://figshare.com/articles/dataset/DDXPlus_Dataset/20043374
                 -> data/ddxplus/

MedQA            MIT
                 https://github.com/jind11/MedQA
                 -> data/medqa/

CIViC            CC0 1.0 (data), MIT (their code)
                 bulk:  https://civicdb.org/releases
                 aws:   s3://civic-bulk-data/   (no account needed, use --no-sign-request)
                 -> data/civic/

ClinVar          terms not yet confirmed - read them first
                 https://ftp.ncbi.nlm.nih.gov/pub/clinvar/
                 -> data/clinvar/

NHAMCS           US government work, public use file - BUT read the NCHS data use
(real ED visits) agreement in each year's readme before you touch it: statistical analysis
                 only, no attempt to identify any person or establishment, and NO LINKAGE with
                 individually identifiable data from any other source. Sanctions are criminal.
                 data:   https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHAMCS/
                         ed2018.zip ed2019.zip ed2021.zip ed2022.zip
                 layout: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHAMCS/
                         doc18-ed-508.pdf doc19-ed-508.pdf doc21-ed-508.pdf doc22-ed-508.pdf
                 -> data/nhamcs-raw/
                 then:   pdftotext -layout data/nhamcs-raw/doc22-ed-508.pdf data/nhamcs-raw/doc22.txt
                         (and the same for 18, 19, 21)
                         python3 scripts/nhamcs_layout.py data/nhamcs-raw
                 The layout script checks itself: the declared field widths must sum to the
                 actual record length, which is 2458 for 2018 and 2382 for 2022.

Not used: MIMIC-IV. Its data use agreement forbids redistribution.
Not used yet: MedMCQA, PubMedQA. Licences unresolved.
TXT
