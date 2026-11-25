import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib                                     # modeli dosyaya yazar, scikit-learn ile geliyor
import numpy as np
import pandas as pd
from google.cloud import bigquery
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit, cross_val_score


PROJECT_ID = os.environ["PROJECT_ID"]             # .env'den ya da GitHub'dan gelir
OUT_DIR = Path("artifacts")                       # modelin yazılacağı klasör
TEST_DAYS = 365
MIN_ROWS = 1000                                   # bundan az gün varsa geçmiş kaybolmuş demektir

FEATURES = [
    "temp_max", "lag1", "lag2", "lag7", "lag28",
    "temp_rolling_3", "temp_rolling_7", "temp_rolling_28",
    "month", "day_of_year", "sin", "cos",
]

def load_data():
    client = bigquery.Client(project= PROJECT_ID)   # gcloud girişinle bağlanır
    df = client.query("""
    select weather_date, temp_max
    from analytics.daily_weather
    where weather_date <= current_date('Europe/Istanbul')   -- bitmemiş günleri alma
    order by weather_date
""").to_dataframe()
    df["weather_date"] = pd.to_datetime(df["weather_date"])
    return df


def make_features(df):
    df = df.sort_values("weather_date").reset_index(drop=True)   # shift'lerden önce sırala
    df["lag1"] = df["temp_max"].shift(1)
    df["lag2"] = df["temp_max"].shift(2)
    df["lag7"] = df["temp_max"].shift(7)
    df["lag28"] = df["temp_max"].shift(28)
    df["temp_rolling_3"] = df["temp_max"].rolling(3).mean()
    df["temp_rolling_7"] = df["temp_max"].rolling(7).mean()
    df["temp_rolling_28"] = df["temp_max"].rolling(28).mean()
    df["month"] = df["weather_date"].dt.month
    df["day_of_year"] = df["weather_date"].dt.dayofyear
    gun = (df["weather_date"] + pd.Timedelta(days=1)).dt.dayofyear   # tahmin edilen günün mevsimi
    df["sin"] = np.sin(2 * np.pi * gun / 365.25)
    df["cos"] = np.cos(2 * np.pi * gun / 365.25)
    return df

def make_training_rows(df):
    df = make_features(df)
    df["target"] = df["temp_max"].shift(-1)       # ertesi gün
    return df.dropna(subset=FEATURES + ["target"])

def select_model(development):
    models = {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(random_state=42),
    }
    tscv = TimeSeriesSplit(n_splits=52, test_size=7)   # haftada bir eğitim, bir yıl
    results = {}
    for name, model in models.items():
        scores = -cross_val_score(
            model, development[FEATURES], development["target"],
            cv=tscv, scoring="neg_mean_absolute_error", n_jobs=-1,
        )
        results[name] = scores.mean()
    print("CV:", {name: round(float(mae), 3) for name, mae in results.items()})
    best_name = min(results, key=results.get)     # en küçük hatalı modelin adı
    return best_name, models[best_name]


def evaluate(model, development, final_test):
    model.fit(development[FEATURES], development["target"])
    return {
    "model_mae": mean_absolute_error(final_test["target"], model.predict(final_test[FEATURES])),
    "baseline_mae": mean_absolute_error(final_test["target"], final_test["temp_max"])
    }


def save(model, metadata):
    OUT_DIR.mkdir(exist_ok=True)                  # klasör yoksa aç
    joblib.dump(model, OUT_DIR / "model.joblib")
    (OUT_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2))



def main():
    df = load_data()
    if len(df) < MIN_ROWS:
        sys.exit(f"Sadece {len(df)} gün var, geçmiş eksik. Model eğitilmedi.")

    rows = make_training_rows(df)
    development, final_test = rows.iloc[:-TEST_DAYS], rows.iloc[-TEST_DAYS:]

    name, model = select_model(development)
    metrics = evaluate(model, development, final_test)
    print(name, metrics)
    if metrics["model_mae"] >= metrics["baseline_mae"]:
        sys.exit("Model baseline'ı geçemedi, kaydedilmedi.")

    model.fit(rows[FEATURES], rows["target"])     # bütün veriyle yeniden eğit
    save(model, {
        "model": name,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "trained_until": str(rows["weather_date"].max().date()),
        "features": FEATURES,
        **metrics,                                # baseline_mae ve model_mae'yi buraya dök
    })
    print("kaydedildi →", OUT_DIR)


if __name__ == "__main__":
    main()