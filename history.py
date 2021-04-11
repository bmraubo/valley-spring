import csv

def history_setup():
    with open('trade_history.csv', mode='a') as history_file:
        fieldnames = ['ID','Time','Type','Symbol','Price','Quantity','Value','Commission']
        writer = csv.DictWriter(history_file,fieldnames=fieldnames)
        writer.writeheader()

history_setup()