import os
import time
import json
import threading
from queue import Queue
from threading import Thread

from collections import defaultdict, deque
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from TelegramBot import sendMessage, sendScriptNotif
from get_watchlist import setup_driver, get_symbols, close_driver
from flask import Flask, jsonify, request

#TODO: Clean up alert_frequency such that it doesn't build up memory endlessly
#TODO: Force close connection

current_directory = os.path.dirname(__file__)
os.chdir(current_directory)

app = Flask(__name__)

# Global variables for threading and control
streaming_active = False
symbol_update_thread = None
queue_thread = None
alert_update_thread = None
queue = Queue()
my_clients = {}
symbols = []

# Input parameters
std_dev_treshold = 5
max_trade_len = 1500
min_trade_count = 500 # Num of trades required before stats can be calculated and alerts sent
update_symbol_interval = 600 # Interval (in seconds) between each symbol update
update_alerts_interval = 120 # Interval (in seconds) between each alert frequency update

# Dictionaries for trade data and alerts
trade_data = defaultdict(lambda: deque(maxlen=max_trade_len))
stats = defaultdict(lambda: {"count": 0, "sum_quantity": 0, "sum_quantity_squared": 0, "avg_quantity": 0, "std_dev": 0})
alert_frequency = defaultdict(lambda: deque())
alert_thresholds = defaultdict(lambda: std_dev_treshold)
alert_limit_per_minute = 5
alert_limit_per_hour = 30


# Insert trade into the dictionary
def insert_trade(symbol, timestamp, price, quantity):
    # Check if the deque is full (i.e., has 1000 entries)
    if len(trade_data[symbol]) == max_trade_len:
        # If deque is full, the oldest trade will be automatically removed, so adjust the stats
        old_timestamp, old_price, old_quantity = trade_data[symbol][0]
        
        # Adjust the statistics by removing the contribution of the old trade
        stats[symbol]["count"] -= 1
        stats[symbol]["sum_quantity"] -= old_quantity
        stats[symbol]["sum_quantity_squared"] -= old_quantity**2
    
    # Append the new trade to the deque
    trade_data[symbol].append((timestamp, price, quantity))
    
    # Update running statistics with the new trade
    stats[symbol]["count"] += 1
    stats[symbol]["sum_quantity"] += quantity
    stats[symbol]["sum_quantity_squared"] += quantity**2

    # Calculate the average and standard deviation
    if stats[symbol]["count"] > min_trade_count: 
        avg_quantity = stats[symbol]["sum_quantity"] / stats[symbol]["count"]
        variance = (stats[symbol]["sum_quantity_squared"] / stats[symbol]["count"]) - (avg_quantity ** 2)
        std_dev = variance ** 0.5
        stats[symbol]["avg_quantity"] = avg_quantity
        stats[symbol]["std_dev"] = std_dev

        # Check if the new quantity is greater than X standard deviations from the average
        current_threshold = alert_thresholds[symbol]
        if quantity > avg_quantity + current_threshold * std_dev:
            alert(symbol, price, quantity, avg_quantity, std_dev, current_threshold)

def format_number(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.1f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:,.1f}M"
    else:
        return f"{value:,.1f}"

