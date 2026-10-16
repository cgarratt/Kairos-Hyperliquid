import unittest
from unittest.mock import patch
import hyperliquid_data as h

META={'tokens':[{'index':150,'name':'HYPE'}, {'index':0,'name':'USDC'}, {'index':151,'name':'OTHER'}],
      'universe':[{'name':'@107','tokens':[150,0]}, {'name':'@108','tokens':[151,0]}]}

class TestHyperliquid(unittest.TestCase):
    def test_market_id(self):
        self.assertEqual(h._spot_pair(META),'@107')
    def test_reject_nonspot(self):
        with self.assertRaises(ValueError):h._spot_pair({'tokens':[{'index':150,'name':'HYPE'}],'universe':[]})
    def test_reject_bad_interval(self):
        self.assertEqual(h.spot_ohlcv('1M')['status'],'DATA_ERROR')
    def test_return_closed_only(self):
        one=h.DAY_MS; t=h._date_ms('2025-01-01');
        items=[{'t':t+i*one,'T':t+(i+1)*one-1,'o':'25','h':'27','l':'24','c':'26','v':'9'} for i in range(3)]
        with patch.object(h,'_market',return_value='@107'), patch.object(h,'_info',return_value=items), patch.object(h,'_now_ms',return_value=t+2*one+3600):
            v=h.spot_ohlcv('1d','2025-01-01',limit=10)
        self.assertEqual(v['status'],'OK');self.assertEqual(v['returned'],2)
        self.assertTrue(v['partial_history'])
    def test_detect_gap(self):
        one=h.DAY_MS;t=h._date_ms('2025-01-01')
        data=[{'t':t+i*one,'T':t+(i+1)*one-1,'o':'25','h':'27','l':'24','c':'26','v':'9'} for i in (0,2)]
        with patch.object(h,'_market',return_value='@107'),patch.object(h,'_info',return_value=data),patch.object(h,'_now_ms',return_value=t+4*one):
            v=h.spot_ohlcv('1d','2025-01-01',limit=10)
        self.assertEqual(v['status'],'INCOMPLETE');self.assertEqual(v['gaps_count'],1)
    def test_reject_bad_price(self):
        t=h._date_ms('2025-01-01');bad=[{'t':t,'T':t+h.DAY_MS-1,'o':'25','h':'23','l':'24','c':'26','v':'1'}]
        with patch.object(h,'_market',return_value='@107'),patch.object(h,'_info',return_value=bad),patch.object(h,'_now_ms',return_value=t+3*h.DAY_MS):
            v=h.spot_ohlcv('1d','2025-01-01',limit=10)
        self.assertEqual(v['status'],'DATA_ERROR')

if __name__=='__main__':unittest.main()
