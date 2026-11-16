#!/usr/bin/env bash
set -euo pipefail                          # bir komut hata verirse dur (setup_gcp.sh'deki gibi)

PROJECT_ID="${PROJECT_ID:-weather-pipeline-cevikyi}"   # .env'den gelir; yoksa bu değer
REPO="cevikyi/weather-pipeline"            # içeri girmesine izin vereceğimiz TEK repo
POOL="github"                              # lobinin adı (biz seçtik)
PROVIDER="weather-pipeline"                # resepsiyonun adı (biz seçtik)

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
                                           # $( ... ): içindeki komutun çıktısını değişkene koy
                                           # projenin numarasını sorar (ör. 844889087778)
POOL_ID="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}"
                                           # pool'un tam adı; IAM yetkisi verirken lazım


gcloud services enable \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  --project="${PROJECT_ID}"

  if ! gcloud iam workload-identity-pools describe "${POOL}" \
     --project="${PROJECT_ID}" --location=global >/dev/null 2>&1; then
                                           # "describe" pool'u sorar. Yoksa hata verir.
                                           # ! = "değilse": pool YOKSA aşağıdakini yap
                                           # >/dev/null 2>&1 = çıktıyı ve hatayı ekrana basma
  gcloud iam workload-identity-pools create "${POOL}" \
    --project="${PROJECT_ID}" \
    --location=global \
    --display-name="GitHub Actions"        # Console'da görünecek ad
fi


if ! gcloud iam workload-identity-pools providers describe "${PROVIDER}" \
     --project="${PROJECT_ID}" --location=global \
     --workload-identity-pool="${POOL}" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER}" \
    --project="${PROJECT_ID}" \
    --location=global \
    --workload-identity-pool="${POOL}" \
    --display-name="weather-pipeline repo" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository == '${REPO}'"
fi

MEMBER="principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/${REPO}"
                                           # "bu pool'dan gelen, repository'si REPO olan herkes"

for ROLE in roles/bigquery.jobUser roles/bigquery.dataEditor roles/bigquery.readSessionUser; do
                                           # for: listedeki her rol için aşağıdakini bir kez çalıştır
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="${MEMBER}" \
    --role="${ROLE}" \
    >/dev/null                             # uzun IAM listesini ekrana basma
done

gcloud iam workload-identity-pools providers describe "${PROVIDER}" \
  --project="${PROJECT_ID}" --location=global \
  --workload-identity-pool="${POOL}" \
  --format="value(name)"                   # sadece tam adı yaz: workflow'a bunu vereceğiz