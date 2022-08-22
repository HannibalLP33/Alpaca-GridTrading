### DEPENDENCIES ###
import alpaca_trade_api as api
import numpy as np 
import pandas as pd
import time
import warnings
import threading
import math
import config
warnings.filterwarnings('ignore')

class GridBot:
    def __init__(self):
        self.alpaca = api.REST(config.ALPACA_KEY, config.ALPACA_SECRET_KEY, config.ALPACA_URL, "v2")
        
        self.ticker = "TQQQ"
        self.gridWidth = 0.10
        self.gridLevels = 10
        self.gridSpread = self.gridWidth * self.gridLevels
        self.positionSize = 100
        self.openLevels = []
        
    def run(self):
        print("------------------")
        print("CHECKING IF THE MARKET IT OPEN")
        marketOpenThread = threading.Thread(target=self.isMarketOpen)
        marketOpenThread.start()
        marketOpenThread.join()
        print("---MARKET IS NOW OPEN---")
        
        primeQuoteThread = threading.Thread(target=self.primeQuoteStream)
        primeQuoteThread.start()
        primeQuoteThread.join()
        
        
        establishGridThread = threading.Thread(target=self.establishGrid)
        establishGridThread.start()
        establishGridThread.join()
        print("---GRID ESTABLISHED---")
        
        MARKET_OPEN = True
        while MARKET_OPEN == True:
            time.sleep(10*60)
            currentTime = self.alpaca.get_clock().timestamp.timestamp()
            closingTime = self.alpaca.get_clock().next_close.timestamp()
            timeLeft = currentTime - closingTime
            if abs(timeLeft) > (10*60):
                redoGridThread = threading.Thread(target = self.redoGrid)
                redoGridThread.start()
                redoGridThread.join()
                print(f"---GRID REDO OCCURED AT {currentTime}---")
            elif abs(timeLeft) < (15*60):
                try:
                    print("---ATTEMPTING TO CANCEL ALL ORDERS---")
                    self.alpaca.cancel_all_orders()
                    print("---ORDER CANCELLATION SUCCESS---")
                except Exception as e:
                    print(f"---ORDER CANCEL ATTEMPT FAILED DUE TO: {e}---")
                try:
                    print("---ATTEMPTING TO CLOSE ALL POSITIONS---")
                    self.alpaca.close_all_positions()
                    print("---POSITION CANCELLATION SUCCESS---")
                    MARKET_OPEN = False
                except Exception as e:
                    print(f"---POSITION CANCEL ATTEMPT FAILED DUE TO: {e}---")
        
    
    def isMarketOpen(self):
        isOpen = self.alpaca.get_clock().is_open
        while(not isOpen):
            nextOpenTime = self.alpaca.get_clock().next_open.timestamp()
            currentTime = self.alpaca.get_clock().timestamp.timestamp()
            difference = (int(nextOpenTime) - int(currentTime))/60
            print(f"---{difference} MINUTES UNTIL THE NEXT MARKET OPEN---")
            print(f"---SLEEPING FOR {difference} MINUTES---")
            time.sleep((difference+15)*60)
            isOpen = self.alpaca.get_clock().is_open
            
    def submitOrder(self,ticker, quantity, side, limitPrice):
        try:
            self.alpaca.submit_order(ticker, quantity, side, "limit", "gtc", limitPrice, order_class = "oto", take_profit = {"limit_price" : round((float(limitPrice) + 0.10),2)})
            print(f"---LIMIT ORDER FOR {ticker} FOR {quantity} SHARES @ {limitPrice} SUBMITTED---")
        except Exception as e:
            print(e)
            print(f"---LIMIT ORDER FOR {ticker} FOR {quantity} SHARES @ {limitPrice} NOT SUBMITTED---")

    
    def establishGrid(self):
        quoteList = []
        for i in range(10):
            aQuote = self.alpaca.get_latest_quote(self.ticker).ap 
            quoteList.append(aQuote)
            time.sleep(1)   
        quote = min(quoteList)
        print(f"---Current Quote: {quote}---")
        low_end = float(math.floor(quote*10)/10) - self.gridSpread
        high_end = float(math.floor(quote*10)/10) + 0.01
        for price in np.arange(low_end,high_end,self.gridWidth, dtype=float).round(2):
            submitOrderThread = threading.Thread(target = self.submitOrder, args=[self.ticker, self.positionSize, "buy", price])
            submitOrderThread.start()
            submitOrderThread.join()
            self.openLevels.append(price)
    
    def redoGrid(self):
        buyOrders = self.alpaca.list_orders(side="buy", status="open")
        for buyOrder in buyOrders:
            print(f"---CANCELING {buyOrder.id} TO RE-ESTABLISH GRID---")
            self.alpaca.cancel_order(buyOrder.id)

            
        reestablishGridThread = threading.Thread(target=self.establishGrid)
        reestablishGridThread.start()
        reestablishGridThread.join()
        
    ###Occasionally the quote that comes in isn't the true quote at that moment so a priming function was made###
    def primeQuoteStream(self):
        quoteList = []
        for i in range(10):
            aQuote = self.alpaca.get_latest_quote(self.ticker).ap 
            quoteList.append(aQuote)
            time.sleep(1)   
        quote = min(quoteList)
        print(f"---PRIMED QUOTE: {quote}")
         
   
        
    
bot = GridBot()
bot.run()