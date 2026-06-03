#!/usr/bin/env python3
"""
Whale Tracker — Monitor whale wallets and large transactions on EVM chains.
Usage:
  python tracker.py --chain eth --min-amount 100
  python tracker.py --chain eth,bsc --telegram-bot TOKEN --telegram-chat CHAT_ID
"""

import argparse
import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml

# ═══════════════════════════════════════════════════════════════
# CHAIN CONFIGS
# ═══════════════════════════════════════════════════════════════

CHAINS = {
    "eth": {
        "name": "Ethereum",
        "rpc": "https://eth.llamarpc.com",
        "explorer_api": "https://api.etherscan.io/api",
        "symbol": "ETH",
        "decimals": 18,
        "explorer": "https://etherscan.io",
    },
    "bsc": {
        "name": "BNB Chain",
        "rpc": "https://bsc-dataseed.binance.org",
        "explorer_api": "https://api.bscscan.com/api",
        "symbol": "BNB",
        "decimals": 18,
        "explorer": "https://bscscan.com",
    },
    "base": {
        "name": "Base",
        "rpc": "https://mainnet.base.org",
        "explorer_api": "https://api.basescan.org/api",
        "symbol": "ETH",
        "decimals": 18,
        "explorer": "https://basescan.org",
    },
    "polygon": {
        "name": "Polygon",
        "rpc": "https://polygon-rpc.com",
        "explorer_api": "https://api.polygonscan.com/api",
        "symbol": "MATIC",
        "decimals": 18,
        "explorer": "https://polygonscan.com",
    },
    "arbitrum": {
        "name": "Arbitrum",
        "rpc": "https://arb1.arbitrum.io/rpc",
        "explorer_api": "https://api.arbiscan.io/api",
        "symbol": "ETH",
        "decimals": 18,
        "explorer": "https://arbiscan.io",
    },
}

# Known labels
KNOWN_LABELS = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance Hot",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance Cold",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Coinbase Prime",
    "0xa090e606e30bd747d4e6245a1517ebe430f0057e": "Coinbase Commerce",
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503": "Jump Trading",
    "0x1b3cb81e51011b549d78bf720b0d924ac763a7c2": "Grayscale",
    "0x56eddb7aa87536c09ccc2793473599fd21a8b17f": "Alameda (defunct)",
}

# Known token contracts
KNOWN_TOKENS = {
    "0xdac17f958d2ee523a2206206994597c13d831ec7": {"symbol": "USDT", "decimals": 6},
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": {"symbol": "USDC", "decimals": 6},
    "0x6b175474e89094c44da98b954eedeac495271d0f": {"symbol": "DAI", "decimals": 18},
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": {"symbol": "WBTC", "decimals": 8},
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": {"symbol": "WETH", "decimals": 18},
}


# ═══════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════

