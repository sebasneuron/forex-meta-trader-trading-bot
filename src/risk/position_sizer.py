"""
Pip-based position sizing for Forex.
"""
from typing import Optional

from ..utils.logger import get_logger

logger = get_logger('position_sizer')


def _pip_value_per_lot(symbol: str) -> float:
    """Pip value in USD per standard lot (100k) for common pairs. Simplified."""
    s = symbol.upper().replace('/', '')
    if 'JPY' in s:
        return 9.35  # ~100 USD/JPY
    return 10.0


def _lot_step() -> float:
    """Minimum lot step (0.01 for most brokers)."""
    return 0.01


class PositionSizer:
    """Calculate lot size from risk %, stop loss pips, and account balance."""

    def __init__(
        self,
        risk_fraction: float = 0.02,
        account_currency: str = 'USD',
        pip_value_per_lot_func=None,
    ):
        self.risk_fraction = risk_fraction
        self.account_currency = account_currency
        self._pip_value = pip_value_per_lot_func or _pip_value_per_lot

    def size_lots(
        self,
        symbol: str,
        balance: float,
        stop_loss_pips: float,
        account_currency: Optional[str] = None,
    ) -> float:
        """
        Size position so that stop_loss_pips risk = risk_fraction * balance.
        Returns lot size (e.g. 0.1, 0.2).
        """
        if balance <= 0 or stop_loss_pips <= 0:
            return 0.0
        currency = account_currency or self.account_currency
        pip_val = self._pip_value(symbol)
        risk_amount = balance * self.risk_fraction
        # risk_amount = lots * stop_loss_pips * pip_value_per_lot
        lots = risk_amount / (stop_loss_pips * pip_val)
        step = _lot_step()
        lots = max(0, round(lots / step) * step)
        if lots < step:
            lots = 0.0
        return round(lots, 2)

    def risk_amount(self, balance: float) -> float:
        """Amount in account currency to risk per trade."""
        return balance * self.risk_fraction
