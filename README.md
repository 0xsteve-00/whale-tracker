# 🐋 Whale Tracker

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)

> Real-time monitoring of large wallet movements across multiple blockchains — track smart money, exchange flows, and trading signals.

## 🎯 What Is This?

Whale Tracker monitors large cryptocurrency wallets ("whales") and alerts you when they make significant moves. Instead of manually checking blockchain explorers, this tool watches for you:

- **Smart Money Tracking** — See what large holders are buying/selling
- **Exchange Flow Monitor** — Detect large deposits (bearish) or withdrawals (bullish)
- **Early Signal Detection** — Get alerts before major price moves
- **Multi-Chain Support** — Monitor wallets across ETH, BSC, Base, Polygon, Arbitrum, and Solana

## 🤔 Who Needs This?

- **Traders** looking for whale-driven market signals
- **Researchers** studying on-chain behavior
- **DeFi users** monitoring protocol treasuries
- **Anyone** who wants to follow smart money

## ⚡ Features

- 🐋 Track unlimited wallet addresses
- 🔔 Real-time alerts (Telegram, Discord, webhook)
- 📊 Transaction history & analytics
- 💰 Token transfer detection (ERC-20, SPL)
- 🏷️ Wallet labeling (exchange, whale, contract)
- 📈 Daily/weekly summary reports
- 🌐 Multi-chain: ETH, BSC, Base, Polygon, Arbitrum, Solana

## 📦 Installation

```bash
git clone https://github.com/0xsteve-00/whale-tracker.git
cd whale-tracker
pip install -r requirements.txt
```

## 🚀 Quick Start

```bash
# Track specific wallets
python tracker.py --wallets wallets.txt --chain eth

# Monitor exchange flows
python tracker.py --mode exchange --alert telegram

# Generate daily report
python tracker.py --report daily
```

## 📁 Project Structure

```
whale-tracker/
├── tracker.py          # Main tracking engine
├── requirements.txt    # Python dependencies
├── .gitignore          # Git ignore rules
├── LICENSE             # MIT License
└── README.md           # This file
```

## ⚠️ Disclaimer

This tool is for informational purposes only. Not financial advice. Always do your own research before making trading decisions.

## 📜 License

MIT License — free to use, modify, and distribute.
