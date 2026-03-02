"""
Spread validation before entry (avoid high spread).
"""
from typing import Optional, Callable

from ..utils.logger import get_logger

logger = get_logger('spread_checker')


class SpreadChecker:
    """Reject entries when spread exceeds max spread in pips."""

    def __init__(self, max_spread_pips: float = 2.0, get_spread_pips: Optional[Callable[[str], Optional[float]]] = None):
        self.max_spread_pips = max_spread_pips
        self._get_spread = get_spread_pips

    def set_spread_provider(self, get_spread_pips: Callable[[str], Optional[float]]) -> None:
        self._get_spread = get_spread_pips

    def is_acceptable(self, symbol: str) -> bool:
        if self._get_spread is None:
            return True
        spread = self._get_spread(symbol)
        if spread is None:
            return True
        ok = spread <= self.max_spread_pips
        if not ok:
            logger.debug("Spread %.1f pips exceeds max %.1f for %s", spread, self.max_spread_pips, symbol)
        return ok

    def current_spread(self, symbol: str) -> Optional[float]:
        return self._get_spread(symbol) if self._get_spread else None
