import numpy as np
import pandas as pd


def synthetic_returns(n_assets, n_days=756, seed=0, n_factors=3,
                      vol_range=(0.10, 0.55), mean_range=(0.02, 0.25)):
    rng = np.random.default_rng(seed)
    mkt = rng.normal(0, 0.01, size=(n_days, n_factors))
    betas = rng.uniform(0.2, 1.6, size=(n_assets, n_factors))
    idio_vol = rng.uniform(0.008, 0.022, size=n_assets)
    idio = rng.normal(0, 1, size=(n_days, n_assets)) * idio_vol
    daily_drift = rng.uniform(mean_range[0], mean_range[1], size=n_assets) / 252.0
    returns = mkt @ betas.T + idio + daily_drift
    sector_ids = rng.integers(0, 10, size=n_assets)
    tickers = [f"A{i:04d}" for i in range(n_assets)]
    df = pd.DataFrame(returns, columns=tickers)
    meta = pd.DataFrame({"ticker": tickers, "sector": sector_ids})
    return df, meta


def stats_from_returns(returns, trading_days=252, shrink=0.10):
    mu = returns.mean().to_numpy() * trading_days
    cov = returns.cov().to_numpy() * trading_days
    n = cov.shape[0]
    avg_var = np.mean(np.diag(cov))
    target = avg_var * np.eye(n)
    cov = (1 - shrink) * cov + shrink * target
    cov = 0.5 * (cov + cov.T)
    return mu, cov


def load_returns(tickers=None, start="2019-01-01", end="2024-01-01", use_cache=True):
    import os
    cache = f"_cache_{start}_{end}_{len(tickers) if tickers else 0}.csv"
    if use_cache and os.path.exists(cache):
        return pd.read_csv(cache, index_col=0, parse_dates=True)
    try:
        import yfinance as yf
    except ImportError:
        raise RuntimeError("yfinance not installed; use synthetic_returns instead")
    if tickers is None:
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM",
                   "JNJ", "V", "WMT", "PG", "XOM", "UNH", "HD", "MA", "BAC", "DIS",
                   "NFLX", "ADBE"]
    prices = yf.download(tickers, start=start, end=end, progress=False, auto_adjust=True)
    if isinstance(prices.columns, pd.MultiIndex):
        prices = prices["Close"]
    returns = prices.pct_change().dropna()
    if use_cache:
        returns.to_csv(cache)
    return returns


def load_sp500_kaggle(max_assets=None, min_history=0.95, use_cache=True,
                      cache_path="_cache_sp500_returns.csv"):
    """Rendements quotidiens S&P 500 depuis le dataset Kaggle.

    Telecharge `andrewmvd/sp-500-stocks` via kagglehub, pivote
    `sp500_stocks.csv` (Adj Close) en matrice large, ne garde que les
    tickers couvrant au moins `min_history` de la fenetre, puis ordonne
    les colonnes par liquidite decroissante (prix * volume moyen) de
    sorte que `max_assets` selectionne les N actions les plus liquides.

    Identifiants Kaggle requis : ~/.kaggle/kaggle.json (chmod 600) ou les
    variables KAGGLE_USERNAME / KAGGLE_KEY. Voir README.
    """
    import os
    import glob

    if use_cache and os.path.exists(cache_path):
        returns = pd.read_csv(cache_path, index_col=0, parse_dates=True)
    else:
        try:
            import kagglehub
        except ImportError:
            raise RuntimeError(
                "kagglehub non installe ; pip install -r requirements.txt "
                "et configure ta cle API Kaggle (voir README)")
        path = kagglehub.dataset_download("andrewmvd/sp-500-stocks")
        matches = glob.glob(os.path.join(path, "**", "sp500_stocks.csv"),
                            recursive=True)
        if not matches:
            raise RuntimeError(f"sp500_stocks.csv introuvable sous {path}")
        df = pd.read_csv(matches[0], parse_dates=["Date"])
        price_col = "Adj Close" if "Adj Close" in df.columns else "Close"
        df = df.dropna(subset=[price_col])
        wide = df.pivot(index="Date", columns="Symbol",
                        values=price_col).sort_index()
        keep = wide.columns[wide.notna().mean() >= min_history]
        wide = wide[keep].dropna(how="any")
        returns = wide.pct_change().dropna(how="any")
        if "Volume" in df.columns:
            liq = (df.assign(_dv=df[price_col] * df["Volume"])
                     .groupby("Symbol")["_dv"].mean())
            order = liq.reindex(returns.columns).sort_values(
                ascending=False).index
            returns = returns[list(order)]
        if use_cache:
            returns.to_csv(cache_path)

    if max_assets is not None and returns.shape[1] > max_assets:
        returns = returns.iloc[:, :max_assets]
    return returns


def split_periods(returns, n_periods=3, train_ratio=0.7):
    T = len(returns)
    chunk = T // n_periods
    out = []
    for i in range(n_periods):
        start = i * chunk
        stop = (i + 1) * chunk if i < n_periods - 1 else T
        window = returns.iloc[start:stop]
        cut = int(len(window) * train_ratio)
        out.append((window.iloc[:cut], window.iloc[cut:]))
    return out
