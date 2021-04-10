import websocket, json, talib, numpy, config, logging
from binance.client import Client
from binance.enums import *

closes = []
starting_portfolio = 100
trade_symbol = 'ETHGBP'

kline_interval = '2h'
klines_per_day = 24/2
rsi_period = 10
rsi_overbought = 75
rsi_oversold = 25

asset_balance = 0
in_position = False

client = Client(config.API_KEY, config.API_SECRET)

socket = 'wss://stream.binance.com:9443/ws/ethgbp@kline_2h'
comms = 0

#logging functions

logging.basicConfig(filename='app.log', filemode='a',level=logging.INFO, format='%(asctime)s - %(process)d  - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    

#get historical data

def get_historical_data():
    global closes
    historic_klines = client.get_historical_klines('ETHGBP', Client.KLINE_INTERVAL_2HOUR, "10 days ago UTC")
    for kline in historic_klines:
        closes.append(float(kline[4]))
    if len(closes) >= 10*klines_per_day:
        print('Historical Data Added Successfully...')
        logging.info('Historical Data Added Successfully...')
    else:
        print(f'Historical Data Incomplete...\nCurrent len(closes): {len(closes)} - Should be {10*klines_per_day}')

#position status

def balance():
    assets = client.get_asset_balance('ETH')
    logging.info(f'Assets check: {assets["free"]}')
    return assets['free']
    
def position(asset_balance,trade_amount):
    if float(asset_balance) < (trade_amount/2):
        logging.info('Not in Position')
        return False
    else:
        logging.info('In position')
        return True

#calculate trade amount

def trade_calc():
    trade_amount = (starting_portfolio*0.9)/closes[-1]
    logging.info(f'Trade Amount set to {trade_amount}')
    return trade_amount
    
#order logic

def order(symbol, quantity, side, order_type=ORDER_TYPE_MARKET):
    print('Creating Order...')
    try:
        order = client.create_order(symbol = symbol,
                    side = side,
                    type = order_type,
                    quantity = quantity)
        print(f'Order created!\n\n{order}')
        logging.info(f'Order created!\n\n{order}')
        return True
    except:
        print('Order exception!')
        logging.error('Order exception!')
        return False

def test_order(symbol, quantity, side, order_type=ORDER_TYPE_MARKET):
    print('Creating TEST order....')
    try:
        order = client.create_test_order(symbol= symbol,
                side= side,
                type= order_type,
                quantity= quantity)
        print(f'TEST Order created!\n\n{order}')
        logging.info(f'TEST Order created!\n\n{order}')
    except:
        print('TEST Order exception!')
        logging.error('TEST Order exception!')
        return False

#technical analysis

def rsi_calc():
    if len(closes) > rsi_period:
        np_closes = numpy.array(closes)
        rsi = talib.RSI(np_closes, rsi_period)
        logging.info(f'RSI calculated at {rsi[-1]}')
        return rsi[-1]

#algo logic

def valley_spring(last_rsi):
    global in_position
    #check asset balance
    asset_balance = balance()
    print(f'Asset Balance: {asset_balance}')
    #adjust trade amount
    trade_amount = trade_calc()
    in_position = position(asset_balance, trade_amount)
    print(f'In Position: {in_position}')
    
    #check RSI status
    if (last_rsi < rsi_oversold) and in_position == False:
        print(f'BUY conditions met\nRSI: {last_rsi} < Threshold: {rsi_oversold}')
        #BUY ORDER ISSUED
        order_succeeded = test_order(trade_symbol, trade_amount, 'buy')
        if order_succeeded:
            print('Order Succeeded')
            logging.info('Order Succeeded')
            in_position = True
            print(in_position)
    elif last_rsi > rsi_overbought and in_position == True:
        print(f'SELL conditions met\nRSI: {last_rsi} > Threshold: {rsi_overbought}')
        #SELL ORDER ISSUED
        order_succeeded = test_order(trade_symbol, trade_amount, 'sell')
        if order_succeeded:
            print('Order Succeeded')
            logging.info('Order Succeeded')
            in_position = False
            print(in_position)
    else:
        print('Conditions not met. Listening...')
        logging.info('Conditions not met. Listening...')
    logging.info('Valley Spring has run successfully')
    print('Valley Spring has run successfully')

#socket processing functions

def on_open(ws):
    print(f'Websocket open for {trade_symbol} with {kline_interval} kline interval')
    logging.info(f'Websocket open for {trade_symbol} with {kline_interval} kline interval')

def on_close(ws):
    print(f'\nWebsocket closed for {trade_symbol} with {kline_interval} kline interval')
    logging.info(f'Websocket closed for {trade_symbol} with {kline_interval} kline interval\n\n##########################################################\n')

def on_message(ws, message):
    global closes
    global in_position

    json_message = json.loads(message)

    candle = json_message['k']

    is_candle_closed = candle['x']
    
    close = candle['c']

    #trying to tone down the amount of message received spam
    global comms
    comms += 1
    if comms == 1:
        print('recieving messages...')
        logging.info('recieving messages...')
    elif comms == 56:
        print('recieving messages...')
        logging.info('recieving messages...')
        comms = 6
    else:
        pass

    if is_candle_closed == True:
        print('candle closed - running analysis')
        logging.info('candle closed - running analysis')
        closes.append(float(close))
        last_rsi = rsi_calc()
        print(f'RSI at last candle closed: {last_rsi}')
        valley_spring(last_rsi)

#start up

def start_up():
    print('Starting up...')
    logging.info('Starting up...')
    global asset_balance
    global in_position
    #prepare historical data
    get_historical_data()
    #log, balance, position
    asset_balance = balance()
    trade_amount = trade_calc()
    position(asset_balance, trade_amount)
    
    last_rsi = rsi_calc()
    print(f'Last RSI: {last_rsi}')
    #run algo first time
    print('Startup completed. Running algorithm')
    logging.info('Startup completed. Running algorithm...')
    valley_spring(last_rsi)
        

#Process

if __name__ == '__main__':
    start_up()
    ws = websocket.WebSocketApp(socket, on_open=on_open, on_close=on_close, on_message=on_message)
    ws.run_forever()