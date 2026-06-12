#!/usr/bin/env python3
"""
Polymarket Whale Tracker
========================
Pantau trade gede ("whale") di Polymarket secara real-time, follow address
tertentu, dan analisa portofolio sebuah wallet. Read-only & legit — cuma baca
data publik dari Data API Polymarket, gak nyentuh transaksi siapapun.

Pakai:
  # 1. Sekali scan trade terbaru, flag whale >= $1000
  python whale_tracker.py scan --min-usd 1000

  # 2. Monitor terus-terusan (real-time), refresh tiap 15 detik
  python whale_tracker.py watch --min-usd 5000 --interval 15

  # 3. Follow address spesifik (alert tiap mereka trade)
  python whale_tracker.py watch --min-usd 0 --follow 0xabc...,0xdef...

  # 4. Analisa 1 wallet (saldo, posisi, PnL, trade terakhir)
  python whale_tracker.py wallet 0xe8072d531800ee0d57f3951f85f15de9b30f4dc8

  # 5. Leaderboard: trader tergede dari N trade terakhir
  python whale_tracker.py leaderboard --lookback 1000
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = "https://data-api.polymarket.com"


def _get(path, params=None):
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "polymarket-whale-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_trades(limit=500, offset=0):
    """Recent trades across all markets. size=shares, price=0..1, USD=size*price."""
    return _get("/trades", {"limit": limit, "offset": offset})


def fetch_positions(wallet, limit=100):
    return _get("/positions", {"user": wallet, "limit": limit, "sortBy": "CURRENT", "sortDirection": "DESC"})


def fetch_value(wallet):
    data = _get("/value", {"user": wallet})
    return data[0]["value"] if data else 0.0


def usd(trade):
    return float(trade.get("size", 0)) * float(trade.get("price", 0))


def fmt_money(x):
    return f"${x:,.2f}"


def short_addr(a):
    return f"{a[:6]}...{a[-4:]}" if a and len(a) > 12 else a


def ts_str(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def trade_line(t):
    name = t.get("name") or t.get("pseudonym") or short_addr(t.get("proxyWallet", ""))
    side = t.get("side", "?")
    arrow = "🟢 BUY " if side == "BUY" else "🔴 SELL"
    return (
        f"{arrow} {fmt_money(usd(t)):>12}  {name[:22]:<22}  "
        f"{t.get('outcome','?'):<6} @ {float(t.get('price',0)):.3f}  | {t.get('title','')[:55]}"
    )


def cmd_scan(args):
    trades = fetch_trades(limit=args.lookback)
    if args.follow:
        follow = {a.strip().lower() for a in args.follow.split(",") if a.strip()}
        trades = [t for t in trades if t.get("proxyWallet", "").lower() in follow]
    whales = [t for t in trades if usd(t) >= args.min_usd]
    whales.sort(key=usd, reverse=True)
    print(f"\n🐋 WHALE SCAN — {len(whales)} trade >= {fmt_money(args.min_usd)} "
          f"(dari {len(trades)} trade terakhir)\n" + "-" * 110)
    for t in whales[: args.top]:
        print(trade_line(t))
    total = sum(usd(t) for t in whales)
    print("-" * 110)
    print(f"Total volume whale: {fmt_money(total)}\n")
    return whales


def cmd_watch(args):
    follow = {a.strip().lower() for a in args.follow.split(",") if a.strip()} if args.follow else None
    seen = set()
    print(f"👀 WATCHING Polymarket — min {fmt_money(args.min_usd)}"
          + (f", follow {len(follow)} wallet" if follow else "")
          + f", refresh {args.interval}s. Ctrl+C buat stop.\n")
    try:
        while True:
            try:
                trades = fetch_trades(limit=args.lookback)
            except Exception as e:
                print(f"⚠️  fetch error: {e}", file=sys.stderr)
                time.sleep(args.interval)
                continue
            new = []
            for t in trades:
                key = t.get("transactionHash", "") + t.get("asset", "") + str(t.get("timestamp"))
                if key in seen:
                    continue
                seen.add(key)
                if follow and t.get("proxyWallet", "").lower() not in follow:
                    continue
                if usd(t) >= args.min_usd:
                    new.append(t)
            new.sort(key=lambda x: x.get("timestamp", 0))
            for t in new:
                print(f"[{ts_str(t.get('timestamp'))}] {trade_line(t)}")
            if len(seen) > 20000:  # keep memory bounded
                seen = set(list(seen)[-10000:])
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n👋 Stopped.")


def cmd_wallet(args):
    w = args.address
    val = fetch_value(w)
    positions = fetch_positions(w, limit=200)
    trades = [t for t in fetch_trades(limit=1000) if t.get("proxyWallet", "").lower() == w.lower()]
    open_pos = [p for p in positions if float(p.get("currentValue", 0)) > 0.01]
    total_pnl = sum(float(p.get("cashPnl", 0)) for p in positions)
    print(f"\n💼 WALLET {w}")
    print("-" * 90)
    print(f"Saldo posisi sekarang : {fmt_money(val)}")
    print(f"Total PnL (all-time)  : {fmt_money(total_pnl)}")
    print(f"Posisi terbuka        : {len(open_pos)}")
    print("\nTop posisi terbuka (by value):")
    for p in sorted(open_pos, key=lambda x: float(x.get("currentValue", 0)), reverse=True)[:10]:
        pnl = float(p.get("cashPnl", 0))
        print(f"  {fmt_money(float(p.get('currentValue',0))):>12}  "
              f"PnL {fmt_money(pnl):>12}  {p.get('outcome','?'):<6} | {p.get('title','')[:50]}")
    print("\nTrade terakhir:")
    for t in sorted(trades, key=lambda x: x.get("timestamp", 0), reverse=True)[:10]:
        print(f"  [{ts_str(t.get('timestamp'))}] {trade_line(t)}")
    print()


def cmd_leaderboard(args):
    trades = fetch_trades(limit=args.lookback)
    agg = {}
    for t in trades:
        w = t.get("proxyWallet", "")
        a = agg.setdefault(w, {"name": t.get("name") or t.get("pseudonym") or short_addr(w),
                               "vol": 0.0, "n": 0})
        a["vol"] += usd(t)
        a["n"] += 1
    ranked = sorted(agg.items(), key=lambda kv: kv[1]["vol"], reverse=True)
    print(f"\n🏆 LEADERBOARD — top trader dari {len(trades)} trade terakhir\n" + "-" * 80)
    print(f"{'#':>2}  {'Volume':>14}  {'Trades':>6}  {'Trader':<22}  Wallet")
    for i, (w, a) in enumerate(ranked[: args.top], 1):
        print(f"{i:>2}  {fmt_money(a['vol']):>14}  {a['n']:>6}  {a['name'][:22]:<22}  {short_addr(w)}")
    print()


def main():
    p = argparse.ArgumentParser(description="Polymarket Whale Tracker (read-only)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scan", help="Sekali scan trade terbaru")
    sc.add_argument("--min-usd", type=float, default=1000)
    sc.add_argument("--lookback", type=int, default=500, help="jumlah trade terakhir yg diambil (max ~1000)")
    sc.add_argument("--top", type=int, default=30)
    sc.add_argument("--follow", type=str, default="")
    sc.set_defaults(func=cmd_scan)

    wt = sub.add_parser("watch", help="Monitor real-time")
    wt.add_argument("--min-usd", type=float, default=5000)
    wt.add_argument("--interval", type=int, default=15)
    wt.add_argument("--lookback", type=int, default=500)
    wt.add_argument("--follow", type=str, default="")
    wt.set_defaults(func=cmd_watch)

    wl = sub.add_parser("wallet", help="Analisa 1 wallet")
    wl.add_argument("address", type=str)
    wl.set_defaults(func=cmd_wallet)

    lb = sub.add_parser("leaderboard", help="Top trader by volume")
    lb.add_argument("--lookback", type=int, default=1000)
    lb.add_argument("--top", type=int, default=20)
    lb.set_defaults(func=cmd_leaderboard)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
