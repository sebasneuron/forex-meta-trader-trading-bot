"""
Forex Trend Following Bot - Configuration
"""
import os
from pathlib import Path

# --- Currency Pairs ---
MAJOR_PAIRS = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'USD/CAD', 'AUD/USD', 'NZD/USD']
MINOR_PAIRS = ['EUR/GBP', 'EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'EUR/AUD', 'GBP/AUD']
EXOTIC_PAIRS = []  # Configurable but higher risk

ALL_PAIRS = MAJOR_PAIRS + MINOR_PAIRS + EXOTIC_PAIRS

# --- Trading Parameters ---
SYMBOLS = ['EUR/USD', 'GBP/USD']
TIMEFRAME = 'H1'
TREND_TIMEFRAME = 'H4'
FAST_MA = 9
SLOW_MA = 21
TREND_FILTER_MA = 200
TREND_FILTER_FAST = 50

# --- Risk Management ---
RISK_PER_TRADE = 0.02  # 2% of account
MAX_RISK_PER_TRADE = 0.03
STOP_LOSS_PIPS = 50
TAKE_PROFIT_RR = 2.0  # 1:2 risk:reward
ATR_STOP_MULTIPLIER = 1.5
MAX_POSITIONS = 2
MAX_SPREAD_PIPS = 2.0
MIN_ATR_PIPS = 10

# --- Sessions ---
FOREX_SESSION = 'ALL'  # LONDON, NY, ASIA, ALL

# Session times (UTC)
SESSION_LONDON = (8, 17)
SESSION_NY = (13, 22)
SESSION_ASIA = (0, 9)
SESSION_OVERLAP = (13, 17)  # London/NY overlap - highest volatility

# --- MT5 Mapping ---
TIMEFRAME_MT5 = {
    'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30,
    'H1': 16385, 'H4': 16388, 'D1': 16408, 'W1': 32769, 'MN1': 49153
}

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / 'logs'
DATA_DIR = BASE_DIR / 'data'

# --- Environment ---
def _env(key: str, default: str = '') -> str:
    return os.getenv(key, default)

MT5_LOGIN = _env('MT5_LOGIN', '')
MT5_PASSWORD = _env('MT5_PASSWORD', '')
MT5_SERVER = _env('MT5_SERVER', '')
MT5_PATH = _env('MT5_PATH', '')  # Optional: path to terminal64.exe

LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
