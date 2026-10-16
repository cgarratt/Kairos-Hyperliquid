"""Hyperliquid HYPE/USDC Spot public market data (READ-ONLY). No trading credentials."""
import datetime as dt
import json
import math
import urllib.error
import urllib.request
from functools import lru_cache
from decimal import Decimal, InvalidOperation

API = 'https://api.hyperliquid.xyz/info'
DAY_MS = 86_400_000
INTERVAL_MS = {'1h': 3_600_000, '4h': 14_400_000, '1d': DAY_MS, '1w': 7 * DAY_MS}
BASE_DATE = '2024-11-29'


def _now_ms():
    return int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)


def _date_ms(day: str, next_day=False) -> int:
    d = dt.date.fromisoformat(day)
    if next_day:
        d += dt.timedelta(days=1)
    return int(dt.datetime.combine(d, dt.time.min, tzinfo=dt.timezone.utc).timestamp() * 1000)


def _iso(ms: int):
    return dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc).isoformat()


def _info(payload: dict):
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(API, data=data,
        headers={'Content-Type':'application/json', 'User-Agent':'Kairos-Hyperliquid-ReadOnly/1.0'}, method='POST')
    with urllib.request.urlopen(request, timeout=25) as resp:
        if resp.status != 200:
            raise ValueError(f'HTTP {resp.status}')
        return json.load(resp)


def _spot_pair(meta):
    if not isinstance(meta, dict) or not isinstance(meta.get('tokens'), list) or not isinstance(meta.get('universe'), list):
        raise ValueError('Invalid spotMeta response')
    tokens = {p['index']:p['name'] for p in meta['tokens']}
    pairs = [p for p in meta['universe'] if isinstance(p,dict) and len(p.get('tokens',[]))==2
        and tokens.get(p['tokens'][0])=='HYPE' and tokens.get(p['tokens'][1])=='USDC']
    if len(pairs)!=1 or not str(pairs[0].get('name','')).startswith('@'):
        raise ValueError(f'Could not uniquely identify HYPE/USDC Spot (found {len(pairs)})')
    return pairs[0]['name']


def _market():
    return _spot_pair(_info({'type':'spotMeta'}))


def market_info():
    try:
        pair = _market()
        return {'status':'OK','source':'Hyperliquid Spot','pair':'HYPE/USDC','api_coin':pair,
            'endpoint':API,'wallet_needed':False,'can_trade':False,'scope':'READ_ONLY'}
    except (ValueError,KeyError,IndexError,TypeError,TimeoutError,OSError,urllib.error.URLError) as err:
        return {'status':'DATA_ERROR','reason':str(err),'scope':'READ_ONLY'}


def _clean_candles(data, interval, start_ms, end_ms, max_count):
    if not isinstance(data,list):
        raise ValueError('Invalid candleSnapshot response type')
    selected=[]
    for i,c in enumerate(data):
        if not isinstance(c,dict) or any(k not in c for k in ('t','T','o','h','l','c','v')):
            raise ValueError(f'Malformed candle at index {i}')
        t=int(c['t']); close_exclusive=t+INTERVAL_MS[interval]
        if t<start_ms or t>=end_ms or close_exclusive>end_ms:
            continue
        try:
            op,hi,lo,cl,vol=(Decimal(str(c[k])) for k in ('o','h','l','c','v'))
        except (ValueError,InvalidOperation) as e:
            raise ValueError(f'Invalid OHLC at {t}: {e}') from e
        if (not all(v.is_finite() for v in (op,hi,lo,cl,vol)) or
            min(op,hi,lo,cl)<=0 or vol<0 or hi<max(op,cl,lo) or lo>min(op,cl,hi)):
            raise ValueError(f'Invalid OHLC range at {_iso(t)}')
        if int(c['T'])<t or int(c['T'])>close_exclusive:
            raise ValueError(f'Invalid closeTime at {_iso(t)}')
        selected.append({'open_utc':_iso(t), 'close_utc':_iso(close_exclusive),
            'open':str(op),'high':str(hi),'low':str(lo),'close':str(cl),'volume_base':str(vol)})
    selected.sort(key=lambda x:x['open_utc'])
    gaps=[]
    for left,right in zip(selected,selected[1:]):
        delta=int(dt.datetime.fromisoformat(right['open_utc']).timestamp()*1000)-int(dt.datetime.fromisoformat(left['open_utc']).timestamp()*1000)
        if delta!=INTERVAL_MS[interval]:
            gaps.append({'after':left['open_utc'],'before':right['open_utc'],'delta_ms':delta})
    if len({c['open_utc'] for c in selected})!=len(selected):
        raise ValueError('Duplicate candle timestamps')
    return selected[-max_count:], gaps


def spot_ohlcv(interval='1w', start_date=BASE_DATE, end_date=None, limit=250):
    """Return closed-only HYPE/USDC spot candles, not perps. Can be partial history."""
    try:
        if interval not in INTERVAL_MS:
            raise ValueError(f'Unsupported interval {interval!r}: use 1h, 4h, 1d, 1w')
        if not isinstance(limit,int) or not 1<=limit<=1500:
            raise ValueError('limit must be 1..1500')
        start_ms=_date_ms(start_date)
        end_ms=min(_date_ms(end_date,True) if end_date else _now_ms(),_now_ms())
        if start_ms>=end_ms:
            raise ValueError('start_date must precede end_date / current UTC time')
        pair=_market()
        candles=_info({'type':'candleSnapshot','req':{
            'coin':pair,'interval':interval,'startTime':start_ms,'endTime':end_ms}})
        records,gaps=_clean_candles(candles,interval,start_ms,end_ms,limit)
        if not records:
            return {'status':'DATA_ERROR','reason':'No closed HYPE/USDC spot candles in requested range',
                'source':'Hyperliquid Spot','scope':'READ_ONLY'}
        return {'status':'OK' if not gaps else 'INCOMPLETE','source':'Hyperliquid Spot',
            'pair':'HYPE/USDC','api_coin':pair,'interval':interval,'closed_only':True,
            'requested_start_date':start_date,'requested_end_date':end_date,
            'returned':len(records),'limit':limit,'partial_history':len(records)<limit,
            'first_open_utc':records[0]['open_utc'],'last_close_utc':records[-1]['close_utc'],
            'gaps_count':len(gaps),'gaps':gaps[:10], 'scope':'EXPLORATORY_ONLY',
            'warning':'USDC Spot source. Do not mix with Binance HYPEUSDT or auto-update approved Kairos CH/CL/O1-O5.',
            'records':records}
    except (ValueError,KeyError,IndexError,TypeError,TimeoutError,OSError,urllib.error.URLError) as err:
        return {'status':'DATA_ERROR','reason':str(err),'source':'Hyperliquid Spot','scope':'READ_ONLY'}
