
import telebot
import requests
import json
from telebot import types
import time
from datetime import datetime
import threading
from secret import BOT_TOKEN
BINANCE_API = "https://api.binance.com/api/v3/ticker/price"
KUCOIN_API = "https://api.kucoin.com/api/v1/market/allTickers"
HUOBI_API = "https://api.huobi.pro/market/tickers"
MEXC_API = "https://api.mexc.com/api/v3/ticker/price"


bot = telebot.TeleBot(BOT_TOKEN)

price_cache = {}
last_update = 0
UPDATE_INTERVAL = 60 

def get_binance_prices():
    """Гирифтани нархҳо аз Binance"""
    try:
        response = requests.get(BINANCE_API)
        if response.status_code == 200:
            data = response.json()
            return {item['symbol']: float(item['price']) for item in data}
        return {}
    except Exception as e:
        print(f"Хатогӣ дар Binance API: {e}")
        return {}

def get_kucoin_prices():
    """Гирифтани нархҳо аз KuCoin"""
    try:
        response = requests.get(KUCOIN_API)
        if response.status_code == 200:
            data = response.json().get('data', {}).get('ticker', [])
            prices = {}
            for item in data:
                symbol = item.get('symbol', '').replace('-', '')
                price = item.get('last')  
                if symbol and price:  
                    try:
                        prices[symbol] = float(price)
                    except (ValueError, TypeError):
                        print(f"Хатогӣ дар табдили нархи {symbol}: {price}")
            return prices
        return {}
    except Exception as e:
        print(f"Хатогӣ дар KuCoin API: {e}")
        return {}


def get_huobi_prices():
    """Гирифтани нархҳо аз Huobi"""
    try:
        response = requests.get(HUOBI_API)
        if response.status_code == 200:
            data = response.json()['data']
            return {item['symbol'].upper(): float(item['close']) for item in data}
        return {}
    except Exception as e:
        print(f"Хатогӣ дар Huobi API: {e}")
        return {}

def get_mexc_prices():
    """Гирифтани нархҳо аз MEXC"""
    try:
        response = requests.get(MEXC_API)
        if response.status_code == 200:
            data = response.json()
            return {item['symbol']: float(item['price']) for item in data}
        return {}
    except Exception as e:
        print(f"Хатогӣ дар MEXC API: {e}")
        return {}

def update_prices():
    """Навсозии нархҳо дар кэш"""
    global price_cache, last_update
    current_time = time.time()
    
    if current_time - last_update < UPDATE_INTERVAL:
        return
    
    price_cache = {
        'binance': get_binance_prices(),
        'kucoin': get_kucoin_prices(),
        'huobi': get_huobi_prices(),
        'mexc': get_mexc_prices()
    }
    last_update = current_time

def format_price(price):
    """Форматкунии нарх"""
    if price >= 1000:
        return f"{price:,.2f}"
    elif price >= 1:
        return f"{price:.2f}"
    else:
        return f"{price:.8f}"

def find_arbitrage_opportunities():
    """Ёфтани имкониятҳои арбитраж"""
    opportunities = []
    common_pairs = set()
    
    
    for exchange in price_cache.values():
        common_pairs.update(exchange.keys())
    
    for pair in common_pairs:
        prices = {}
        for exchange, exchange_prices in price_cache.items():
            if pair in exchange_prices:
                prices[exchange] = exchange_prices[pair]
        
        if len(prices) >= 2:
            min_exchange = min(prices.items(), key=lambda x: x[1])
            max_exchange = max(prices.items(), key=lambda x: x[1])
            price_diff = ((max_exchange[1] - min_exchange[1]) / min_exchange[1]) * 100
            
            if price_diff > 1:  
                opportunities.append({
                    'pair': pair,
                    'buy_exchange': min_exchange[0],
                    'buy_price': min_exchange[1],
                    'sell_exchange': max_exchange[0],
                    'sell_price': max_exchange[1],
                    'difference': price_diff
                })
    
    return sorted(opportunities, key=lambda x: x['difference'], reverse=True)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('💰 Нархҳо', '📊 Муқоиса')
    markup.row('💹 Арбитраж', '❓ Ёрдам')
    
    welcome_text = """
Салом! Ман боти муқоисаи нархҳои криптовалюта ҳастам.

Амрҳои дастрас:
/price <symbol> - Нархи як криптовалютаи мушаххас
/compare <symbol> - Муқоисаи нархҳо дар биржаҳои гуногун
/arbitrage - Ёфтани имкониятҳои арбитраж
/top - 10 криптовалютаи беҳтарин

Шумо инчунин метавонед аз тугмаҳои зер истифода баред 👇
    """
    bot.reply_to(message, welcome_text, reply_markup=markup)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