class Database:
    def __init__(self, path: str = "whale_tracker.db"):
        self.conn = sqlite3.connect(path)
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain TEXT,
                hash TEXT UNIQUE,
                block INTEGER,
                timestamp INTEGER,
                from_addr TEXT,
                to_addr TEXT,
                value REAL,
                symbol TEXT,
                token TEXT,
                is_token INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_tx_chain ON transactions(chain);
            CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_tx_value ON transactions(value);
        """)
        self.conn.commit()

    def insert_tx(self, tx: dict):
        try:
            self.conn.execute(
                """INSERT OR IGNORE INTO transactions
                   (chain, hash, block, timestamp, from_addr, to_addr, value, symbol, token, is_token)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tx["chain"], tx["hash"], tx["block"], tx["timestamp"],
                 tx["from"], tx["to"], tx["value"], tx["symbol"],
                 tx.get("token", ""), tx.get("is_token", 0)),
            )
            self.conn.commit()
        except Exception as e:
            print(f"  DB error: {e}")

    def get_recent(self, chain: str = None, limit: int = 50) -> list:
        if chain:
            rows = self.conn.execute(
                "SELECT * FROM transactions WHERE chain=? ORDER BY timestamp DESC LIMIT ?",
                (chain, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return rows


# ═══════════════════════════════════════════════════════════════
# TELEGRAM NOTIFIER
# ═══════════════════════════════════════════════════════════════

class TelegramNotifier:
    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    def send(self, message: str):
        if not self.enabled:
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception as e:
            print(f"  Telegram error: {e}")


# ═══════════════════════════════════════════════════════════════
# TRACKER ENGINE
# ═══════════════════════════════════════════════════════════════

class WhaleTracker:
    def __init__(self, chain: str, config: dict, db: Database, notifier: TelegramNotifier):
        self.chain = chain
        self.chain_cfg = CHAINS[chain]
        self.config = config
        self.db = db
        self.notifier = notifier
        self.min_amount = config.get("min_amount", 100)
        self.whale_addresses = set()
        self.last_block = 0
        self.api_key = config.get("chains", {}).get(chain, {}).get("api_key", "")
        self._load_whale_addresses()

    def _load_whale_addresses(self):
        """Load whale addresses from file."""
        whale_file = self.config.get("whale_file", "whale_addresses.txt")
        path = Path(whale_file)
        if path.exists():
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        addr = line.split("#")[0].strip().lower()
                        if addr.startswith("0x"):
                            self.whale_addresses.add(addr)
        # Add known labels
        for addr in KNOWN_LABELS:
            self.whale_addresses.add(addr)
        print(f"  📋 Loaded {len(self.whale_addresses)} whale addresses")

    def _get_latest_block(self) -> int:
        """Get latest block number via RPC."""
        try:
            resp = requests.post(
                self.chain_cfg["rpc"],
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                timeout=10,
            )
            return int(resp.json()["result"], 16)
        except Exception as e:
            print(f"  ❌ RPC error: {e}")
            return 0

    def _get_block_txs(self, block_num: int) -> list:
        """Get transactions from a block via RPC."""
        try:
            resp = requests.post(
                self.chain_cfg["rpc"],
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getBlockByNumber",
                    "params": [hex(block_num), True],
                    "id": 1,
                },
                timeout=15,
            )
            data = resp.json()
            return data.get("result", {}).get("transactions", [])
        except Exception as e:
            print(f"  ❌ Block fetch error: {e}")
            return []

    def _get_token_transfers(self, block_num: int) -> list:
        """Get ERC-20 transfers from explorer API."""
        if not self.api_key:
            return []
        try:
            resp = requests.get(
                self.chain_cfg["explorer_api"],
                params={
                    "module": "account",
                    "action": "tokentx",
                    "startblock": block_num,
                    "endblock": block_num,
                    "sort": "asc",
                    "apikey": self.api_key,
                },
                timeout=10,
            )
            data = resp.json()
            return data.get("result", []) if data.get("status") == "1" else []
        except Exception:
            return []

    def _label_address(self, addr: str) -> str:
        """Get label for known address."""
        addr_lower = addr.lower()
        if addr_lower in KNOWN_LABELS:
            return KNOWN_LABELS[addr_lower]
        if addr_lower in self.whale_addresses:
            return "🐋 Whale"
        return "Unknown"

    def _format_value(self, wei: int, decimals: int = 18) -> float:
        """Convert wei to human-readable value."""
        return wei / (10 ** decimals)

    def _is_whale_involved(self, from_addr: str, to_addr: str) -> bool:
        """Check if any whale address is involved."""
        return (
            from_addr.lower() in self.whale_addresses
            or to_addr.lower() in self.whale_addresses
        )

    def process_block(self, block_num: int):
        """Process a single block."""
        txs = self._get_block_txs(block_num)
        if not txs:
            return

        for tx in txs:
            value_wei = int(tx.get("value", "0x0"), 16)
            value = self._format_value(value_wei)

            if value < self.min_amount:
                continue

            from_addr = tx.get("from", "").lower()
            to_addr = (tx.get("to") or "").lower()

            if not self._is_whale_involved(from_addr, to_addr):
                continue

            tx_hash = tx.get("hash", "")
            from_label = self._label_address(from_addr)
            to_label = self._label_address(to_addr)

            record = {
                "chain": self.chain,
                "hash": tx_hash,
                "block": block_num,
                "timestamp": int(time.time()),
                "from": from_addr,
                "to": to_addr,
                "value": value,
                "symbol": self.chain_cfg["symbol"],
                "is_token": 0,
            }
            self.db.insert_tx(record)

            # Print & notify
            msg = (
                f"🐋 [{self.chain_cfg['name']}] 💸 {value:,.2f} {self.chain_cfg['symbol']}\n"
                f"From: {from_addr[:10]}... ({from_label})\n"
                f"To:   {to_addr[:10]}... ({to_label})\n"
                f"Tx: {tx_hash[:16]}...\n"
                f"🔗 {self.chain_cfg['explorer']}/tx/{tx_hash}"
            )
            print(f"\n  💸 {value:,.2f} {self.chain_cfg['symbol']}")
            print(f"     {from_label} → {to_label}")
            print(f"     {self.chain_cfg['explorer']}/tx/{tx_hash[:16]}...")
            self.notifier.send(msg)

    def poll(self, interval: int = 15):
        """Main polling loop."""
        print(f"\n🐋 Whale Tracker — {self.chain_cfg['name']}")
        print(f"  Min amount: {self.min_amount} {self.chain_cfg['symbol']}")
        print(f"  Poll interval: {interval}s")
        print("━" * 50)

        while True:
            try:
                current_block = self._get_latest_block()
                if current_block <= self.last_block:
                    time.sleep(interval)
                    continue

                if self.last_block == 0:
                    # First run — only check latest block
                    self.last_block = current_block - 1

                for block_num in range(self.last_block + 1, current_block + 1):
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"  [{ts}] Block #{block_num}", end="")
                    self.process_block(block_num)
                    print(f" ✓")

                self.last_block = current_block
                time.sleep(interval)

            except KeyboardInterrupt:
                print("\n\n  ⏹️ Stopped.")
                break
            except Exception as e:
                print(f"\n  ❌ Error: {e}")
                time.sleep(interval)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def load_config(path: str = "config.yaml") -> dict:
    p = Path(path)
    if p.exists():
        with open(p) as f:
            return yaml.safe_load(f) or {}
    return {}


