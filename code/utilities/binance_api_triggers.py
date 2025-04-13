import time
import hmac
import hashlib
import requests
from typing import Optional, Dict


class BinanceTriggerOrders:
    BASE_URL = "https://fapi.binance.com"

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    def _sign(self, params: Dict[str, str]) -> str:
        query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
        return hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    def _send_signed_request(self, method: str, endpoint: str, params: Dict[str, str]) -> Dict:
        url = self.BASE_URL + endpoint
        timestamp = int(time.time() * 1000)
        params['timestamp'] = timestamp
        query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
        signature = self._sign(params)
        query_string += f"&signature={signature}"

        headers = {
            'X-MBX-APIKEY': self.api_key
        }

        if method.upper() == 'POST':
            response = requests.post(url + '?' + query_string, headers=headers)
        elif method.upper() == 'GET':
            response = requests.get(url + '?' + query_string, headers=headers)
        elif method.upper() == 'DELETE':
            response = requests.delete(url + '?' + query_string, headers=headers)
        else:
            raise ValueError("Invalid method")

        return response.json()

    def place_stop_market_order(self, symbol: str, side: str, quantity: float, stop_price: float, reduce_only: bool = False) -> Dict:
        params = {
            'symbol': symbol.replace('/', ''),
            'side': side.upper(),
            'type': 'STOP_MARKET',
            'stopPrice': f"{stop_price:.2f}",
            'closePosition': 'true' if reduce_only else 'false',
            'quantity': quantity,
            'timeInForce': 'GTC',
            'workingType': 'CONTRACT_PRICE'
        }
        return self._send_signed_request('POST', '/fapi/v1/order', params)

    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        params = {
            'symbol': symbol.replace('/', ''),
            'orderId': order_id
        }
        return self._send_signed_request('DELETE', '/fapi/v1/order', params)

    def fetch_open_orders(self, symbol: str) -> Dict:
        params = {
            'symbol': symbol.replace('/', '')
        }
        return self._send_signed_request('GET', '/fapi/v1/openOrders', params)

    def fetch_all_orders(self, symbol: str, limit: int = 50) -> Dict:
        params = {
            'symbol': symbol.replace('/', ''),
            'limit': limit
        }
        return self._send_signed_request('GET', '/fapi/v1/allOrders', params)