Роҳнамои истифодаи бот:

1. Барои дидани нархи як криптовалюта:
   /price BTC - нархи Bitcoin
   /price ETH - нархи Ethereum

2. Барои муқоисаи нархҳо:
   /compare BTC - муқоисаи нархи Bitcoin дар ҳама биржаҳо
   
3. Барои дидани имкониятҳои арбитраж:
   /arbitrage - нишон додани беҳтарин имкониятҳо

4. Барои дидани TOP-10:
   /top - нишон додани 10 криптовалютаи беҳтарин

Нархҳо ҳар 60 сония нав мешаванд.
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['price'])
def send_price(message):
    try:
        symbol = message.text.split()[1].upper()
        update_prices()
        
        response = "Нархи " + symbol + ":\n\n"
        for exchange, prices in price_cache.items():
            if symbol in prices:
                response += f"{exchange.capitalize()}: ${format_price(prices[symbol])}\n"
        
        if response == f"Нархи {symbol}:\n\n":
            response = f"Бахшиш, барои {symbol} нарх ёфт нашуд."
            
        bot.reply_to(message, response)
    except IndexError:
        bot.reply_to(message, "Лутфан символро ворид кунед. Масалан: /price BTC")

@bot.message_handler(commands=['compare'])
def compare_prices(message):
    try:
        symbol = message.text.split()[1].upper()
        update_prices()
        
        prices = []
        for exchange, exchange_prices in price_cache.items():
            if symbol in exchange_prices:
                prices.append((exchange, exchange_prices[symbol]))
        
        if not prices:
            bot.reply_to(message, f"Бахшиш, барои {symbol} нарх ёфт нашуд.")
            return
            
        prices.sort(key=lambda x: x[1])
        
        response = f"Муқоисаи нархҳо барои {symbol}:\n\n"
        for exchange, price in prices:
            response += f"{exchange.capitalize()}: ${format_price(price)}\n"
        
        min_price = prices[0][1]
        max_price = prices[-1][1]
        diff_percent = ((max_price - min_price) / min_price) * 100
        
        response += f"\nФарқи нарх: {diff_percent:.2f}%"
        
        bot.reply_to(message, response)
    except IndexError:
        bot.reply_to(message, "Лутфан символро ворид кунед. Масалан: /compare BTC")

@bot.message_handler(commands=['arbitrage'])
def show_arbitrage(message):
    update_prices()
    opportunities = find_arbitrage_opportunities()
    
    if not opportunities:
        bot.reply_to(message, "Дар айни ҳол имкониятҳои арбитраж ёфт нашуданд.")
        return
    
    response = "🔄 Имкониятҳои беҳтарини арбитраж:\n\n"
    for opp in opportunities[:5]:
        response += f"💠 {opp['pair']}\n"
        response += f"Харид: {opp['buy_exchange'].capitalize()} - ${format_price(opp['buy_price'])}\n"
        response += f"Фурӯш: {opp['sell_exchange'].capitalize()} - ${format_price(opp['sell_price'])}\n"
        response += f"Фарқ: {opp['difference']:.2f}%\n\n"
    
    bot.reply_to(message, response)

@bot.message_handler(func=lambda message: message.text in ['💰 Нархҳо', '📊 Муқоиса', '💹 Арбитраж', '❓ Ёрдам'])
def handle_buttons(message):
    if message.text == '💰 Нархҳо':
        bot.reply_to(message, "Лутфан амри /price <symbol> -ро истифода баред. Масалан: /price BTC")
    elif message.text == '📊 Муқоиса':
        bot.reply_to(message, "Лутфан амри /compare <symbol> -ро истифода баред. Масалан: /compare BTC")
    elif message.text == '💹 Арбитраж':
        show_arbitrage(message)
    elif message.text == '❓ Ёрдам':
        send_help(message)

def main():
    """Функсияи асосӣ"""
    try:
        print("Бот оғоз шуд...")
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Хатогӣ рӯй дод: {e}")
        time.sleep(15)
        main()

if __name__ == "__main__":
    main()