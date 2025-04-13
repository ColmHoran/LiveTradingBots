import ccxt
import time
import pandas as pd
from typing import Any, Optional, Dict, List


class BinanceFutures():
    def __init__(self, api_setup: Optional[Dict[str, Any]] = None, use_testnet: bool = False) -> None:
        if api_setup is None:
            api_setup = {}

        api_setup.setdefault("options", {"defaultType": "future"})

        if use_testnet:
            api_setup['urls'] = {
                'api': {
                    'public': 'https://testnet.binancefuture.com/fapi/v1',
                    'private': 'https://testnet.binancefuture.com/fapi/v1'
                }
            }


    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return self.session.fetch_ticker(symbol)

    def fetch_min_amount_tradable(self, symbol: str) -> float:
        return self.markets[symbol]['limits']['amount']['min']

    def amount_to_precision(self, symbol: str, amount: float) -> str:
        return self.session.amount_to_precision(symbol, amount)

    def price_to_precision(self, symbol: str, price: float) -> str:
        return self.session.price_to_precision(symbol, price)

    def fetch_balance(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.session.fetch_balance(params or {})

    def fetch_order(self, id: str, symbol: str) -> Dict[str, Any]:
        return self.session.fetch_order(id, symbol)

    def fetch_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        return self.session.fetch_open_orders(symbol)

    def fetch_open_trigger_orders(self, symbol: str) -> List[Dict[str, Any]]:
        # Simulated as Binance trigger orders are not directly available via CCXT
        return []

    def fetch_closed_trigger_orders(self, symbol: str) -> List[Dict[str, Any]]:
        return []  # Needs custom implementation via Binance API if needed

    def cancel_order(self, id: str, symbol: str) -> Dict[str, Any]:
        return self.session.cancel_order(id, symbol)

    def cancel_trigger_order(self, id: str, symbol: str) -> Dict[str, Any]:
        return {}  # Not supported in CCXT for Binance

    def fetch_open_positions(self, symbol: str) -> List[Dict[str, Any]]:
        all_positions = self.session.fetch_positions([symbol])
        return [pos for pos in all_positions if float(pos.get('contracts', 0)) > 0]

    def flash_close_position(self, symbol: str, side: Optional[str] = None) -> Dict[str, Any]:
        # This assumes market order with correct side and full size. Customize as needed.
        return self.place_market_order(symbol, 'sell' if side == 'long' else 'buy', 0, reduce=True)

    def set_margin_mode(self, symbol: str, margin_mode: str = 'isolated') -> None:
        self.session.set_margin_mode(margin_mode, symbol)

    def set_leverage(self, symbol: str, margin_mode: str = 'isolated', leverage: int = 1) -> None:
        self.session.set_leverage(leverage, symbol)

    def fetch_recent_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        data = self.session.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df

    def place_market_order(self, symbol: str, side: str, amount: float, reduce: bool = False) -> Dict[str, Any]:
        amount = self.amount_to_precision(symbol, amount)
        return self.session.create_order(symbol, 'market', side, amount, params={'reduceOnly': reduce})

    def place_limit_order(self, symbol: str, side: str, amount: float, price: float, reduce: bool = False) -> Dict[str, Any]:
        amount = self.amount_to_precision(symbol, amount)
        price = self.price_to_precision(symbol, price)
        return self.session.create_order(symbol, 'limit', side, amount, price, params={'reduceOnly': reduce})

    def place_trigger_market_order(self, *args, **kwargs):
        print("Trigger orders not supported via CCXT for Binance. Use polling or Binance API directly.")
        return None

    def place_trigger_limit_order(self, *args, **kwargs):
        print("Trigger orders not supported via CCXT for Binance. Use polling or Binance API directly.")
        return None
