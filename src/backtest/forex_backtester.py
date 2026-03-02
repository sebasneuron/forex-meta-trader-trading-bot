"""
Forex-specific backtester with spread/slippage simulation and key metrics.
"""
from dataclasses import dataclass, field
from typing import Optional, List
import pandas as pd
import numpy as np

from ..strategies.ma_crossover import MACrossoverStrategy, Signal
from ..utils.indicators import ema


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    symbol: str
    side: str  # 'long' | 'short'
    entry_price: float
    exit_price: float
    lots: float
    pips: float
    pnl: float
    exit_reason: str  # 'tp' | 'sl' | 'signal'


@dataclass
class BacktestResult:
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    total_return: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    total_pips: float = 0.0


def _pips_from_prices(side: str, entry: float, exit_price: float, is_jpy: bool) -> float:
    mult = 0.01 if is_jpy else 0.0001
    if side == 'long':
        return (exit_price - entry) / mult
    return (entry - exit_price) / mult


class ForexBacktester:
    """
    Backtest MA crossover strategy on OHLCV DataFrame.
    Columns required: open, high, low, close; optional: spread (in pips).
    """

    def __init__(
        self,
        strategy: MACrossoverStrategy,
        initial_balance: float = 10000,
        risk_per_trade: float = 0.02,
        spread_pips: float = 1.0,
        slippage_pips: float = 0.5,
        pip_value_per_lot: float = 10.0,
    ):
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.spread_pips = spread_pips
        self.slippage_pips = slippage_pips
        self.pip_value = pip_value_per_lot

    def _lot_size(self, balance: float, sl_pips: float) -> float:
        risk_amt = balance * self.risk_per_trade
        if sl_pips <= 0:
            return 0.0
        lots = risk_amt / (sl_pips * self.pip_value)
        return round(min(max(lots, 0.01), 10) * 100) / 100

    def run(
        self,
        df: pd.DataFrame,
        symbol: str = 'EUR/USD',
        trend_df: Optional[pd.DataFrame] = None,
    ) -> BacktestResult:
        """
        Run backtest on df (must have datetime index and open, high, low, close).
        trend_df: optional higher-timeframe data; will be aligned by date for trend filter.
        """
        if df is None or len(df) < 200:
            return BacktestResult()
        is_jpy = 'JPY' in symbol.upper()
        df = df.copy()
        df = self.strategy._ensure_indicators(df)
        if trend_df is not None and len(trend_df) > 0:
            trend_df = trend_df.copy()
            if 'trend_ema' not in trend_df.columns:
                trend_df['trend_ema'] = ema(trend_df['close'], self.strategy.trend_filter_period)

        balance = self.initial_balance
        equity = [balance]
        times = [df.index[0]]
        position = None  # {'side': 'long'|'short', 'entry_price', 'entry_time', 'lots', 'sl_pips', 'tp_pips'}
        trades: List[Trade] = []

        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            bar_time = df.index[i]
            high, low, close = row['high'], row['low'], row['close']
            spread = row.get('spread_pips', self.spread_pips) + self.slippage_pips

            # Resample trend to current bar if needed
            tf_trend_df = None
            if trend_df is not None:
                tf_trend_df = trend_df[trend_df.index <= bar_time].tail(500)

            # Check exit first
            if position is not None:
                exit_price = None
                exit_reason = None
                if position['side'] == 'long':
                    if low <= position['sl_price']:
                        exit_price = position['sl_price']
                        exit_reason = 'sl'
                    elif high >= position['tp_price']:
                        exit_price = position['tp_price']
                        exit_reason = 'tp'
                    elif self.strategy.exit_signal(df.iloc[: i + 1], True):
                        exit_price = close
                        exit_reason = 'signal'
                else:
                    if high >= position['sl_price']:
                        exit_price = position['sl_price']
                        exit_reason = 'sl'
                    elif low <= position['tp_price']:
                        exit_price = position['tp_price']
                        exit_reason = 'tp'
                    elif self.strategy.exit_signal(df.iloc[: i + 1], False):
                        exit_price = close
                        exit_reason = 'signal'

                if exit_price is not None:
                    pips = _pips_from_prices(position['side'], position['entry_price'], exit_price, is_jpy)
                    pnl = pips * self.pip_value * position['lots']
                    balance += pnl
                    trades.append(Trade(
                        entry_time=position['entry_time'],
                        exit_time=bar_time,
                        symbol=symbol,
                        side=position['side'],
                        entry_price=position['entry_price'],
                        exit_price=exit_price,
                        lots=position['lots'],
                        pips=pips,
                        pnl=pnl,
                        exit_reason=exit_reason,
                    ))
                    position = None

            # Entry
            if position is None:
                sub = df.iloc[: i + 1]
                signal, params = self.strategy.entry_signal(sub, tf_trend_df)
                if signal != Signal.NONE and params:
                    sl_pips = params.get('sl_pips', 50)
                    tp_pips = params.get('tp_pips', 100)
                    lots = self._lot_size(balance, sl_pips)
                    if lots >= 0.01:
                        entry_price = close + (spread * 0.0001) if signal == Signal.LONG else close - (spread * 0.0001)
                        if is_jpy:
                            entry_price = close + (spread * 0.01) if signal == Signal.LONG else close - (spread * 0.01)
                        mult = 0.0001 if not is_jpy else 0.01
                        if signal == Signal.LONG:
                            sl_price = entry_price - sl_pips * mult
                            tp_price = entry_price + tp_pips * mult
                        else:
                            sl_price = entry_price + sl_pips * mult
                            tp_price = entry_price - tp_pips * mult
                        position = {
                            'side': 'long' if signal == Signal.LONG else 'short',
                            'entry_price': entry_price,
                            'entry_time': bar_time,
                            'lots': lots,
                            'sl_pips': sl_pips,
                            'tp_pips': tp_pips,
                            'sl_price': sl_price,
                            'tp_price': tp_price,
                        }

            equity.append(balance)
            times.append(bar_time)

        # Close any open position at last bar
        if position is not None:
            close_price = df.iloc[-1]['close']
            pips = _pips_from_prices(position['side'], position['entry_price'], close_price, is_jpy)
            pnl = pips * self.pip_value * position['lots']
            balance += pnl
            trades.append(Trade(
                entry_time=position['entry_time'],
                exit_time=df.index[-1],
                symbol=symbol,
                side=position['side'],
                entry_price=position['entry_price'],
                exit_price=close_price,
                lots=position['lots'],
                pips=pips,
                pnl=pnl,
                exit_reason='signal',
            ))

        equity_series = pd.Series(equity, index=times)
        total_return = (balance - self.initial_balance) / self.initial_balance
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        win_rate = len(wins) / len(trades) if trades else 0
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit or 0)
        cum = equity_series
        roll_max = cum.cummax()
        drawdown = (cum - roll_max) / roll_max
        max_drawdown = float(drawdown.min()) if len(drawdown) else 0
        returns = equity_series.pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * np.sqrt(252 * 24)) if returns.std() > 0 else 0  # rough annualized
        total_pips = sum(t.pips for t in trades)

        return BacktestResult(
            trades=trades,
            equity_curve=equity_series,
            total_return=total_return,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=float(sharpe),
            total_pips=total_pips,
        )
