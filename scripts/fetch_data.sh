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

Not used: MIMIC-IV. Its data use agreement forbids redistribution.
Not used yet: MedMCQA, PubMedQA. Licences unresolved.
TXT
