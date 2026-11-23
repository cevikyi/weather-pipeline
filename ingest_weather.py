import argparse                           # komut satırından --dry-run gibi seçenekleri okur
import os                                 # os.environ için
from datetime import datetime, timezone   # ingested_at zamanı için

import requests                           # API'ye istek atmak için
from google.cloud import bigquery         # BigQuery'ye yazmak için
import time

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

URL = "https://api.open-meteo.com/v1/forecast"   # adres artık bir sabit (eskiden requests.get'in içindeydi)
MAX_ATTEMPTS = 5                                  # en fazla kaç kez denensin
RETRY_STATUS = {429, 500, 502, 503, 504}          # "geçici" saydığımız HTTP kodları (yukarıdaki tablo)


class TemporaryError(Exception):                  # kendi hata türümüz: "geçici, tekrar dene" etiketi
    """Tekrar denemeye değer bir hata (429, 5xx)."""

def fetch(past_days):                             # past_days artık dışarıdan geliyor (bölüm c)
    for attempt in range(1, MAX_ATTEMPTS + 1):    # attempt sırayla 1, 2, 3, 4, 5 olur
        try:                                      # "bu bloğu dene; hata çıkarsa except'e atla"
            resp = requests.get(
                URL,
                params={
                    "latitude": LAT,
                    "longitude": LON,
                    "hourly": "temperature_2m",
                    "past_days": past_days,       # eskiden sabit 1'di
                    "forecast_days": 2,
                },
                timeout=30,                       # 30 sn cevap yoksa Timeout hatası
            )
            if resp.status_code in RETRY_STATUS:  # 429 ya da 5xx geldiyse
                raise TemporaryError(f"HTTP {resp.status_code}")   # "geçici" etiketiyle hata fırlat → except'e
            resp.raise_for_status()               # 400/404 gibi kalıcı hata → hata fırlatır ama except YAKALAMAZ → script durur
            return resp.json()                    # başarılı: veriyi döndür, döngü biter
        except (requests.Timeout, requests.ConnectionError, TemporaryError) as err:   # sadece bu üç tür yakalanır
            if attempt == MAX_ATTEMPTS:           # son denemeydi
                raise                             # pes et: hatayı yukarı gönder → kırmızı run
            wait = 15 * 2 ** (attempt - 1)        # 15·1, 15·2, 15·4, 15·8 → 15, 30, 60, 120 sn
            print(f"Deneme {attempt}/{MAX_ATTEMPTS} olmadı ({err}). {wait} sn bekleyip tekrar deniyorum.", flush=True)
            # flush=True: mesajı bekletmeden hemen yaz (yoksa Actions logunda iş bitene kadar görünmeyebilir)
            time.sleep(wait)



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

    parser.add_argument("--past-days", type=int, default=1)
    # "--past-days 5" yazılırsa args.past_days = 5 (type=int: yazıyı sayıya çevir); yazılmazsa 1

    args = parser.parse_args()
    # terminalde gerçekte ne yazıldığını oku → args.dry_run True ya da False olur

    ingested_at = datetime.now(timezone.utc).isoformat()
    # şu anki zaman (UTC), BİR KEZ, en başta → bu çalıştırmanın tüm satırlarına aynısı yazılacak

    rows = to_rows(fetch(args.past_days), ingested_at)
    # önce API'den veriyi al (fetch), sonra satırlara çevir (to_rows)

    if args.dry_run:
        # deneme modu: BigQuery'ye dokunma, sadece ekrana yaz
        print(len(rows), "satır")
        for r in rows[:3]:      # ilk 3 satırı göster
            print(r)
    else:
        # normal mod: satırları BigQuery'ye yükle
        load(rows)