def main():
    parser = argparse.ArgumentParser(description="🐋 Whale Tracker — EVM whale monitor")
    parser.add_argument("--chain", default="eth", help="Chains: eth,bsc,base,polygon,arbitrum (comma-separated)")
    parser.add_argument("--min-amount", type=float, default=100, help="Min amount to alert")
    parser.add_argument("--wallets", help="Custom whale wallets file")
    parser.add_argument("--config", default="config.yaml", help="Config file")
    parser.add_argument("--telegram-bot", help="Telegram bot token")
    parser.add_argument("--telegram-chat", help="Telegram chat ID")
    parser.add_argument("--interval", type=int, default=15, help="Poll interval (seconds)")
    parser.add_argument("--db", default="whale_tracker.db", help="Database path")
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)
    if args.min_amount:
        config["min_amount"] = args.min_amount
    if args.wallets:
        config["whale_file"] = args.wallets

    # Init
    db = Database(args.db)
    notifier = TelegramNotifier(
        bot_token=args.telegram_bot or config.get("telegram", {}).get("bot_token", ""),
        chat_id=args.telegram_chat or config.get("telegram", {}).get("chat_id", ""),
    )

    # Parse chains
    chains = [c.strip() for c in args.chain.split(",")]
    for chain in chains:
        if chain not in CHAINS:
            print(f"❌ Unknown chain: {chain}. Available: {', '.join(CHAINS.keys())}")
            return

    print("🐋 Whale Tracker Starting...")
    print(f"  Chains: {', '.join(chains)}")
    print(f"  Min amount: {args.min_amount}")
    print(f"  Telegram: {'✅' if notifier.enabled else '❌'}")

    # Run
    if len(chains) == 1:
        tracker = WhaleTracker(chains[0], config, db, notifier)
        tracker.poll(args.interval)
    else:
        # Multi-chain: use threads
        import threading

        def run_chain(chain):
            tracker = WhaleTracker(chain, config, db, notifier)
            tracker.poll(args.interval)

        threads = []
        for chain in chains:
            t = threading.Thread(target=run_chain, args=(chain,), daemon=True)
            t.start()
            threads.append(t)

        try:
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            print("\n\n  ⏹️ Stopped all trackers.")


if __name__ == "__main__":
    main()
