"""Kairos Hyperliquid MCP: HYPE Spot historical market data, no trading tools."""
import os
from fastmcp import FastMCP
from hyperliquid_data import market_info, spot_ohlcv

mcp = FastMCP('Kairos Hyperliquid Historical Spot')

@mcp.tool()
def get_hype_spot_market() -> dict:
    """Identify the native HYPE/USDC Spot pair via Hyperliquid spotMeta; no account access."""
    return market_info()

@mcp.tool()
def get_hype_spot_ohlcv(interval: str='1w', start_date: str='2024-11-29',
                        end_date: str|None=None, limit: int=250) -> dict:
    """Retrieve actual closed HYPE/USDC Spot OHLCV 1h/4h/1d/1w (last 5000 source candles available).
    For macro CH/CL use weekly/daily; do not infer Elliott waves or replace approved anchors.
    May return fewer than requested; does not fill gaps, synthesize or mix futures/Binance prices.
    """
    return spot_ohlcv(interval,start_date,end_date,limit)

if __name__=='__main__':
    mcp.run(transport='http',host='0.0.0.0',port=int(os.environ.get('PORT','10000')))
