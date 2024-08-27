import requests
import time
from collections import defaultdict, deque

#TODO: Stream current prices and alert if price is X% from big level
#TODO: If price of big levels too far (X%) away from current price, reduce depth limit 

# Telegram bot configuration
BOT_TOKEN = 'your-telegram-bot-token'
CHAT_ID = 'your-telegram-chat-id'

# Binance API configuration
symbols = ['TAOUSDT', 'RENDERUSDT']
max_levels = defaultdict(list)
DEPTH_LIMIT = 1000
CHECK_INTERVAL = 60  # Fetch the order book every 60 seconds
# LIQUIDITY_THRESHOLD = 100  # Example threshold for large liquidity

def fetch_order_book(symbol, limit):
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

def analyze_and_alert(symbol):
    order_book = fetch_order_book(symbol, DEPTH_LIMIT)
    max_bid, max_ask = find_max_liquidity_level(order_book)

    max_levels[symbol]=(max_bid, max_ask)  # Append the tuple of max_bid and max_ask

    # alert_messages = []

    # # Check if max bid quantity exceeds the threshold
    # if max_bid['quantity'] >= LIQUIDITY_THRESHOLD:
    #     alert_messages.append(f"[{symbol}] High liquidity on bid side: ${max_bid['price']} with {max_bid['quantity']} contracts.")

    # # Check if max ask quantity exceeds the threshold
    # if max_ask['quantity'] >= LIQUIDITY_THRESHOLD:
    #     alert_messages.append(f"[{symbol}] High liquidity on ask side: ${max_ask['price']} with {max_ask['quantity']} contracts.")

    # # Send alerts if any
    # for message in alert_messages:
    #     send_telegram_message(message)
    

def main():
    while True:
        for symbol in symbols:
            analyze_and_alert(symbol)
        print(max_levels)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
