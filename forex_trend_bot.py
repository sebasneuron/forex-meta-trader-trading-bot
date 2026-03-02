#!/usr/bin/env python3
"""
Forex Trend Following Bot - CLI entry point.
Usage:
  python forex_trend_bot.py --symbol EUR/USD --timeframe H1 --fast 9 --slow 21 --risk 2 --session LONDON --dry-run
  python forex_trend_bot.py --backtest --from 2024-01-01 --to 2024-12-31 --visualize
"""
import argparse
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv()


def parse_args():
    p = argparse.ArgumentParser(description='Forex MA Crossover Trend Bot')
    p.add_argument('--symbol', type=str, nargs='+', default=['EUR/USD', 'GBP/USD'],
                   help='Symbol(s), e.g. EUR/USD')
    p.add_argument('--timeframe', type=str, default='H1', choices=['M15', 'M30', 'H1', 'H4', 'D1'],
                   help='Entry chart timeframe')
    p.add_argument('--trend-timeframe', type=str, default='H4', choices=['H4', 'D1'],
                   help='Trend confirmation timeframe')
    p.add_argument('--fast', type=int, default=9, help='Fast MA period')
    p.add_argument('--slow', type=int, default=21, help='Slow MA period')
    p.add_argument('--trend-ma', type=int, default=200, help='Trend filter EMA period')
    p.add_argument('--risk', type=float, default=2.0, help='Risk per trade (percent, e.g. 2)')
    p.add_argument('--session', type=str, default='ALL',
                   choices=['ALL', 'LONDON', 'NY', 'ASIA', 'OVERLAP'],
                   help='Trade only during session')
    p.add_argument('--dry-run', action='store_true', default=True,
                   help='No real orders (default: True)')
    p.add_argument('--live', action='store_true', help='Enable live trading (overrides --dry-run)')
    p.add_argument('--backtest', action='store_true', help='Run backtest instead of live/dry loop')
    p.add_argument('--from', dest='from_date', type=str, default='2024-01-01',
                   help='Backtest start date (YYYY-MM-DD)')
    p.add_argument('--to', dest='to_date', type=str, default='2024-12-31',
                   help='Backtest end date (YYYY-MM-DD)')
    p.add_argument('--visualize', action='store_true', help='Plot equity curve after backtest')
    p.add_argument('--interval', type=int, default=3600,
                   help='Seconds between bot checks (default 3600 = 1h)')
    return p.parse_args()


def run_bot(args):
    from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH
    from src.bot import ForexTrendBot
    from src.data.mt5_fetcher import MT5Fetcher

    login = int(MT5_LOGIN) if MT5_LOGIN and MT5_LOGIN.isdigit() else None
    fetcher = MT5Fetcher(login=login, password=MT5_PASSWORD or '', server=MT5_SERVER or '', path=MT5_PATH or '')
    bot = ForexTrendBot(
        symbols=args.symbol,
        timeframe=args.timeframe,
        trend_timeframe=args.trend_timeframe,
        fast_ma=args.fast,
        slow_ma=args.slow,
        trend_filter_ma=args.trend_ma,
        risk_per_trade=args.risk / 100.0,
        session=args.session,
        dry_run=not args.live,
        mt5_fetcher=fetcher,
    )
    if args.live:
        print('WARNING: Live trading enabled. Orders will be sent to the broker.')
    bot.run_loop(interval_seconds=args.interval)


def run_backtest(args):
    import pandas as pd
    from datetime import datetime
    from config import SYMBOLS
    from src.strategies.ma_crossover import MACrossoverStrategy
    from src.backtest.forex_backtester import ForexBacktester

    try:
        import MetaTrader5 as mt5
        mt5_available = True
    except ImportError:
        mt5_available = False

    symbols = args.symbol if args.symbol else SYMBOLS
    strategy = MACrossoverStrategy(
        fast_period=args.fast,
        slow_period=args.slow,
        trend_filter_period=args.trend_ma,
        fixed_sl_pips=50,
        risk_reward=2.0,
    )
    backtester = ForexBacktester(
        strategy=strategy,
        initial_balance=10000,
        risk_per_trade=args.risk / 100.0,
        spread_pips=1.2,
        slippage_pips=0.5,
    )

    from_date = getattr(args, 'from_date', '2024-01-01')
    to_date = getattr(args, 'to_date', '2024-12-31')

    if mt5_available:
        # Fetch from MT5
        if not mt5.initialize():
            print('MT5 init failed. Provide CSV or install MT5.')
            return
        tf_map = {'M15': 15, 'M30': 30, 'H1': 16385, 'H4': 16388, 'D1': 16408}
        tf = tf_map.get(args.timeframe, 16385)
        tf_trend = 16388 if args.trend_timeframe == 'H4' else 16408
        for symbol in symbols:
            sym = symbol.replace('/', '')
            rates = mt5.copy_rates_range(sym, tf, datetime.strptime(from_date, '%Y-%m-%d'), datetime.strptime(to_date, '%Y-%m-%d'))
            if rates is None or len(rates) == 0:
                print(f'No data for {symbol}')
                continue
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df.rename(columns={'tick_volume': 'volume'}, inplace=True, errors='ignore')
            trend_rates = mt5.copy_rates_range(sym, tf_trend, datetime.strptime(from_date, '%Y-%m-%d'), datetime.strptime(to_date, '%Y-%m-%d'))
            trend_df = pd.DataFrame(trend_rates) if trend_rates is not None and len(trend_rates) else None
            if trend_df is not None and len(trend_df) > 0:
                trend_df['time'] = pd.to_datetime(trend_df['time'], unit='s')
                trend_df.set_index('time', inplace=True)
            res = backtester.run(df, symbol=symbol, trend_df=trend_df)
            _print_backtest_result(res, symbol)
            if args.visualize:
                _plot_equity(res, symbol)
        if mt5_available:
            mt5.shutdown()
    else:
        # Demo: synthetic or CSV
        print('MT5 not available. Use CSV or install MetaTrader5 for backtest data.')
        print('Example: save OHLCV CSV with columns: time,open,high,low,close')
        return

    return


def _print_backtest_result(res, symbol: str):
    print(f'\n--- Backtest {symbol} ---')
    print(f'Total return: {res.total_return:.2%}')
    print(f'Win rate: {res.win_rate:.1%}')
    print(f'Profit factor: {res.profit_factor:.2f}')
    print(f'Max drawdown: {res.max_drawdown:.2%}')
    print(f'Sharpe ratio: {res.sharpe_ratio:.2f}')
    print(f'Total pips: {res.total_pips:.1f}')
    print(f'Trades: {len(res.trades)}')


def _plot_equity(res, symbol: str):
    try:
        import matplotlib.pyplot as plt
        res.equity_curve.plot(title=f'Equity - {symbol}')
        plt.xlabel('Time')
        plt.ylabel('Equity')
        plt.tight_layout()
        plt.savefig(Path(__file__).parent / 'logs' / f'equity_{symbol.replace("/", "_")}.png')
        plt.show()
    except Exception as e:
        print('Could not plot:', e)


def main():
    args = parse_args()
    if args.backtest:
        run_backtest(args)
    else:
        run_bot(args)


if __name__ == '__main__':
    main()
