"""
MetaTrader 5 data acquisition for Forex symbols.
"""
import pandas as pd
from typing import Optional

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from ..utils.logger import get_logger

logger = get_logger('mt5_fetcher')

# MT5 timeframe constants (when package not installed, use integers)
TIMEFRAME_M1 = 1
TIMEFRAME_M5 = 5
TIMEFRAME_M15 = 15
TIMEFRAME_M30 = 30
TIMEFRAME_H1 = 16385
TIMEFRAME_H4 = 16388
TIMEFRAME_D1 = 16408

TIMEFRAME_MAP = {
    'M1': TIMEFRAME_M1, 'M5': TIMEFRAME_M5, 'M15': TIMEFRAME_M15,
    'M30': TIMEFRAME_M30, 'H1': TIMEFRAME_H1, 'H4': TIMEFRAME_H4, 'D1': TIMEFRAME_D1
}


def _symbol_mt5(symbol: str) -> str:
    """Convert EUR/USD to MT5 symbol (often EURUSD)."""
    return symbol.replace('/', '')


class MT5Fetcher:
    """Fetch OHLC and tick data from MetaTrader 5."""

    def __init__(self, login: Optional[int] = None, password: str = '', server: str = '', path: str = ''):
        self._initialized = False
        self._login = login
        self._password = password
        self._server = server
        self._path = path

    def initialize(self) -> bool:
        if not MT5_AVAILABLE:
            logger.warning("MetaTrader5 package not installed. Use pip install MetaTrader5")
            return False
        kwargs = {}
        if self._path:
            kwargs['path'] = self._path
        if not mt5.initialize(**kwargs):
            logger.error("MT5 initialization failed: %s", mt5.last_error())
            return False
        self._initialized = True
        if self._login and self._password and self._server:
            if not mt5.login(self._login, password=self._password, server=self._server):
                logger.warning("MT5 login failed: %s", mt5.last_error())
            else:
                info = mt5.account_info()
                if info:
                    logger.info("Connected to MT5. Balance: %s %s", info.balance, info.currency)
        return True

    def shutdown(self) -> None:
        if MT5_AVAILABLE and self._initialized:
            mt5.shutdown()
            self._initialized = False

    def copy_rates(self, symbol: str, timeframe: str, count: int = 1000, start_pos: int = 0) -> Optional[pd.DataFrame]:
        """Copy OHLCV rates into a DataFrame. Columns: time, open, high, low, close, tick_volume, spread, real_volume."""
        if not MT5_AVAILABLE or not self._initialized:
            return None
        tf = TIMEFRAME_MAP.get(timeframe.upper(), TIMEFRAME_H1)
        sym = _symbol_mt5(symbol)
        rates = mt5.copy_rates_from_pos(sym, tf, start_pos, count)
        if rates is None or len(rates) == 0:
            logger.warning("No rates for %s %s: %s", sym, timeframe, mt5.last_error())
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df

    def current_spread(self, symbol: str) -> Optional[float]:
        """Current spread in points. Divide by 10 for 5-digit broker (pips)."""
        if not MT5_AVAILABLE or not self._initialized:
            return None
        tick = mt5.symbol_info_tick(_symbol_mt5(symbol))
        if tick is None:
            return None
        return (tick.ask - tick.bid)  # in points

    def spread_pips(self, symbol: str) -> Optional[float]:
        """Spread in pips (5-digit: 1 pip = 10 points)."""
        points = self.current_spread(symbol)
        if points is None:
            return None
        # 5-digit: 1 pip = 10 points for XXX/USD; JPY pairs often same
        return round(points / 10.0, 1)

    def account_info(self) -> Optional[dict]:
        if not MT5_AVAILABLE or not self._initialized:
            return None
        info = mt5.account_info()
        if info is None:
            return None
        return {
            'balance': info.balance,
            'equity': info.equity,
            'currency': info.currency,
            'leverage': info.leverage,
        }
