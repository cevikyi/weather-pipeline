#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-weather-pipeline-cevikyi}"
LOCATION="${LOCATION:-EU}"

gcloud config set project "${PROJECT_ID}"
gcloud services enable bigquery.googleapis.com

if ! bq show "${PROJECT_ID}:raw" >/dev/null 2>&1; then
  bq --location="${LOCATION}" mk --dataset "${PROJECT_ID}:raw"
fi
bq show "${PROJECT_ID}:raw"
