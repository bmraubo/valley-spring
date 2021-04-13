import websocket, json, talib, numpy, config, logging, datetime, csv
from binance.client import Client
from binance.enums import *

test_mode = True

closes = []
starting_portfolio = 30
trade_symbol = 'ETHGBP'
trade_amount = 0

kline_interval = '2h'
klines_per_day = 24/2
rsi_period = 10
rsi_overbought = 75
rsi_oversold = 25

asset_balance = 0
in_position = False
transaction_history = {}

client = Client(config.API_KEY, config.API_SECRET)
socket_open = False

socket = 'wss://stream.binance.com:9443/ws/ethgbp@kline_2h'
comms = 0

#test mode

def test_mode_check():
    if test_mode == True:
        print('TEST MODE ACTIVE')
        logging.info('TEST MODE ACTIVE')
    else:
        print('LIVE TRADING!')
        logging.info('LIVE TRADING!')


def test_switch():
    valid_input = 0
    while valid_input == 0:
        test_input = input('Would you like to run test mode? (y/n): ')
        if test_input.upper() == 'Y':
            print('TEST MODE ACTIVE')
            logging.info('TEST MODE ACTIVE')
            valid_input = 1
            return True
        elif test_input.upper() == 'N':
            print('LIVE TRADING!')
            logging.info('LIVE TRADING!')
            valid_input = 1
            return False
        else:
            print('Invalid Input, please try again...')

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

#Transaction History

def history(order):
    #takes order RESPONSE JSON from binance, logs it and stores it in a CSV file
    #updating dictionary
    order_id = order["orderId"]
    order_time = datetime.datetime.utcfromtimestamp(order["transactTime"] / 1000.0)
    order_type = order["side"]
    order_symbol = order["symbol"]
    order_price = order["price"]
    order_qty = order["executedQty"]
    order_value = float(order_price)*float(order_qty)
    order_commission = order_value*0.001
    transaction_history[order_id] = {'ID':order_id, 'Time':order_time, 'Type':order_type,'Symbol':order_symbol,'Price':order_price,'Quantity':order_qty,'Value':order_value,'Commission':order_commission}
    #appending to CSV file
    with open('trade_history.csv', mode='a') as history_file:
        fieldnames = ['ID','Time','Type','Symbol','Price','Quantity','Value','Commission']
        writer = csv.DictWriter(history_file,fieldnames=fieldnames)
        writer.writerow(transaction_history[order_id])
    #log history update
    logging.info('Order added to Trade History')        

#position status

def balance():
    assets = client.get_asset_balance('ETH')
    logging.info(f'Assets check: {assets["free"]}')
    return assets['free']
    
def position(asset_balance):
    if float(asset_balance) < ((starting_portfolio/closes[-1])/2):
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
    logging.info('Creating Order...')
    try:
        order = client.create_order(symbol = symbol,
                    side = side,
                    type = order_type,
                    quantity = quantity)
        print(f'Order created!\nSymbol: {order["symbol"]}\nOrder Type: {order["side"]}\nOrder ID: {order["orderId"]}\nPrice: {order["price"]}\nQuantity: {order["executedQty"]}\nStatus: {order["status"]}')
        logging.info(f'Order created!\nSymbol: {order["symbol"]}\nOrder Type: {order["side"]}\nOrder ID: {order["orderId"]}\nPrice: {order["price"]}\nQuantity: {order["executedQty"]}\nStatus: {order["status"]}')
        #add order to transaction history
        try:
            history(order)
        except:
            logging.error('Exception in history function')
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
    global trade_amount
    #check asset balance
    asset_balance = balance()
    print(f'Asset Balance: {asset_balance}')
    
    in_position = position(asset_balance)
    print(f'In Position: {in_position}')
    
    #check RSI status
    if (last_rsi < rsi_oversold) and in_position == False:
        print(f'BUY conditions met\nRSI: {last_rsi} < Threshold: {rsi_oversold}')
        logging.info(f'BUY conditions met\nRSI: {last_rsi} < Threshold: {rsi_oversold}')
        #BUY ORDER ISSUED
        #adjust trade amount
        trade_amount = trade_calc()
        if test_mode == True:
            order_succeeded = test_order(trade_symbol, trade_amount, 'buy')
        else:
            order_succeeded = order(trade_symbol, trade_amount, 'buy')
        if order_succeeded:
            print('Order Succeeded')
            logging.info('Order Succeeded')
            in_position = True
            print(in_position)
    elif last_rsi > rsi_overbought and in_position == True:
        print(f'SELL conditions met\nRSI: {last_rsi} > Threshold: {rsi_overbought}')
        logging.info(f'SELL conditions met\nRSI: {last_rsi} > Threshold: {rsi_overbought}')
        #SELL ORDER ISSUED
        if test_mode == 1:
            order_succeeded = test_order(trade_symbol, trade_amount, 'sell')
        else:
            order_succeeded = order(trade_symbol, trade_amount, 'sell')
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
    global socket_open
    socket_open = True
    print(f'Websocket open for {trade_symbol} with {kline_interval} kline interval')
    logging.info(f'Websocket open for {trade_symbol} with {kline_interval} kline interval')

def on_close(ws):
    global socket_open
    global comms
    comms = 0 
    socket_open = False
    print(f'\nWebsocket closed for {trade_symbol} with {kline_interval} kline interval')
    logging.info(f'Websocket closed for {trade_symbol} with {kline_interval} kline interval\n')

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
    elif comms == 106:
        print('recieving messages...')
        logging.info('recieving messages...')
        comms = 6
    else:
        pass

    #When the candle closes, run analysis and algorithm

    if is_candle_closed == True:
        print('candle closed - running analysis')
        logging.info('candle closed - running analysis')
        closes.append(float(close))
        last_rsi = rsi_calc()
        print(f'RSI at last candle closed: {last_rsi}')
        valley_spring(last_rsi)

#start up

def start_up():
    print('\n##########################################################\n\nStarting up...')
    logging.info('\n##########################################################\n\nStarting up...')
    global asset_balance
    global in_position
    global trade_amount
    #check test mode
    test_mode_check()
    #prepare historical data
    get_historical_data()
    #log, balance, position
    asset_balance = balance()
    position(asset_balance)
    
    last_rsi = rsi_calc()
    print(f'Last RSI: {last_rsi}')
    #run algo first time
    print('Startup completed. Running algorithm')
    logging.info('Startup completed. Running algorithm...')
    valley_spring(last_rsi)        

#Process

if __name__ == '__main__':
    start_up()
    while socket_open == False:
        try:
            ws = websocket.WebSocketApp(socket, on_open=on_open, on_close=on_close, on_message=on_message)
            ws.run_forever()
        except:
            print('Socket Connection Error')
            logging.error('Socket Connection Error')