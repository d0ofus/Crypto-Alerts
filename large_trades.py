import os
import logging
import time
import json
import sqlite3
import threading
from queue import Queue
from collections import defaultdict
from binance.lib.utils import config_logging
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient

current_directory = os.path.dirname(__file__)
os.chdir(current_directory)

config_logging(logging, logging.DEBUG)

# Define variables
sd_multiple = 4

# Function to create a new connection for each thread
def get_db_connection():
    return sqlite3.connect('stream_data/aggTrades.db', check_same_thread=False)

# Create table for each symbol
def create_data_table(cursor, symbol):
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {symbol} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER,
        price REAL,
        quantity REAL
    )
    """)

# Delete old entries for each symbol
def delete_old_entries(cursor):
    symbols = ['btcusdt', 'ethusdt']
    for symbol in symbols:
        cursor.execute(f"DELETE FROM {symbol}")
    
    # Clear all entries from the stats table
    cursor.execute("DELETE FROM stats")

    conn.commit()

# Insert trade data into the table
def insert_trade(cursor, symbol, timestamp, price, quantity):
    cursor.execute(f"""
    INSERT INTO {symbol} (timestamp, price, quantity) VALUES (?, ?, ?)
    """, (timestamp, price, quantity))
    
    # cursor.execute(f"""
    # INSERT INTO stats (symbol, count, sum_quantity, sum_quantity_squared)
    # VALUES (?, 1, ?, ?)
    # ON CONFLICT(symbol) DO UPDATE SET
    #     count = count + 1,
    #     sum_quantity = sum_quantity + ?,
    #     sum_quantity_squared = sum_quantity_squared + ?
    # """, (symbol, quantity, quantity**2, quantity, quantity**2))

    cursor.execute(f"""
    DELETE FROM {symbol} WHERE id NOT IN (
        SELECT id FROM {symbol} ORDER BY timestamp DESC LIMIT 1000
    )
    """)


'''
Alert functions
'''
alerts_history = defaultdict(list)

# Alert function
def alert(symbol, quantity, avg_quantity, std_dev):
    timestamp = time.time()
    alerts_history[symbol].append(timestamp)
    logging.info(f"ALERT: {symbol} trade quantity {quantity} is greater than {sd_multiple} standard deviations from the average {avg_quantity} with a standard deviation of {std_dev}")


def calculate_average_alerts(symbol, timeframe='minute'):
    now = time.time()
    if timeframe == 'minute':
        start_time = now - 60
    elif timeframe == 'hour':
        start_time = now - 3600
    elif timeframe == 'day':
        start_time = now - 86400
    else:
        raise ValueError("Invalid timeframe. Choose from 'minute', 'hour', or 'day'.")

    relevant_alerts = [alert_time for alert_time in alerts_history[symbol] if alert_time >= start_time]
    count = len(relevant_alerts)
    
    return count

def get_alert_stats(symbol):
    avg_minute = calculate_average_alerts(symbol, timeframe='minute')
    avg_hour = calculate_average_alerts(symbol, timeframe='hour')
    avg_day = calculate_average_alerts(symbol, timeframe='day')
    logging.info(f"AVERAGE ALERTS for {symbol}: {avg_minute}/min, {avg_hour}/hour, {avg_day}/day")

def alert_stats_thread():
    while True:
        # Periodically update the running stats for each symbol
        for symbol in symbols:
            get_alert_stats(symbol)
            print(len(alerts_history[symbol]))
 
        time.sleep(60)



'''
Calculation functions
'''
# Maintain running stats
stats = defaultdict(lambda: {"count": 0, "sum_quantity": 0, "sum_quantity_squared": 0, "avg_quantity": 0, "std_dev": 0})

def get_recent_trades(cursor, symbol):
    cursor.execute(f"""
    SELECT quantity FROM {symbol} ORDER BY timestamp DESC LIMIT 1000
    """)
    return cursor.fetchall()

