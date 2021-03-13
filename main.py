import websocket, json, talib, numpy, config
from binance.client import Client
from binance.enums import *

closes = []
trade_amount = 0.02
trade_symbol = 'ETHGBP'

kline_interval = '4h'
klines_per_day = 24/4
rsi_period = 7
rsi_overbought = 70
rsi_oversold = 30

asset_balance = 0
in_position = False

client = Client(config.API_KEY, config.API_SECRET)

socket = 'wss://stream.binance.com:9443/ws/ethgbp@kline_4h'

#get historical data

def get_historical_data():
    global closes
    historic_klines = client.get_historical_klines('ETHGBP', Client.KLINE_INTERVAL_4HOUR, "10 days ago UTC")
    for kline in historic_klines:
        closes.append(float(kline[4]))
    if len(closes) >= 10*klines_per_day:
        print('Historical Data Added Successfully...')
    else:
        print(f'Historical Data Incomplete...\nCurrent len(closes): {len(closes)} - Should be {10*klines_per_day}')

#position status

def balance():
    assets = client.get_asset_balance('ETH')
    return assets['free']
    
def position(asset_balance):
    if float(asset_balance) < (trade_amount/2):
        return False
    else:
        return True
    
#order logic

def order(symbol, quantity, side, order_type=ORDER_TYPE_MARKET):
    print('Creating Order...')
    try:
        order = client.create_order(symbol = symbol,
                    side = side,
                    type = order_type,
                    quantity = quantity)
        print(f'Order created!\n\n{order}')
        return True
    except:
        print('Order exception!')
        return False

def test_order(symbol, quantity, side, order_type=ORDER_TYPE_MARKET):
    print('Creating TEST order....')
    try:
        order = client.create_test_order(symbol= symbol,
                side= side,
                type= order_type,
                quantity= quantity)
        print(f'Order created!\n\n{order}')
    except:
        print('Order exception!')
        return False

#technical analysis

def rsi_calc():
    if len(closes) > rsi_period:
        np_closes = numpy.array(closes)
        rsi = talib.RSI(np_closes, rsi_period)
        return rsi[-1]

#algo logic

def valley_spring(last_rsi):
    global in_position
    #check asset balance
    asset_balance = balance()
    print(f'Asset Balance: {asset_balance}')
    in_position = position(asset_balance)
    print(f'In Position: {in_position}')
    #check RSI status
    if (last_rsi < rsi_oversold) and in_position == False:
        print(f'BUY conditions met\nRSI: {last_rsi} < Threshold: {rsi_oversold}')
        #BUY ORDER ISSUED
        order_succeeded = test_order(trade_symbol, trade_amount, 'buy')
        if order_succeeded:
            print('Order Succeeded')
            in_position = True
            print(in_position)
    elif last_rsi > rsi_overbought and in_position == True:
        print(f'SELL conditions met\nRSI: {last_rsi} > Threshold: {rsi_overbought}')
        #SELL ORDER ISSUED
        order_succeeded = test_order(trade_symbol, trade_amount, 'sell')
        if order_succeeded:
            print('Order Succeeded')
            in_position = False
            print(in_position)

#socket processing functions

def on_open(ws):
    print(f'Websocket open for {trade_symbol} with {kline_interval} kline interval')

def on_close(ws):
    print(f'\nWebsocket closed for {trade_symbol} with {kline_interval} kline interval')

def on_message(ws, message):
    global closes
    global in_position
    print('Message received')

    json_message = json.loads(message)

    candle = json_message['k']

    is_candle_closed = candle['x']

    close = candle['c']

    if is_candle_closed:
        print('candle closed - running analysis')
        closes.append(close)
        last_rsi = rsi_calc()
        print(f'RSI at last candle closed: {last_rsi}')
        valley_spring(last_rsi)

#start up

def start_up():
    global asset_balance
    global in_position
    #prepare historical data
    get_historical_data()
    last_rsi = rsi_calc()
    print(f'Last RSI: {last_rsi}')
    #run algo first time
    valley_spring(last_rsi)

#Process

if __name__ == '__main__':
    start_up()
    ws = websocket.WebSocketApp(socket, on_open=on_open, on_close=on_close, on_message=on_message)
    ws.run_forever()