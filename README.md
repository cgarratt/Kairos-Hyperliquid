# Kairos Hyperliquid MCP — Read-only Historical Spot (v1.0)

## Purpose
Separate MCP from Binance: HYPE/USDC *Spot* historical OHLCV, to reconcile existing CH/CL and Elliott wave history. **No trading, no authentication, no keys, no wallet**. Does not change Binance BSI or Kairos positions.

## Tools
- `get_hype_spot_market()` resolves the official native HYPE/USDC spot identifier dynamically from `spotMeta` (normally `@107`).
- `get_hype_spot_ohlcv(interval='1w', start_date='2024-11-29', end_date=None, limit=250)` returns only actual closed candles for 1h, 4h, 1d, 1w. Fewer than `limit` is allowed and flagged. **No interpolation or futures data.**

Hyperliquid API: `POST https://api.hyperliquid.xyz/info` with `spotMeta` and `candleSnapshot` requests. Hyperliquid currently documents only the most recent **5000 candles** retained at the API endpoint; requesting older dates cannot override that. Coverage before Binance listing must be verified with live output after deployment.

## Deploy to Render (separate service)
1. Create a NEW GitHub repository `Kairos-Hyperliquid` (without changing Kairos-Binance).
2. Upload the contents of this directory to the repository root; commit to `main`.
3. Render Dashboard > New > Web Service > select that repository.
4. Name `kairos-hyperliquid` (must be available), Branch `main`, Language `Docker`.
5. Root Directory BLANK, Dockerfile Path `./Dockerfile`, Docker Build Context `.` (if files are in root).
6. No credentials or API keys. `PORT` is provided by Render (default 10000); application listens on `0.0.0.0`.
7. Deploy and verify `Live`. The MCP endpoint is `<actual Render HTTPS URL>/mcp`.
8. Add a **second** custom MCP connection in ChatGPT using that HTTPS URL; do not delete Binance MCP.
9. Run `get_hype_spot_market` then `get_hype_spot_ohlcv` for `1w` and `1d`. Confirm returned first candle and coverage *before* deleting HYPE Fibo image.

## Safeguards
- Treat all derived pivots and Fibo history as EXPLORATORY until matched to approved TradingView anchors.
- HYPE/USDC on Hyperliquid Spot is distinct from HYPE/USDT Binance; do not concatenate or substitute without quote/venue reconciliation.
- Does not retrieve HYPE perpetual futures data.
- `INFO` requests have Hyperliquid per-IP rate limits. Avoid repeated large queries without caching.

## Tests
`python -m unittest discover -p 'test_*.py'`

## Live check
Network access to `api.hyperliquid.xyz` was not available in the build container; unit tests validate parsing but **not live historical coverage**. Check after deploying to Render.
