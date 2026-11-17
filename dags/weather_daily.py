
from pathlib import Path                           # dosya yollarıyla çalışmak için
from datetime import timedelta                     # "5 dakika" gibi süreler için (retry_delay)

import pendulum                                    # saat dilimli tarih (Airflow ile birlikte kuruldu)
from airflow.providers.standard.operators.bash import BashOperator   # komut çalıştıran task tipi
from airflow.sdk import DAG                        # DAG'in kendisi

PROJECT_DIR = Path.home() / "weather-pipeline"     # /Users/sen/weather-pipeline; Path.home() = ~

with DAG(
    dag_id="weather_daily",                        # arayüzde görünecek isim
    schedule="17 6 * * *",                         # daily.yml ile aynı cron ifadesi
    start_date=pendulum.datetime(2026, 11, 17, tz="Europe/Istanbul"),  # bu tarihten itibaren; cron İstanbul saatiyle okunur
    catchup=False,                                 # kaçırılan günlerin hepsini sonradan çalıştırma
    default_args={                                 # her task'a uygulanacak ortak ayarlar
        "retries": 2,                              # hata verirse 2 kez daha dene
        "retry_delay": timedelta(minutes=5),       # denemeler arası 5 dk bekle
    },
    tags=["weather"],                              # arayüzde filtrelemek için etiket
) as dag:

    ingest = BashOperator(
        task_id="ingest",                                              # kutunun adı
        bash_command="source .env && .venv/bin/python ingest_weather.py",  # PROJECT_ID'yi yükle, sonra ingest
        cwd=str(PROJECT_DIR),                                          # komutu repo klasöründe çalıştır
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="source .env && .venv/bin/dbt build --target prod --profiles-dir .",  # profiles.yml'yi bu klasörde ara
        cwd=str(PROJECT_DIR),
    )

    ingest >> dbt_build