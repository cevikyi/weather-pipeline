import argparse                           # komut satırından --dry-run gibi seçenekleri okur
import os                                 # os.environ için
from datetime import datetime, timezone   # ingested_at zamanı için

import requests                           # API'ye istek atmak için
from google.cloud import bigquery         # BigQuery'ye yazmak için


PROJECT_ID = os.environ["PROJECT_ID"]       # terminaldeki nottan
TABLE = f"{PROJECT_ID}.raw.weather_hourly"  # proje.dataset.tablo
LOCATION_ID = "istanbul"                    # raw'daki location_id kolonuna yazılacak isim
LAT, LON = 41.01, 28.98                     # şehrin enlem/boylamı


SCHEMA = [
    bigquery.SchemaField("location_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("valid_time", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("temperature_2m", "FLOAT"),
]



def fetch():
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": LAT,
            "longitude": LON,
            "hourly": "temperature_2m",
            "past_days": 1,
            "forecast_days": 2,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()



def to_rows(payload,ingested_at):
    hourly = payload["hourly"]
    rows = []
    for t,temp in zip(hourly["time"],hourly["temperature_2m"]):
        row = {
        "location_id": LOCATION_ID,
        "valid_time": t,
        "ingested_at": ingested_at,
        "temperature_2m": temp
        }
        rows.append(row)
    return rows


def load(rows):
    client = bigquery.Client(project=PROJECT_ID)
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    job = client.load_table_from_json(rows, TABLE, job_config=job_config)
    job.result()
    print(f"{len(rows)} satır yüklendi → {TABLE}")

if __name__ == "__main__":
    # "python ingest_weather.py" diye çalıştırılınca buradan başla

    parser = argparse.ArgumentParser()
    # terminalde script adından sonra yazılan seçenekleri okuyacak bir okuyucu oluştur

    parser.add_argument("--dry-run", action="store_true")
    # "--dry-run" adında bir seçenek tanımla: yazıldıysa True, yazılmadıysa False

    args = parser.parse_args()
    # terminalde gerçekte ne yazıldığını oku → args.dry_run True ya da False olur

    ingested_at = datetime.now(timezone.utc).isoformat()
    # şu anki zaman (UTC), BİR KEZ, en başta → bu çalıştırmanın tüm satırlarına aynısı yazılacak

    rows = to_rows(fetch(), ingested_at)
    # önce API'den veriyi al (fetch), sonra satırlara çevir (to_rows)

    if args.dry_run:
        # deneme modu: BigQuery'ye dokunma, sadece ekrana yaz
        print(len(rows), "satır")
        for r in rows[:3]:      # ilk 3 satırı göster
            print(r)
    else:
        # normal mod: satırları BigQuery'ye yükle
        load(rows)