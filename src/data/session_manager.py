"""
Forex session handling (London, New York, Asia) in UTC.
"""
from datetime import datetime
from typing import Optional
import pytz

UTC = pytz.UTC

# Session ranges (hour start, hour end) in UTC
SESSION_LONDON = (8, 17)
SESSION_NY = (13, 22)
SESSION_ASIA = (0, 9)
SESSION_OVERLAP_LONDON_NY = (13, 17)


def _hour_utc(dt: Optional[datetime] = None) -> int:
    if dt is None:
        dt = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = UTC.localize(dt)
    return dt.astimezone(UTC).hour


def is_in_session(session: str, dt: Optional[datetime] = None) -> bool:
    """Check if current (or given) time is within the session. Session in UTC."""
    h = _hour_utc(dt)
    if session.upper() == 'LONDON':
        start, end = SESSION_LONDON
        return start <= h < end
    if session.upper() in ('NY', 'NEW YORK', 'NEWYORK'):
        start, end = SESSION_NY
        return start <= h < end
    if session.upper() == 'ASIA':
        start, end = SESSION_ASIA
        return start <= h < end
    if session.upper() == 'ALL':
        return True
    if session.upper() == 'OVERLAP':
        start, end = SESSION_OVERLAP_LONDON_NY
        return start <= h < end
    return True


def get_active_session(dt: Optional[datetime] = None) -> str:
    """Return current session name: LONDON, NY, ASIA, OVERLAP, or OFF."""
    h = _hour_utc(dt)
    if SESSION_OVERLAP_LONDON_NY[0] <= h < SESSION_OVERLAP_LONDON_NY[1]:
        return 'OVERLAP'
    if SESSION_LONDON[0] <= h < SESSION_LONDON[1]:
        return 'LONDON'
    if SESSION_NY[0] <= h < SESSION_NY[1]:
        return 'NY'
    if SESSION_ASIA[0] <= h < SESSION_ASIA[1]:
        return 'ASIA'
    return 'OFF'


class SessionManager:
    """Filter trading by Forex session."""

    def __init__(self, allowed_sessions: str = 'ALL'):
        self.allowed_sessions = allowed_sessions.upper()

    def can_trade(self, dt: Optional[datetime] = None) -> bool:
        if self.allowed_sessions == 'ALL':
            return True
        if self.allowed_sessions == 'OVERLAP':
            return is_in_session('OVERLAP', dt)
        return is_in_session(self.allowed_sessions, dt)
