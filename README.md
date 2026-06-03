# 🐋 Whale Tracker

Track whale wallets and large transactions across multiple EVM chains in real-time.

## 🎯 Apa Ini?

**Whale Tracker** adalah tool untuk memantau pergerakan wallet besar (whale) di blockchain. Sangat berguna untuk:

- **Smart Money Tracking** — ikuti kemana uang besar bergerak (accumulate/dump)
- **Exchange Flow** — monitor deposit/withdrawal di Binance, Coinbase, dll
- **Rug Pull Detection** — deteksi jika whale besar mulai dump token
- **Trading Signal** — buat signal trading berdasarkan pergerakan whale
- **Airdrop Hunter** — monitor wallet yang sering dapat airdrop

**Masalah yang diselesaikan:**
Whale beli/jual duluan sebelum harga berubah. Dengan tool ini, lo tau real-time dan bisa reaksi lebih cepat.

## Features

- 🐋 Monitor whale wallets (top holders, custom addresses)
- 💸 Real-time large transaction alerts
- 🔗 Multi-chain support (Ethereum, BSC, Base, Polygon, Arbitrum)
- 📊 Transaction history logging (SQLite)
- 📱 Telegram notifications
- 🎯 Token transfer tracking (ERC-20)
- ⚡ WebSocket & polling modes
- 🐍 Pure Python, no external services needed

## Installation

```bash
git clone https://github.com/0xsteve-00/whale-tracker.git
cd whale-tracker
pip install -r requirements.txt
```

## Quick Start

```bash
# Track whale transactions on Ethereum
python tracker.py --chain eth --min-amount 100

# Track specific wallets
python tracker.py --chain eth --wallets wallets.txt --min-amount 50

# With Telegram alerts
python tracker.py --chain eth --telegram-bot BOT_TOKEN --telegram-chat CHAT_ID

# Multi-chain
python tracker.py --chain eth,bsc,base --min-amount 1000
```

## Config (config.yaml)

```yaml
chains:
  eth:
    rpc: "https://eth.llamarpc.com"
    explorer_api: "https://api.etherscan.io/api"
    api_key: ""  # optional, free tier works
  bsc:
    rpc: "https://bsc-dataseed.binance.org"
    explorer_api: "https://api.bscscan.com/api"
  base:
    rpc: "https://mainnet.base.org"
    explorer_api: "https://api.basescan.org/api"

# Minimum ETH/BNB amount to alert
min_amount: 100

# Whale wallets to watch (auto-populated or custom)
whale_file: "whale_addresses.txt"

# Telegram alerts
telegram:
  bot_token: ""
  chat_id: ""

# Poll interval (seconds)
poll_interval: 15

# Database
db: "whale_tracker.db"
```

## Whale Addresses

```
# whale_addresses.txt — one address per line
# Add known whale wallets, exchanges, or DeFi protocols
0x28C6c06298d514Db089934071355E5743bf21d60  # Binance Hot Wallet
0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549  # Binance Cold Wallet
0xDFd5293D8e347dFe59E90eFd55b2956a1343963d  # Coinbase Prime
```

## Output Example

```
🐋 Whale Tracker — Ethereum
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[14:32:15] 💸 2,500 ETH ($6.2M)
  From: 0x28C6...1d60 (Binance Hot)
  To:   0xDFd5...963d (Coinbase Prime)
  Tx:   0xabc...def
  🔗 https://etherscan.io/tx/0xabc...def

[14:31:42] 🪙 50,000 USDT
  From: 0x21a3...5549 (Binance Cold)
  To:   0x1234...5678 (Unknown)
  Tx:   0x789...012
  🔗 https://etherscan.io/tx/0x789...012
```

## Use Cases

- 📈 Track whale accumulation/distribution
- 🚨 Get alerted before large dumps
- 🔍 Monitor exchange inflows/outflows
- 🎯 Follow smart money movements
- 📊 Build trading signals

## Tech Stack

- Python 3.10+
- web3.py (EVM interaction)
- requests (API calls)
- SQLite (history)
- python-telegram-bot (alerts)

## Disclaimer

For educational and research purposes only. Not financial advice.

## License

MIT