def update_running_stats(symbol, cursor):
    symbol = symbol.upper()
    trades = get_recent_trades(cursor, symbol)

    if trades:
        count = len(trades)
        sum_quantity = sum(trade[0] for trade in trades)
        sum_quantity_squared = sum(trade[0] ** 2 for trade in trades)

        if count > 1:
            avg_quantity = sum_quantity / count
            variance = (sum_quantity_squared / count) - (avg_quantity ** 2)
            std_dev = variance ** 0.5
            stats[symbol] = {"count": count, "sum_quantity": sum_quantity, "sum_quantity_squared": sum_quantity_squared, "avg_quantity": avg_quantity, "std_dev": std_dev}
        else:
            print(f"Not enough data to calculate stats for {symbol}: count = {count}")

        print(f"Stats for {symbol}: {stats[symbol]}")
    else:
        print(f"No trades found for symbol: {symbol}")

    # cursor.execute(f"""
    # SELECT count, sum_quantity, sum_quantity_squared FROM stats WHERE symbol = ?
    # """, (symbol,))
    # row = cursor.fetchone()
    
    # # Check if row is None
    # if row is None:
    #     print(f"No data found for symbol: {symbol}")
    # else:
    #     count, sum_quantity, sum_quantity_squared = row
    #     print(f"Data for {symbol}: count={count}, sum_quantity={sum_quantity}, sum_quantity_squared={sum_quantity_squared}")

    #     # Check if count is greater than 1
    #     if count > 1:
    #         avg_quantity = sum_quantity / count
    #         variance = (sum_quantity_squared / count) - (avg_quantity ** 2)
    #         std_dev = variance ** 0.5
    #         stats[symbol] = {"count": count, "sum_quantity": sum_quantity, "sum_quantity_squared": sum_quantity_squared, "avg_quantity": avg_quantity, "std_dev": std_dev}
    #     else:
    #         print(f"Not enough data to calculate stats for {symbol}: count = {count}")
    
    # print(f"Stats for {symbol}: {stats[symbol]}")

def update_stats_thread():
    while True:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Periodically update the running stats for each symbol
            for symbol in symbols:
                update_running_stats(symbol, cursor)
        finally:
            conn.close()
        time.sleep(10)


'''
Websocket functions
'''
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Ensure table exists for each symbol
            create_data_table(cursor, symbol)
            # create_stats_table(cursor)
            
            # Insert data into the table
            insert_trade(cursor, symbol, timestamp, price, quantity)
            
            # Check if the new quantity is greater than 2 standard deviations from the average
            avg_quantity = stats[symbol]['avg_quantity']
            std_dev = stats[symbol]['std_dev']
            if avg_quantity and std_dev:
                if quantity > avg_quantity + sd_multiple * std_dev:
                    alert(symbol, quantity, avg_quantity, std_dev)
        finally:
            conn.commit()
            conn.close()

# def create_stats_table(cursor):
#     cursor.execute(f"""
#     CREATE TABLE IF NOT EXISTS stats (
#         symbol TEXT PRIMARY KEY,
#         count INTEGER,
#         sum_quantity REAL,
#         sum_quantity_squared REAL
#     )
#     """)
#     conn.commit()


'''
Script Initialization
'''
queue = Queue()
my_clients = {}
symbols = ['btcusdt', 'ethusdt']

# Delete old entries before starting the stream
conn = get_db_connection()
cursor = conn.cursor()
try:
    delete_old_entries(cursor)
    # create_stats_table(cursor)
except:
    pass
# finally:
#     conn.close()
# Start threads to process the queue and update stats
queue_thread = threading.Thread(target=process_queue)
queue_thread.start()

stats_thread = threading.Thread(target=update_stats_thread)
stats_thread.start()

alerts_thread = threading.Thread(target=alert_stats_thread)
alerts_thread.start()

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
    queue_thread.join()
    stats_thread.join()
    alerts_thread.join()
    conn.close()

