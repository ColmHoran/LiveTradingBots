import os
import sys
import json
import ta
from datetime import datetime
from typing import Dict

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from utilities.binance_futures import BinanceFutures
from utilities.binance_api_triggers import BinanceTriggerOrders

# --- CONFIG ---
params = {
    'symbol': 'ETH/USDT',
    'timeframe': '1h',
    'margin_mode': 'isolated',
    'balance_fraction': 1.0,  # 100% of balance
    'leverage': 2,
    'average_type': 'SMA',
    'average_period': 4,
    'envelopes': [0.1, 0.2, 0.3],
    'stop_loss_pct': 0.5,
    'use_longs': True,
    'use_shorts': True,
}


key_path = 'secret.json'
key_name = 'envelope'
tracker_file = f"/code/strategies/envelope/tracker_{params['symbol'].replace('/', '-')}.json"
trigger_price_delta = 0.005

if not os.path.exists(tracker_file):
    os.makedirs(os.path.dirname(tracker_file), exist_ok=True)
    with open(tracker_file, 'w') as file:
        json.dump({"status": "ok_to_trade", "last_side": None, "stop_loss_ids": []}, file)
        
print(f"\n{datetime.now().strftime('%H:%M:%S')}: >>> starting execution for {params['symbol']}")

with open(key_path, "r") as f:
    api_setup = json.load(f)[key_name]

binance = BinanceFutures(api_setup, use_testnet=True)
trigger_api = BinanceTriggerOrders(api_setup['apiKey'], api_setup['secret'])

if not os.path.exists(tracker_file):
    with open(tracker_file, 'w') as file:
        json.dump({"status": "ok_to_trade", "last_side": None, "stop_loss_ids": []}, file)

def read_tracker_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def update_tracker_file(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file)

# --- CANCEL OPEN ORDERS ---
orders = binance.fetch_open_orders(params['symbol'])
for order in orders:
    binance.cancel_order(order['id'], params['symbol'])

# Skip trigger order cancellation for now or use Binance API if storing IDs
long_orders_left = short_orders_left = 0
print(f"{datetime.now().strftime('%H:%M:%S')}: orders cancelled")

# --- FETCH OHLCV & INDICATORS ---
data = binance.fetch_recent_ohlcv(params['symbol'], params['timeframe'], 100).iloc[:-1]
if params['average_type'] == 'DCM':
    ta_obj = ta.volatility.DonchianChannel(data['high'], data['low'], data['close'], window=params['average_period'])
    data['average'] = ta_obj.donchian_channel_mband()
elif params['average_type'] == 'SMA':
    data['average'] = ta.trend.sma_indicator(data['close'], window=params['average_period'])
elif params['average_type'] == 'EMA':
    data['average'] = ta.trend.ema_indicator(data['close'], window=params['average_period'])
elif params['average_type'] == 'WMA':
    data['average'] = ta.trend.wma_indicator(data['close'], window=params['average_period'])
else:
    raise ValueError(f"Unsupported average type: {params['average_type']}")

for i, e in enumerate(params['envelopes']):
    data[f'band_high_{i + 1}'] = data['average'] / (1 - e)
    data[f'band_low_{i + 1}'] = data['average'] * (1 - e)

print(f"{datetime.now().strftime('%H:%M:%S')}: ohlcv data fetched")

# --- POSITION CHECK ---
positions = binance.fetch_open_positions(params['symbol'])
position = positions[0] if positions else None
open_position = position is not None

if open_position:
    print(f"{datetime.now().strftime('%H:%M:%S')}: {position['side']} position of {round(position['contracts'] * position['contractSize'],2)} contracts")

# --- STOP LOSS CHECK (manual tracking) ---
tracker_info = read_tracker_file(tracker_file)

# --- CANCEL OLD SL ORDERS ---
for sl_id in tracker_info.get('stop_loss_ids', []):
    try:
        trigger_api.cancel_order(params['symbol'], sl_id)
        print(f"{datetime.now().strftime('%H:%M:%S')}: cancelled old SL order {sl_id}")
    except Exception as e:
        print(f"{datetime.now().strftime('%H:%M:%S')}: failed to cancel SL order {sl_id}: {e}")

# Clear stop-loss tracking before placing new ones
tracker_info['stop_loss_ids'] = []
update_tracker_file(tracker_file, tracker_info)

# --- MARGIN/LEVERAGE SETUP ---
if not open_position:
    binance.set_margin_mode(params['symbol'], margin_mode=params['margin_mode'])
    binance.set_leverage(params['symbol'], margin_mode=params['margin_mode'], leverage=params['leverage'])

# --- PLACE NEW ORDERS ---
balance = params['balance_fraction'] * params['leverage'] * binance.fetch_balance()['USDT']['total']
print(f"{datetime.now().strftime('%H:%M:%S')}: trading balance is {balance}")

# For each envelope band, place conditional entry and stop-loss orders manually
for i, e in enumerate(params['envelopes']):
    long_price = data[f'band_low_{i + 1}'].iloc[-1]
    short_price = data[f'band_high_{i + 1}'].iloc[-1]
    
    amount = balance / len(params['envelopes']) / data['close'].iloc[-1]
    min_amount = binance.fetch_min_amount_tradable(params['symbol'])
    if amount < min_amount:
        continue

    if params['use_longs']:
        stop_price = long_price * (1 - params['stop_loss_pct'])
        trigger_api.place_stop_market_order(
            symbol=params['symbol'],
            side='SELL',
            quantity=amount,
            stop_price=stop_price,
            reduce_only=True
        )

        print(f"{datetime.now().strftime('%H:%M:%S')}: placed long stop-loss at {stop_price}")

    if params['use_shorts']:
        stop_price = short_price * (1 + params['stop_loss_pct'])
        trigger_api.place_stop_market_order(
            symbol=params['symbol'],
            side='BUY',
            quantity=amount,
            stop_price=stop_price,
            reduce_only=True
        )
        print(f"{datetime.now().strftime('%H:%M:%S')}: placed short stop-loss at {stop_price}")

update_tracker_file(tracker_file, tracker_info)
print(f"{datetime.now().strftime('%H:%M:%S')}: <<< all done")

