#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  8 22:21:59 2023

@author: jasonlcyy
"""

from stock_indicators import indicators
from stock_indicators import Quote
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from selenium import webdriver
from plotly.subplots import make_subplots
from datetime import datetime
import datapane as dp

dp.login(token="ffc8357d80e3e1cbf77819036ef70878818bb721")

pio.renderers.default = "browser"

def top_100_by_market_cap():
    driver_path = "/Users/jasonlcyy/Downloads/chromedriver"

    browser = webdriver.Chrome(executable_path = driver_path)
    
    ranking_link = "https://companiesmarketcap.com/usa/largest-companies-in-the-usa-by-market-cap/"
    
    browser.get(ranking_link)
    
    stock_list = []
    
    for row in range(1, 101):
        temp = browser.find_element_by_xpath('//*[@id="cmkt"]/div[5]/table/tbody/tr[{}]/td[2]/div[2]/a/div[2]'.format(str(row)))
        stock_list.append(temp.text)
    
    browser.quit()
    
    return stock_list

''' MACD Crossover Strategy '''

companies = top_100_by_market_cap()

profit_list = []

cum_profit_list = []

trade_list = []

cum_profit = 0

for company in companies:
    ticker = yf.Ticker(company)
    ticker_hist = ticker.history(period = "10y")
    ticker_hist = ticker_hist.drop(['Dividends', 'Stock Splits'], axis=1).reset_index()
    ticker_hist['Date'] = pd.to_datetime(ticker_hist['Date']).dt.tz_localize(None)
    
    quotes_list = [
        Quote(d,o,h,l,c,v) 
        for d,o,h,l,c,v 
        in zip(ticker_hist['Date'], ticker_hist['Open'], ticker_hist['High'], 
               ticker_hist['Low'], ticker_hist['Close'], ticker_hist['Volume'])
    ]
    ticker_hist['Date'] = ticker_hist['Date'].apply(lambda x: x.date())
    
    results = indicators.get_macd(quotes_list, 12, 26, 9)
    rsi = indicators.get_rsi(quotes_list)
    
    date_list = []
    macd_list = []
    signal_list = []
    histogram_list = []
    rsi_list = []
    
    for i in range(len(results)):
        if results[i].histogram != None and rsi[i].rsi != None:
            date_list.append(results[i].date.date())
            macd_list.append(results[i].macd)
            signal_list.append(results[i].signal)
            histogram_list.append(results[i].histogram)
            rsi_list.append(rsi[i].rsi)
    
    histogram_color = ['green' if float(x) >= 0 else 'red' for x in histogram_list]
    
    macd_over_signal = False
    holding = False
    
    for i in range(len(date_list)):
        if macd_over_signal == False and macd_list[i] > signal_list[i] and holding == False:
            date = date_list[i]
            buy_price = ticker_hist[ticker_hist['Date'] == date]['Close'].values[0]
            macd_over_signal = True
            holding = True
            print(str(date) + " Buy " + company + ": $" + str(round(buy_price, 2)))
        if macd_over_signal == True and macd_list[i] < signal_list[i] and holding == True:
            date = date_list[i]
            sell_price = ticker_hist[ticker_hist['Date'] == date]['Close'].values[0]
            macd_over_signal = False
            holding = False
            profit = sell_price - buy_price
            profit_list.append(profit)
            cum_profit += profit
            cum_profit_list.append(cum_profit)
            print(str(date) + " Sell " + company + ": $" + str(round(sell_price, 2)) + 
                  " Profit: $" + str(round(profit, 2)) + 
                  " Cumulative Profit: $" + str(round(cum_profit, 2)))
            trade_list.append(company + ' ' + str(date) + ' Profit: $' + str(round(profit, 2)))

# example of MACD graph
fig = make_subplots(rows = 2, cols=1, row_width = [0.2, 0.8], shared_xaxes = True, vertical_spacing=0.05)
fig.add_trace(go.Candlestick(x=ticker_hist['Date'],
                              open=ticker_hist['Open'],
                              high=ticker_hist['High'],
                              low=ticker_hist['Low'],
                              close=ticker_hist['Close'],
                              showlegend=False,
                              name='OHLC'
                             ),
              row = 1, col = 1)
fig.add_trace(go.Scatter(x = date_list, y = macd_list, mode = 'lines', name = 'macd',
                                marker_color = 'cornflowerblue'),
               row = 2, col = 1)
fig.add_trace(go.Scatter(x=date_list,y=signal_list,mode='lines', name = 'signal',
                          marker_color = 'red'),
               row = 2, col = 1)
fig.add_trace(go.Bar(x = date_list, y = histogram_list, name = 'histogram',
                      marker = {'color':histogram_color}, showlegend=False),
               row = 2, col = 1)
fig.update_xaxes(rangebreaks = [
                        dict(bounds=['sat','mon']), # hide weekends
                        dict(values=["2021-12-25","2022-01-01"]) #hide Xmas and New Year
                                ])
fig.update_layout(template="plotly_dark",
                  xaxis_rangeslider_visible=False,
                  xaxis2_rangeslider_visible=True,
                  xaxis2_rangeslider_thickness=0.1,
                  xaxis_range=[datetime.strptime('2022/01/01', '%Y/%m/%d').date(), datetime.today().date()])
fig.show()

# MACD return graph
profit_color = ['green' if float(x) >= 0 else 'red' for x in profit_list]
positive_count = len(list(filter(lambda x: x >= 0, profit_list)))
accuracy = positive_count / len(profit_list)

fig2 = go.Figure()
fig2.add_trace(go.Bar(x = list(range(1, len(profit_list)+1)), y = profit_list,
                       marker = {'color':profit_color},
                       name = "Profit",
                       showlegend=False))
fig2.add_trace(go.Scatter(x = list(range(1, len(profit_list)+1)), y = cum_profit_list,
                          mode = 'lines',
                          name = "Cumulated profit",
                          marker_color = "cornflowerblue"))
fig2.update_layout(hovermode = "x unified",
                   template="plotly_dark")
fig2.add_annotation(dict(text="Accuracy: " + str(round(accuracy*100, 2)) + "%",
                         x = 30,
                         y = 810,
                         font = dict(size=16)),
                    showarrow=False)
fig2.show()

dp.upload_report([dp.Plot(fig2)], name="MACDRSI_return")

''' END OF MACD CROSSOVER '''


