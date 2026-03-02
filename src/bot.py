"""
Main Forex Trend Following Bot: MA crossover with trend filter and risk controls.
"""
from typing import Optional, List
from datetime import datetime
import time

from .strategies.ma_crossover import MACrossoverStrategy, Signal
from .data.mt5_fetcher import MT5Fetcher, TIMEFRAME_MAP
from .data.session_manager import SessionManager, get_active_session
from .risk.position_sizer import PositionSizer
from .risk.spread_checker import SpreadChecker
from .utils.logger import get_logger

logger = get_logger('bot')


class ForexTrendBot:
    """
    Trend following bot: Golden Cross / Death Cross with higher-timeframe trend filter.
    """

    def __init__(
        self,
        symbols: List[str],
        timeframe: str = 'H1',
        trend_timeframe: str = 'H4',
        fast_ma: int = 9,
        slow_ma: int = 21,
        trend_filter_ma: int = 200,
        risk_per_trade: float = 0.02,
        stop_loss_pips: float = 50,
        risk_reward: float = 2.0,
        max_spread_pips: float = 2.0,
        session: str = 'ALL',
        dry_run: bool = True,
        mt5_fetcher: Optional[MT5Fetcher] = None,
    ):
        self.symbols = symbols
        self.timeframe = timeframe.upper()
        self.trend_timeframe = trend_timeframe.upper()
        self.dry_run = dry_run
        self.strategy = MACrossoverStrategy(
            fast_period=fast_ma,
            slow_period=slow_ma,
            trend_filter_period=trend_filter_ma,
            fixed_sl_pips=stop_loss_pips,
            risk_reward=risk_reward,
        )
        self.session_mgr = SessionManager(allowed_sessions=session)
        self.position_sizer = PositionSizer(risk_fraction=risk_per_trade)
        self.spread_checker = SpreadChecker(max_spread_pips=max_spread_pips)
        self.fetcher = mt5_fetcher or MT5Fetcher()
        self._positions = {}  # symbol -> 'long' | 'short'

    def _ensure_connected(self) -> bool:
        if getattr(self.fetcher, '_initialized', False):
            return True
        return self.fetcher.initialize()

    def _get_rates(self, symbol: str, tf: str, count: int = 500) -> Optional["pd.DataFrame"]:
        df = self.fetcher.copy_rates(symbol, tf, count=count)
        if df is None or len(df) < 50:
            return None
        return df

    def _get_trend_rates(self, symbol: str) -> Optional["pd.DataFrame"]:
        return self._get_rates(symbol, self.trend_timeframe, count=300)

    def _run_symbol(self, symbol: str) -> None:
        import pandas as pd
        df = self._get_rates(symbol, self.timeframe)
        if df is None:
            logger.warning("No data for %s %s", symbol, self.timeframe)
            return
        df = self.strategy._ensure_indicators(df)
        trend_df = self._get_trend_rates(symbol)
        signal, params = self.strategy.entry_signal(df, trend_df)

        session_name = get_active_session()
        logger.info("[%s] Checking %s on %s chart", session_name, symbol, self.timeframe)
        last = df.iloc[-1]
        logger.info(
            "Fast EMA(%s): %s, Slow EMA(%s): %s",
            self.strategy.fast_period, round(last['fast_ema'], 5),
            self.strategy.slow_period, round(last['slow_ema'], 5),
        )

        # Check exit for existing position
        if symbol in self._positions:
            is_long = self._positions[symbol] == 'long'
            if self.strategy.exit_signal(df, is_long):
                logger.info("Exit signal: closing %s %s", 'LONG' if is_long else 'SHORT', symbol)
                if not self.dry_run and self.fetcher:
                    self._close_position(symbol)
                del self._positions[symbol]
            return

        if signal == Signal.NONE:
            return

        if not self.session_mgr.can_trade():
            logger.debug("Outside allowed session, skip trade")
            return
        if not self.spread_checker.is_acceptable(symbol):
            spread = self.spread_checker.current_spread(symbol)
            logger.warning("Spread %.1f pips exceeds max for %s", spread or 0, symbol)
            return

        if signal == Signal.LONG:
            logger.info("GOLDEN CROSS DETECTED! Fast EMA crossed above Slow EMA")
        else:
            logger.info("DEATH CROSS DETECTED! Fast EMA crossed below Slow EMA")
        if trend_df is not None and len(trend_df) > 0:
            logger.info("Trend filter: %s EMA(%s) confirms %s", self.trend_timeframe, self.strategy.trend_filter_period,
                        'uptrend' if signal == Signal.LONG else 'downtrend')

        spread = self.spread_checker.current_spread(symbol) or 0
        logger.info("Current spread: %.1f pips (within limit %.1f)", spread, self.spread_checker.max_spread_pips)

        sl_pips = params.get('sl_pips', 50)
        tp_pips = params.get('tp_pips', 100)
        info = self.fetcher.account_info()
        balance = info.get('balance', 10000) if info else 10000
        risk_amt = self.position_sizer.risk_amount(balance)
        lots = self.position_sizer.size_lots(symbol, balance, sl_pips)
        logger.info("Risk: %.0f%% of account = %s", self.position_sizer.risk_fraction * 100, risk_amt)
        logger.info("Position size: %.2f lots (stop %.0f pips)", lots, sl_pips)

        if lots <= 0:
            logger.warning("Position size is 0, skip")
            return

        if self.dry_run:
            logger.info(
                "[DRY-RUN] Would execute %s market order: %.2f lots %s (SL: %.0f pips, TP: %.0f pips)",
                'BUY' if signal == Signal.LONG else 'SELL', lots, symbol, sl_pips, tp_pips
            )
            self._positions[symbol] = 'long' if signal == Signal.LONG else 'short'
            return

        self._place_order(symbol, signal == Signal.LONG, lots, last['close'], sl_pips, tp_pips)
        self._positions[symbol] = 'long' if signal == Signal.LONG else 'short'

    def _place_order(self, symbol: str, is_buy: bool, lots: float, price: float, sl_pips: float, tp_pips: float) -> None:
        """Place market order via MT5 (stub; implement with mt5.order_send)."""
        try:
            import MetaTrader5 as mt5
            sym = symbol.replace('/', '')
            point = 0.0001 if 'JPY' not in symbol.upper() else 0.01
            sl_dist = sl_pips * point * (10 if 'JPY' in symbol.upper() else 1)
            tp_dist = tp_pips * point * (10 if 'JPY' in symbol.upper() else 1)
            if is_buy:
                sl_price = price - sl_dist
                tp_price = price + tp_dist
            else:
                sl_price = price + sl_dist
                tp_price = price - tp_dist
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": sym,
                "volume": round(lots, 2),
                "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": sl_price,
                "tp": tp_price,
                "deviation": 20,
                "magic": 234000,
                "comment": "ForexTrendBot",
            }
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info("Order filled. SL: %s, TP: %s", sl_price, tp_price)
            else:
                logger.error("Order failed: %s", result)
        except Exception as e:
            logger.exception("Order failed: %s", e)

    def _close_position(self, symbol: str) -> None:
        """Close open position for symbol (MT5)."""
        try:
            import MetaTrader5 as mt5
            sym = symbol.replace('/', '')
            positions = mt5.positions_get(symbol=sym)
            for pos in positions or []:
                mt5.close_position(pos)
        except Exception as e:
            logger.exception("Close failed: %s", e)

    def run_once(self) -> None:
        """One iteration: check all symbols and optionally place/close trades."""
        if not self._ensure_connected():
            logger.warning("MT5 not connected; run in dry-run or connect first")
            if not self.dry_run:
                return
        self.spread_checker.set_spread_provider(self.fetcher.spread_pips)
        for symbol in self.symbols:
            try:
                self._run_symbol(symbol)
            except Exception as e:
                logger.exception("Error processing %s: %s", symbol, e)

    def run_loop(self, interval_seconds: int = 3600) -> None:
        """Run bot every interval_seconds (e.g. 3600 for H1)."""
        logger.info("Starting bot loop (interval=%ss, dry_run=%s)", interval_seconds, self.dry_run)
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                logger.info("Stopped by user")
                break
            except Exception as e:
                logger.exception("Loop error: %s", e)
            time.sleep(interval_seconds)
        if getattr(self.fetcher, 'shutdown', None):
            self.fetcher.shutdown()
