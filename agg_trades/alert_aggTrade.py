''' [WORKING]

Sample output:
{
  "e": "aggTrade",  // Event type
  "E": 123456789,   // Event time
  "s": "BTCUSDT",    // Symbol
  "a": 5933014,     // Aggregate trade ID
  "p": "0.001",     // Price
  "q": "100",       // Quantity
  "f": 100,         // First trade ID
  "l": 105,         // Last trade ID
  "T": 123456785,   // Trade time
  "m": true,        // Is the buyer the market maker?
}
'''

import os
import time
import json
import threading
from queue import Queue
from collections import defaultdict, deque
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from TelegramBot import sendMessage, sendScriptNotif
from get_watchlist import setup_driver, get_symbols, close_driver
from flask import Flask, jsonify, request

#TODO: Run alert update after 30 mins initial one, then 5 mins thereafter

current_directory = os.path.dirname(__file__)
os.chdir(current_directory) 

# Input parameters
std_dev_treshold = 5
max_trade_len = 1500
min_trade_count = 500 # Num of trades required before stats can be calculated and alerts sent
update_symbol_interval = 600 #Interval (in seconds) between each symbol update
update_alerts_interval = 120 #Interval (in seconds) between each alert frequency update

# Dictionary to store trades, with each symbol as the key and deque to hold trade data
trade_data = defaultdict(lambda: deque(maxlen=max_trade_len))
stats = defaultdict(lambda: {"count": 0, "sum_quantity": 0, "sum_quantity_squared": 0, "avg_quantity": 0, "std_d ev": 0})

# Dictionary to store alert frequencies and thresholds
alert_frequency = defaultdict(lambda: deque())
alert_thresholds = defaultdict(lambda: std_dev_treshold)  # Store the current threshold for each symbol
alert_limit_per_minute = 5  # Define limits for alerts per minute
alert_limit_per_hour = 30  # Define limits for alerts per hour

queue = Queue()
my_clients = {}
symbols = []

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
            
            # if alerts_per_minute > alert_limit_per_minute or alerts_per_hour > alert_limit_per_hour:
            
            if alerts_per_hour > alert_limit_per_hour and 0 < time_delta <= 600: # Make sure last alert came through during the alert update interval, else don't increase threshold
                # Increase threshold to reduce alerts
                alert_thresholds[symbol] += 1
            # else:
            #     # Gradually decrease threshold if alerts are infrequent
            #     alert_thresholds[symbol] = max(alert_thresholds[symbol] - 0.1, std_dev_treshold)

            # Send update message
            update_message += f"<b>{symbol}</b>: {alerts_per_minute} / min | {alerts_per_hour} / hour -> ({alert_thresholds[symbol]} s.d.) \n"
        
        # Send messag eif there are alerts
        if update_message != default_message:
            sendMessage(update_message)
            print(">>>>>>> Alert Frequency Sent\n")

        time.sleep(update_alerts_interval)
    
# Start process
print("======= Initializing Large Trade Alerts ========")

# Start thread to update symbols periodically
symbol_update_thread = threading.Thread(target=update_symbols)
symbol_update_thread.start()

# Start thread to process the queue
queue_thread = threading.Thread(target=process_queue)
queue_thread.start()

# Start thread to process the queue
alert_update_thread = threading.Thread(target=update_alerts)
alert_update_thread.start()

# Keep the connection open
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    for symbol in list(my_clients.keys()):
        my_clients[symbol].stop()
    queue.put(None)  # Signal the queue processing thread to exit
    symbol_update_thread.join()
    queue_thread.join()
    alert_update_thread.join()



''' Old code [WORKING]

import os
import time
import json
import threading
from queue import Queue
from collections import defaultdict, deque
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from TelegramBot import sendMessage, sendScriptNotif
from get_watchlist import setup_driver, get_symbols, close_driver

current_directory = os.path.dirname(__file__)
os.chdir(current_directory) 

# Input parameters
std_dev_treshold = 6
max_trade_len = 1000
update_interval = 120 #Interval (in seconds) between each update

# Dictionary to store trades, with each symbol as the key and deque to hold trade data
trade_data = defaultdict(lambda: deque(maxlen=max_trade_len))
stats = defaultdict(lambda: {"count": 0, "sum_quantity": 0, "sum_quantity_squared": 0, "avg_quantity": 0, "std_d ev": 0})

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
if stats[symbol]["count"] > 1:
    avg_quantity = stats[symbol]["sum_quantity"] / stats[symbol]["count"]
    variance = (stats[symbol]["sum_quantity_squared"] / stats[symbol]["count"]) - (avg_quantity ** 2)
    std_dev = variance ** 0.5
    stats[symbol]["avg_quantity"] = avg_quantity
    stats[symbol]["std_dev"] = std_dev

    # Check if the new quantity is greater than X standard deviations from the average
    if quantity > avg_quantity + std_dev_treshold * std_dev:
        alert(symbol, price, quantity, avg_quantity, std_dev)

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

def alert(symbol, price, quantity, avg_quantity, std_dev):
    notional = format_notional(price * quantity)
    tele_message = '<b>[Large Trade] - ' + symbol + ': ' + str(price) + '</b>\n' \
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
        symbol = data['s']
        timestamp = int(data['T'])
        price = float(data['p'])
        quantity = float(data['q'])

        # Insert trade into the dictionary and update statistics
        insert_trade(symbol, timestamp, price, quantity)

def process_update_thread():
    while True:
        update_message = "<b>[Update - Large Trade Alerts]</b>\n"
        for symbol in symbols:
            symbol = symbol.upper()
            trade_count = stats[symbol]["count"]
            update_message += f"{symbol}: {trade_count} trades\n"
        sendMessage(update_message)
        time.sleep(600)  # Sleep for 10 minutes

queue = Queue()
my_clients = {}
symbols = ['tonusdt', 'zecusdt', 'linkusdt']

# Start thread to periodically update ticker info
update_thread = threading.Thread(target=process_update_thread)
update_thread.start()

for symbol in symbols:
    my_clients[symbol] = UMFuturesWebsocketClient(on_message=message_handler, is_combined=True)
    my_clients[symbol].subscribe(stream=f"{symbol}@aggTrade")

# Keep the connection open
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    for symbol in symbols:
        my_clients[symbol].stop()
    for symbol in symbols:
        my_clients[symbol].close()
    queue.put(None)  # Signal the queue processing thread to exit
    symbol_update_thread.join()
    queue_thread.join()
    update_thread.join()

'''