# Triple MA + MACD Trading Bot

Python trading bot for [Capital.com](https://capital.com/) with **Triple EMA + MACD** signals, multi-symbol support, and threaded position management.

## Features

- **Strategy**: EMA21/50/200 alignment + MACD confirmation on 15-minute candles
- **Multi-symbol**: Crypto, FX, indices, and commodities
- **Position management**: Dynamic trailing stops based on account balance milestones
- **Backtesting**: `backtest.py` and `backtest.ipynb` for offline validation

## Stack

Python 3.9+ · pandas · pandas-ta · Capital.com REST API

## Setup

```bash
git clone https://github.com/poudatmorteza/mac_triplema.git
cd mac_triplema
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.ini.example config.ini
# Edit config.ini with your Capital.com credentials
python main.py
```

## Project layout

| File | Purpose |
|------|---------|
| `main.py` | Strategy + position threads, main entry point |
| `strategy.py` | Triple MA + MACD signal logic |
| `broker.py` | Capital.com API wrapper |
| `position.py` | Trailing stop / milestone position tracking |
| `backtest.py` | Backtesting utilities |
| `config.ini` | Local credentials (not committed) |

## Disclaimer

For educational purposes. Trading involves risk. Test on a demo account first.
