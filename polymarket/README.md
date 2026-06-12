# 🐋 Polymarket Whale Tracker

Pantau trade gede ("whale") di Polymarket secara real-time, follow address tertentu,
dan analisa portofolio sebuah wallet — buat bantu keputusan trading kamu.

**100% read-only & legit.** Cuma baca data publik dari Data API Polymarket
(`data-api.polymarket.com`). Gak nyentuh / gak ngubah transaksi siapapun.

## Cara pakai

Butuh Python 3 aja. **Gak perlu install apa-apa** (pakai library bawaan Python).

```bash
# 1. Scan trade terbaru, flag whale >= $1000
python3 whale_tracker.py scan --min-usd 1000

# 2. Monitor real-time (refresh tiap 15 detik), alert whale >= $5000
python3 whale_tracker.py watch --min-usd 5000 --interval 15

# 3. Follow address spesifik — alert tiap mereka trade (set min-usd 0)
python3 whale_tracker.py watch --min-usd 0 --follow 0xabc...,0xdef...

# 4. Analisa 1 wallet: saldo, posisi terbuka, PnL, trade terakhir
python3 whale_tracker.py wallet 0xe8072d531800ee0d57f3951f85f15de9b30f4dc8

# 5. Leaderboard trader tergede dari N trade terakhir
python3 whale_tracker.py leaderboard --lookback 1000 --top 20
```

## Penjelasan kolom
- **USD value** = `size` (jumlah share) × `price` (0..1). Ini nilai dolar trade-nya.
- **BUY/SELL** = arah trade. **outcome** = sisi pasar yg dibeli (Yes/No/nama tim, dll).
- **price** = harga per share saat itu, sekaligus implied probability (0.823 ≈ 82%).

## Ide pemakaian buat trading
- Jalanin `watch` di pasar yg lagi kamu pantau, set threshold sesuai gaya kamu.
- Kalau ada whale masuk gede di satu outcome, itu sinyal sentimen — tapi **bukan
  jaminan**. Tetap riset sendiri (DYOR).
- Pakai `leaderboard` buat nemu wallet whale yg aktif, terus `wallet <addr>` buat
  liat track record & posisi mereka, lalu `--follow` address-nya.

## Catatan
- Endpoint `/trades` ngambil sampai ~1000 trade terakhir per panggilan. Buat history
  lebih jauh per-wallet, Polymarket batesin di sini.
- Kalau mau dijadiin alert ke Telegram/Discord/Slack, tinggal sambung output `watch`
  ke webhook — bisa aku bantu kalau mau.