def format_notional(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return str(value)

def alert(symbol, price, quantity, avg_quantity, std_dev, current_threshold):
    current_time = time.time()

    # Update frequency
    alert_frequency[symbol].append(current_time)

    notional = format_notional(price * quantity)
    tele_message = '<b>[Large Trade] - ' + symbol + ': ' + str(price) + '</b> (' + str(current_threshold) + ' s.d.)\n' \
                    + 'Volume traded: ' + str(format_number(quantity)) + '\n' \
                    + 'Notional: ' + notional + '\n' \
                    + 'Average volume: ' + str(format_number(round(avg_quantity, 2))) + '\n' \
                    + 'Std Dev: ' + str(format_number(round(std_dev, 2)))

    sendMessage(tele_message)

def message_handler(_, message):
    if isinstance(message, str):
        message = json.loads(message)
    data = message['data']
    queue.put(data)

def process_queue():
    while True:
        data = queue.get()
        if data is None:
            break
        symbol = data['s'] # !!! Gives upper case symbol, which feeds as the key to all local dictionaries
        timestamp = int(data['T'])
        price = float(data['p'])
        quantity = float(data['q'])

        # Insert trade into the dictionary and update statistics
        insert_trade(symbol, timestamp, price, quantity)

def get_watchlist():
    setup_driver()
    symbols = get_symbols()
    close_driver()
    watchlist = [symbol.split('.')[0].lower() for symbol in symbols if ".P" in symbol]
    return watchlist

# Grabs symbols from TV watchlist, subscribe/unsubscribe to aggTrade streams, sends telegram update on symbol list and number of trades registered
def update_symbols():
    global symbols, my_clients, trade_data, stats, alert_frequency, alert_thresholds
    init_message = "<b>[Update - Large Trade Alerts Symbols]</b>\n"
    while True:
        update_symbol_message = init_message
        new_symbols = get_watchlist()
        # Handle unsubscribing from symbols no longer in the list
        for symbol in list(my_clients.keys()):
            if symbol not in new_symbols:
                my_clients[symbol].stop()
                # Delete symbols from various dictionaries
                del my_clients[symbol]
                del trade_data[symbol.upper()]
                del stats[symbol.upper()]
                del alert_frequency[symbol.upper()]
                del alert_thresholds[symbol.upper()]
        
        # Handle subscribing to new symbols
        for symbol in new_symbols:
            if symbol not in my_clients:
                client = UMFuturesWebsocketClient(on_message=message_handler, is_combined=True)
                client.subscribe(stream=f"{symbol.lower()}@aggTrade")
                my_clients[symbol] = client

        symbols = new_symbols

        # Send update message
        for symbol in symbols:
            symbol = symbol.upper()
            trade_count = stats[symbol]["count"]
            update_symbol_message += f"{symbol}: {trade_count} trades\n"
        
        if update_symbol_message != init_message:
            sendMessage(update_symbol_message)
            print(">>>>>>> Alert Symbols Sent\n")

        time.sleep(update_symbol_interval)

def update_alerts():
    global symbols, alert_frequency, alert_thresholds
    default_message = "<b>[Update - Large Trade Alerts Frequency]</b>\n"
    while True:
        update_message = default_message
        for symbol in symbols:
            symbol = symbol.upper()
      
            # Calculate total time and frequency
            if len(alert_frequency[symbol]) > 1:
                current_time = time.time()
                time_delta = current_time - alert_frequency[symbol][-1]
                total_time = alert_frequency[symbol][-1] - alert_frequency[symbol][0]
                alert_rate = total_time / len(alert_frequency[symbol])  # average time between alerts
                alerts_per_minute = round(60 / alert_rate if total_time > 0 else float('inf'), 2)
                alerts_per_hour = round(3600 / alert_rate if total_time > 0 else float('inf'), 2)
            else:
                alerts_per_minute = 0
                alerts_per_hour = 0
                time_delta = 0
                        
            if alerts_per_hour > alert_limit_per_hour and 0 < time_delta <= 600: # Make sure last alert came through during the alert update interval, else don't increase threshold
                # Increase threshold to reduce alerts
                alert_thresholds[symbol] += 1
            # else:
            #     # Gradually decrease threshold if alerts are infrequent
            #     alert_thresholds[symbol] = max(alert_thresholds[symbol] - 0.1, std_dev_treshold)

            # Send update message
            update_message += f"<b>{symbol}</b>: {alerts_per_minute} / min | {alerts_per_hour} / hour -> ({alert_thresholds[symbol]} s.d.) \n"
        
        # Send message if there are alerts
        if update_message != default_message:
            sendMessage(update_message)
            print(">>>>>>> Alert Frequency Sent\n")

        time.sleep(update_alerts_interval)
    
# Function to start alert streaming
def start_streaming():
    global streaming_active, symbol_update_thread, queue_thread, alert_update_thread
    if streaming_active:
        return
    streaming_active = True

    symbol_update_thread = Thread(target=update_symbols, daemon=True)
    queue_thread = Thread(target=process_queue, daemon=True)
    alert_update_thread = Thread(target=update_alerts, daemon=True)

    symbol_update_thread.start()
    queue_thread.start()
    alert_update_thread.start()


'''
Flask web app routes
'''
@app.route('/start', methods=['GET'])
def start():
    thread = Thread(target=start_streaming, daemon=True)
    thread.start()
    return jsonify({'status': 'streaming started'}), 200

@app.route('/stop', methods=['GET'])
def stop():
    global streaming_active, my_clients, trade_data, stats, alert_frequency, alert_thresholds, queue

    if not streaming_active:
        return jsonify({'status': 'not running'}), 400
    
    # Set the streaming flag to False
    streaming_active = False
    
    # Attempt to join threads
    if symbol_update_thread:
        symbol_update_thread.join(timeout=1)  # Timeout to avoid blocking forever
    if queue_thread:
        queue_thread.join(timeout=1)
    if alert_update_thread:
        alert_update_thread.join(timeout=1)

    # Forcefully stop WebSocket clients
    for symbol in list(my_clients.keys()):
        try:
            my_clients[symbol].stop()
            my_clients[symbol].ws.close()
        except Exception as e:
            print(f"Error stopping client {symbol}: {e}")
    
    # Signal the queue processing thread to exit
    queue.put(None)

    # Clear all data structures
    my_clients.clear()
    trade_data.clear()
    stats.clear()
    alert_frequency.clear()
    alert_thresholds.clear()

    # Reset the queue to a new instance
    queue = Queue()

    return jsonify({'status': 'streaming stopped'}), 200


@app.route('/')
def index():
    return "Alert Streaming Service up and running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)