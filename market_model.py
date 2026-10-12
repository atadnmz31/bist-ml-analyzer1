from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import warnings

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


class TickerDataError(RuntimeError):
    pass


def normalize_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if ticker.endswith(".IS"):
        return ticker
    return f"{ticker}.IS"


def download_history(ticker: str, period: str = "10y") -> pd.DataFrame:
    symbol = normalize_ticker(ticker)
    try:
        data = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
    except Exception as exc:
        raise TickerDataError(f"{symbol} verisi alınamadı. İnternet bağlantısını ve hisse kodunu kontrol edin.") from exc

    if data is None or data.empty or "Close" not in data.columns:
        raise TickerDataError(
            f"{symbol} için tarihsel veri bulunamadı. Kodun doğru olduğunu ve veri sağlayıcının bu sembolü desteklediğini kontrol edin."
        )

    data = data.copy()
    data = data[~data.index.duplicated(keep="last")].sort_index()
    required = {"Close", "Volume"}
    if not required.issubset(data.columns):
        raise TickerDataError("Veri sağlayıcısından gerekli kapanış/hacim alanları gelmedi.")
    data = data.replace([np.inf, -np.inf], np.nan)
    return data


def make_features(data: pd.DataFrame) -> pd.DataFrame:
    close = data["Close"].astype(float)
    volume = data["Volume"].astype(float)
    daily_return = close.pct_change()

    x = pd.DataFrame(index=data.index)
    for lag in [1, 2, 3, 5, 10, 20]:
        x[f"return_{lag}d"] = close.pct_change(lag)

    for window in [5, 10, 20, 50]:
        moving_average = close.rolling(window).mean()
        x[f"price_vs_sma_{window}"] = close / moving_average - 1
        x[f"volatility_{window}"] = daily_return.rolling(window).std()

    delta = close.diff()
    gains = delta.clip(lower=0).rolling(14).mean()
    losses = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gains / losses.replace(0, np.nan)
    x["rsi_14"] = 100 - (100 / (1 + rs))

    x["volume_change_1d"] = volume.pct_change().replace([np.inf, -np.inf], np.nan)
    volume_avg = volume.rolling(20).mean()
    x["volume_vs_sma_20"] = volume / volume_avg - 1
    x["intraday_range"] = (data["High"] - data["Low"]) / close
    x["close_open_return"] = (close - data["Open"]) / data["Open"].replace(0, np.nan)
    return x.replace([np.inf, -np.inf], np.nan)


def make_dataset(data: pd.DataFrame, horizon: int):
    features = make_features(data)
    future_close = data["Close"].shift(-horizon)
    target = (future_close > data["Close"]).where(future_close.notna()).astype("float")
    dataset = features.copy()
    dataset["target"] = target
    dataset = dataset.dropna(subset=["target"])
    y = dataset.pop("target").astype(int)
    # Keep rows where enough features are available. The pipeline imputes any remaining gaps.
    valid = features.loc[dataset.index]
    return valid, y, features


def new_model() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=5,
            max_features="sqrt",
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )),
    ])


def analyze_ticker(ticker: str, horizon: int) -> dict:
    if horizon not in (1, 5, 20):
        raise ValueError("Tahmin süresi 1, 5 veya 20 işlem günü olmalıdır.")

    data = download_history(ticker)
    features, y, all_features = make_dataset(data, horizon)
    if len(features) < 250:
        raise TickerDataError(
            f"Model eğitimi için yeterli geçmiş veri yok ({len(features)} etiketli gün). Daha uzun geçmişi olan bir hisse deneyin."
        )

    # Chronological holdout. The gap prevents training labels from reaching into the test period.
    n = len(features)
    test_size = max(40, int(n * 0.2))
    test_start = n - test_size
    train_end = test_start - horizon
    if train_end < 100 or test_start >= n:
        test_accuracy = None
        test_samples = 0
    else:
        x_train, y_train = features.iloc[:train_end], y.iloc[:train_end]
        x_test, y_test = features.iloc[test_start:], y.iloc[test_start:]
        if y_train.nunique() < 2 or y_test.nunique() < 2:
            test_accuracy = None
            test_samples = len(y_test)
        else:
            test_model = new_model()
            test_model.fit(x_train, y_train)
            predictions = test_model.predict(x_test)
            test_accuracy = float(accuracy_score(y_test, predictions))
            test_samples = int(len(y_test))

    # Fit a final model on every row whose future outcome is already known.
    final_model = new_model()
    final_model.fit(features, y)

    latest_x = all_features.iloc[[-1]]
    if latest_x.isna().all(axis=1).iloc[0]:
        raise TickerDataError("Güncel veri için gerekli teknik göstergeler hesaplanamadı.")
    probabilities = final_model.predict_proba(latest_x)[0]
    classes = list(final_model.named_steps["classifier"].classes_)
    up_probability = float(probabilities[classes.index(1)]) if 1 in classes else 0.0
    down_probability = 1.0 - up_probability

    if up_probability >= 0.55:
        direction = "Yükseliş eğilimi"
    elif down_probability >= 0.55:
        direction = "Düşüş eğilimi"
    else:
        direction = "Belirsiz / zayıf yön sinyali"

    last_date = data.index[-1]
    if hasattr(last_date, "strftime"):
        data_date = last_date.strftime("%Y-%m-%d")
    else:
        data_date = str(last_date)

    return {
        "ticker": normalize_ticker(ticker).replace(".IS", ""),
        "horizon": horizon,
        "up_probability": up_probability,
        "down_probability": down_probability,
        "direction": direction,
        "last_close": float(data["Close"].iloc[-1]),
        "data_date": data_date,
        "test_accuracy": test_accuracy,
        "test_samples": test_samples,
    }
