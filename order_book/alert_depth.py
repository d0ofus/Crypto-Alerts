import os
import time
import requests
from threading import Thread
from collections import defaultdict
from flask import Flask, jsonify, request
from TelegramBot import sendMessage
from get_watchlist import setup_driver, get_symbols, close_driver

current_directory = os.path.dirname(__file__)
os.chdir(current_directory)

#TODO: Alert if above X s.d. of normal size + within 2%
#TODO: Grab symbols from watchlist
#TODO: Make this function callable through the flask app on koyeb for any given ticker
#TODO: Combine into one alert message

app = Flask(__name__)

symbols = ['ETHUSDT', 'TAOUSDT']
alerts_active = False
max_levels = defaultdict(list)
CHECK_INTERVAL = 30 
THRESHOLD_DIFF = 0.03 # In % terms
VALID_DEPTH_LIMITS = [5, 10, 20, 50, 100, 500, 1000]

def fetch_order_book(symbol, limit=1000):
    url = f'https://fapi.binance.com/fapi/v1/depth?symbol={symbol}&limit={limit}'
    response = requests.get(url)
    data = response.json()
    return data

def find_max_liquidity_level(order_book):
    max_bid = {'price': None, 'quantity': 0}
    max_ask = {'price': None, 'quantity': 0}

    # Find the maximum quantity level on the bid side
    for bid in order_book['bids']:
        price = float(bid[0])
        quantity = float(bid[1])
        if quantity > max_bid['quantity']:
            max_bid = {'price': price, 'quantity': quantity}

    # Find the maximum quantity level on the ask side
    for ask in order_book['asks']:
        price = float(ask[0])
        quantity = float(ask[1])
        if quantity > max_ask['quantity']:
            max_ask = {'price': price, 'quantity': quantity}
    return max_bid, max_ask

def find_bbo(order_book):
    best_bid = {'price': float(order_book['bids'][0][0]), 
               'quantity': float(order_book['bids'][0][1])}
    best_ask = {'price': float(order_book['asks'][0][0]), 
               'quantity': float(order_book['asks'][0][1])}
    mid_px = (best_bid['price'] + best_ask['price'])/2

    #TODO: Make mid_px round to the nearest decimal of what it is meant to be

    return best_bid, best_ask, mid_px

def calc_pct(best_bid, best_ask, max_bid, max_ask):
    bid_diff = best_bid['price']/max_bid['price'] - 1
    ask_diff = max_ask['price']/best_ask['price'] - 1
    return bid_diff, ask_diff

def format_pct(value):
    formatted_value = "{:.1%}".format(value)
    print(formatted_value)
    return formatted_value

def format_notional(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return str(value)

def send_message(symbol, mid_px, max_bid, max_ask, bid_diff, ask_diff):
    max_ask_notional = format_notional(max_ask['price'] * max_ask['quantity'])
    max_bid_notional = format_notional(max_bid['price'] * max_bid['quantity'])
    tele_message = '<b>[Max Depth] - ' + symbol + ': ' + str(mid_px) + '</b> \n' \
                    + 'Max Ask ('+ format_pct(ask_diff)+ '): ' + str(max_ask['price']) + ' | ' + str(max_ask['quantity']) + ' = ' + max_ask_notional + '\n' \
                    + 'Max bid ('+ format_pct(bid_diff)+ '): ' + str(max_bid['price']) + ' | ' + str(max_bid['quantity']) + ' = ' + max_bid_notional + '\n' 

    sendMessage(tele_message)

def analyze_and_alert(symbol):
    best_diff = {'bid': None, 'ask': None}
    best_max = {'bid': None, 'ask': None}
    for i in range(len(VALID_DEPTH_LIMITS)):
        print(best_diff['bid'], best_diff['ask'])
        if best_diff['bid'] and best_diff['ask']:
            break  # Exit the loop if both differences are within the threshold

        limit = sorted(VALID_DEPTH_LIMITS, reverse=True)[i]
        print(f"{symbol}: {limit}")
        order_book = fetch_order_book(symbol, limit)
        max_bid, max_ask = find_max_liquidity_level(order_book)
        best_bid, best_ask, mid_px = find_bbo(order_book)
        bid_diff, ask_diff = calc_pct(best_bid, best_ask, max_bid, max_ask)
        
        if bid_diff <= THRESHOLD_DIFF and best_diff['bid']==None:
            best_diff['bid'] = bid_diff
            best_max['bid'] = max_bid

        if ask_diff <= THRESHOLD_DIFF and best_diff['ask']==None:
            best_diff['ask'] = ask_diff
            best_max['ask'] = max_ask
        
    max_levels[symbol] = (best_max['bid'], best_max['ask'])  # Append the tuple of max_bid and max_ask
    send_message(symbol, mid_px, best_max['bid'], best_max['ask'], best_diff['bid'], best_diff['ask'])

def run_alerts():
    global symbols
    while alerts_active:
        for symbol in symbols:
            analyze_and_alert(symbol)
        time.sleep(CHECK_INTERVAL)


'''
Flask web app routes
'''
@app.route('/start')
def start_alerts():
    global alerts_active
    if alerts_active == False:
        alerts_active = True
    else:
        return
    thread = Thread(target=run_alerts)
    thread.start()
    return jsonify({"message": "Large book depth alerts started"}), 200

@app.route('/stop')
def stop_alerts():
    global alerts_active, max_levels
    alerts_active = False
    max_levels.clear()
    return jsonify({"message": "Large book depth alerts stopped"}), 200

@app.route('/')
def index():
    return "Large Book Depth Alert Service up and running!"

## Individual symbol
# @app.route('/symbol', methods=['GET'])
# def get_symbol(symbol):
#     analyze_and_alert(symbol)
#     return jsonify({"Symbol": "Generating max depth."})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
    
# if __name__ == "__main__":
#     symbols = ['APTUSDT', 'SOLUSDT', 'ASTRUSDT']
#     main()

# #%% Testing
# symbol = 'SOLUSDT'
# analyze_and_alert(symbol)

# order_book = fetch_order_book(symbol, 1000)
# if 'code' in order_book: # Check if depth limit available
#     print(order_book['msg'])
# max_bid, max_ask = find_max_liquidity_level(order_book)
# best_bid, best_ask, mid_px = find_bbo(order_book)
# bid_diff, ask_diff = calc_pct(best_bid, best_ask, max_bid, max_ask)
# print(max_bid, max_ask)
# print(bid_diff, ask_diff)

