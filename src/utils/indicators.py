"""
Technical indicators for Forex MA crossover strategy.
"""
import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def crossover_above(fast: pd.Series, slow: pd.Series, shift: int = 1) -> pd.Series:
    """True where fast crosses above slow on current bar (vs previous bar)."""
    prev_fast_below = fast.shift(shift) <= slow.shift(shift)
    curr_fast_above = fast > slow
    return prev_fast_below & curr_fast_above


def crossover_below(fast: pd.Series, slow: pd.Series, shift: int = 1) -> pd.Series:
    """True where fast crosses below slow on current bar (vs previous bar)."""
    prev_fast_above = fast.shift(shift) >= slow.shift(shift)
    curr_fast_below = fast < slow
    return prev_fast_above & curr_fast_below


def atr_pips(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """ATR in pips (assuming 5-digit quote, e.g. 1.12345)."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    return atr * 10000  # 5-digit; for JPY pairs use 100


def pip_value_per_lot(symbol: str, account_currency: str = 'USD') -> float:
    """
    Approximate pip value per standard lot (100k units) in account currency.
    Simplified: for XXX/USD or USD/XXX we use 10 USD per pip per lot for standard pairs.
    """
    symbol_clean = symbol.replace('/', '').upper()
    if 'USD' in symbol_clean and symbol_clean.index('USD') == 0:
        # USD/XXX: pip value ≈ 10 / quote_per_usd for USD account
        return 10.0
    if 'USD' in symbol_clean:
        return 10.0
    # Cross pairs: simplified
    return 10.0
