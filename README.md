# Forex Trend Following Bot

A Python trading bot that implements a **Trend Following Strategy** using Moving Average crossovers for **FOREX** (MetaTrader 5).

## Strategy

- **Golden Cross (BUY)**: Fast EMA crosses above Slow EMA, with higher-timeframe trend filter confirming uptrend.
- **Death Cross (SELL)**: Fast EMA crosses below Slow EMA, with higher-timeframe confirming downtrend.
- **Exits**: Close LONG when Fast crosses below Slow; Close SHORT when Fast crosses above Slow.
- **Trend filter**: 50/200 EMA on H4 (or Daily) to only trade in the direction of the higher timeframe.

## Requirements

- Python 3.9+
- MetaTrader 5 terminal (for live/demo and backtest data)
- Broker demo or live account

## Install

```bash
cd forex-trading-bot
pip install -r requirements.txt
```

Copy environment and set your MT5 credentials (use a **demo** account first):

```bash
copy .env.example .env
# Edit .env: MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
```

## MetaTrader 5 Setup

1. Install the MetaTrader 5 terminal from your broker.
2. Open a **DEMO** account (do not start with real money).
3. In MT5: **Tools → Options → Expert Advisors** → enable **Allow automated trading**.
4. Click the **AutoTrading** button in the toolbar (must be green when the bot runs).
5. Keep the MT5 terminal running while the bot is active.

## Usage

**Dry-run (default, no real orders):**

```bash
python forex_trend_bot.py --symbol EUR/USD --timeframe H1 --fast 9 --slow 21 --risk 2 --session LONDON --dry-run
```

**Multiple symbols:**

```bash
python forex_trend_bot.py --symbol EUR/USD GBP/USD --timeframe H1 --session OVERLAP
```

**Backtest (requires MT5 and historical data):**

```bash
python forex_trend_bot.py --backtest --from 2024-01-01 --to 2024-12-31 --visualize
```

**Live trading (use with caution):**

```bash
python forex_trend_bot.py --symbol EUR/USD --timeframe H1 --live
```

## Configuration

| Option            | Default   | Description                    |
|-------------------|-----------|--------------------------------|
| `--symbol`        | EUR/USD, GBP/USD | Symbol(s) to trade      |
| `--timeframe`     | H1        | Entry chart (M15, M30, H1, H4, D1) |
| `--trend-timeframe` | H4     | Trend filter chart             |
| `--fast` / `--slow` | 9 / 21  | Fast and slow EMA periods      |
| `--trend-ma`      | 200       | Trend filter EMA period        |
| `--risk`          | 2         | Risk per trade (%)             |
| `--session`       | ALL       | LONDON, NY, ASIA, OVERLAP, ALL |
| `--dry-run`       | true      | No real orders                 |
| `--live`          | false     | Send real orders               |

Risk management (in code): 2% risk per trade, 50 pip default stop, 1:2 risk:reward, max spread check.

## Project Structure

```
forex-trend-bot/
├── src/
│   ├── bot.py                 # Main bot loop
│   ├── strategies/
│   │   └── ma_crossover.py    # MA crossover + trend filter
│   ├── data/
│   │   ├── mt5_fetcher.py     # MT5 data
│   │   └── session_manager.py # Forex sessions
│   ├── risk/
│   │   ├── position_sizer.py  # Pip-based sizing
│   │   └── spread_checker.py  # Spread filter
│   ├── backtest/
│   │   └── forex_backtester.py
│   └── utils/
│       ├── logger.py
│       └── indicators.py
├── config.py
├── forex_trend_bot.py         # CLI
├── .env.example
├── requirements.txt
└── README.md
```

## Supported Pairs

- **Majors**: EUR/USD, GBP/USD, USD/JPY, USD/CHF, USD/CAD, AUD/USD, NZD/USD
- **Minors**: EUR/GBP, EUR/JPY, GBP/JPY, AUD/JPY, EUR/AUD, GBP/AUD

Start with 1–2 major pairs (e.g. EUR/USD, GBP/USD).

## Sessions (UTC)

- **London**: 08:00–17:00  
- **New York**: 13:00–22:00  
- **Overlap (best volatility)**: 13:00–17:00  

Use `--session OVERLAP` or `LONDON`/`NY` to limit trading to these windows.

## Warnings

- Use a **DEMO account** for at least 1–2 months before considering live trading.
- This strategy may **not** be profitable; it is for education and experimentation.
- Forex trading involves **high risk** of loss; never risk money you cannot afford to lose.
- MT5 must stay **open** and **AutoTrading enabled** while the bot runs.
- Check spreads and avoid trading through major news (e.g. NFP, FOMC) unless you add a news filter.

## Example Log Output

```
2024-01-15 14:30:00 - [London Session] Checking EUR/USD on H1 chart
2024-01-15 14:30:00 - Fast EMA(9): 1.1234, Slow EMA(21): 1.1221
2024-01-15 14:30:00 - GOLDEN CROSS DETECTED! Fast EMA crossed above Slow EMA
2024-01-15 14:30:00 - Trend filter: H4 EMA(200) confirms uptrend
2024-01-15 14:30:00 - Current spread: 1.2 pips (within limit 2.0)
2024-01-15 14:30:01 - Risk: 2% of $10,000 = $200
2024-01-15 14:30:01 - Position size: 0.2 lots (stop 50 pips)
2024-01-15 14:30:02 - [DRY-RUN] Would execute BUY market order: 0.2 lots EUR/USD (SL: 50 pips, TP: 100 pips)
```

## License

Use at your own risk. Not financial advice.
