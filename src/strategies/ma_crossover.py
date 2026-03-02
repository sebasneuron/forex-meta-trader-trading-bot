"""
Dual Moving Average Crossover strategy for Forex.
Golden Cross = BUY, Death Cross = SELL, with higher-timeframe trend filter.
"""
from enum import Enum
from typing import Optional, Tuple

import pandas as pd

from ..utils.indicators import ema, crossover_above, crossover_below, atr_pips


class Signal(int, Enum):
    NONE = 0
    LONG = 1
    SHORT = -1


class MACrossoverStrategy:
    """
    Entry timeframe: Fast/Slow EMA crossover.
    Trend filter: Higher timeframe EMA (e.g. 200) confirms direction.
    """

    def __init__(
        self,
        fast_period: int = 9,
        slow_period: int = 21,
        trend_filter_period: int = 200,
        use_atr_stop: bool = False,
        atr_period: int = 14,
        atr_mult: float = 1.5,
        fixed_sl_pips: Optional[float] = 50,
        risk_reward: float = 2.0,
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.trend_filter_period = trend_filter_period
        self.use_atr_stop = use_atr_stop
        self.atr_period = atr_period
        self.atr_mult = atr_mult
        self.fixed_sl_pips = fixed_sl_pips
        self.risk_reward = risk_reward

    def _ensure_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Fast EMA, Slow EMA, Trend EMA, and optional ATR to dataframe."""
        if 'fast_ema' in df.columns:
            return df
        close = df['close']
        df = df.copy()
        df['fast_ema'] = ema(close, self.fast_period)
        df['slow_ema'] = ema(close, self.slow_period)
        df['trend_ema'] = ema(close, self.trend_filter_period)
        if self.use_atr_stop and 'high' in df.columns and 'low' in df.columns:
            df['atr_pips'] = atr_pips(df['high'], df['low'], close, self.atr_period)
        return df

    def _trend_up(self, row: pd.Series) -> bool:
        """Price above trend EMA = uptrend."""
        return row['close'] > row['trend_ema']

    def _trend_down(self, row: pd.Series) -> bool:
        """Price below trend EMA = downtrend."""
        return row['close'] < row['trend_ema']

    def entry_signal(self, df: pd.DataFrame, trend_df: Optional[pd.DataFrame] = None) -> Tuple[Signal, Optional[dict]]:
        """
        Returns (Signal.LONG | SHORT | NONE, optional dict with sl_pips, tp_pips, etc).
        trend_df: higher timeframe OHLC with same index alignment or last row used for trend.
        """
        df = self._ensure_indicators(df)
        if len(df) < 2:
            return Signal.NONE, None

        row = df.iloc[-1]
        prev = df.iloc[-2]
        golden = crossover_above(df['fast_ema'], df['slow_ema']).iloc[-1]
        death = crossover_below(df['fast_ema'], df['slow_ema']).iloc[-1]

        # Trend from higher TF if provided
        if trend_df is not None and len(trend_df) > 0:
            trend_row = trend_df.iloc[-1]
            if 'trend_ema' not in trend_df.columns:
                trend_df = trend_df.copy()
                trend_df['trend_ema'] = ema(trend_df['close'], self.trend_filter_period)
                trend_row = trend_df.iloc[-1]
            trend_up = trend_row['close'] > trend_row['trend_ema']
            trend_down = trend_row['close'] < trend_row['trend_ema']
        else:
            trend_up = self._trend_up(row)
            trend_down = self._trend_down(row)

        sl_pips = self.fixed_sl_pips
        if self.use_atr_stop and 'atr_pips' in df.columns:
            atr_val = row.get('atr_pips', self.fixed_sl_pips or 50)
            sl_pips = round(float(atr_val) * self.atr_mult, 1)
        if sl_pips is None:
            sl_pips = 50.0
        tp_pips = round(sl_pips * self.risk_reward, 1)

        if golden and trend_up:
            return Signal.LONG, {'sl_pips': sl_pips, 'tp_pips': tp_pips}
        if death and trend_down:
            return Signal.SHORT, {'sl_pips': sl_pips, 'tp_pips': tp_pips}
        return Signal.NONE, None

    def exit_signal(self, df: pd.DataFrame, position_long: bool) -> bool:
        """True = close position. Long: close on death cross; Short: close on golden cross."""
        df = self._ensure_indicators(df)
        if len(df) < 2:
            return False
        death = crossover_below(df['fast_ema'], df['slow_ema']).iloc[-1]
        golden = crossover_above(df['fast_ema'], df['slow_ema']).iloc[-1]
        if position_long and death:
            return True
        if not position_long and golden:
            return True
        return False
