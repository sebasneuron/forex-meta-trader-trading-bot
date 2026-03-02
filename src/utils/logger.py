"""
Logging with optional pip/trade tracking for Forex bot.
"""
import logging
import sys
from pathlib import Path

# Default to project root for log path
LOG_DIR = Path(__file__).resolve().parents[2] / 'logs'
LOG_DIR.mkdir(exist_ok=True)


def get_logger(name: str = 'forex_bot', level: int = logging.INFO) -> logging.Logger:
    """Get configured logger writing to console and file."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    fmt = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    fh = logging.FileHandler(LOG_DIR / f'{name}.log', encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger
