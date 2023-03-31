#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 15 21:33:44 2023

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
import plotly.offline as py
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

''' PSAR  '''

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
    
    results = indicators.get_parabolic_sar(quotes_list)
    rsi = indicators.get_rsi(quotes_list)
    
    date_list = []
    sar_list = []
    is_reversal_list = []
    rsi_list = []
            
    for i in range(len(results)):
        if results[i].sar != None and rsi[i].rsi != None:
            date_list.append(results[i].date.date())
            sar_list.append(results[i].sar)
            is_reversal_list.append(results[i].is_reversal)
            rsi_list.append(rsi[i].rsi)
    
    
    price_list = ticker_hist[ticker_hist['Date'].isin(date_list)]['Close'].tolist()
    
    sar_color = ['green' if sar_list[i] < price_list[i] else 'red' for i in range(len(sar_list))]
    
    holding = False
    
    for i in range(len(date_list)):
        if holding == False and is_reversal_list[i] == True and sar_list[i] < price_list[i] \
        and rsi_list[i-1] <= 30 and rsi_list[i] >= 30:
            date = date_list[i]
            buy_price = ticker_hist[ticker_hist['Date'] == date]['Close'].values[0]
            holding = True
            print(str(date) + " Buy " + company + ": $" + str(round(buy_price, 2)))
        if holding == True and is_reversal_list[i] == True and sar_list[i] > price_list[i] \
        and rsi_list[i-1] >= 70 and rsi_list[i] <= 70:
            date = date_list[i]
            sell_price = ticker_hist[ticker_hist['Date'] == date]['Close'].values[0]
            holding = False
            profit = sell_price - buy_price
            profit_list.append(profit)
            cum_profit += profit
            cum_profit_list.append(cum_profit)
            print(str(date) + " Sell " + company + ": $" + str(round(sell_price, 2)) + 
                  " Profit: $" + str(round(profit, 2)) + 
                  " Cumulative Profit: $" + str(round(cum_profit, 2)))
            trade_list.append(company + ' ' + str(date) + ' Profit: $' + str(round(profit, 2)))

# example graph for PSAR and RSI
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
fig.add_trace(go.Scatter(x = date_list, y = sar_list, mode = 'markers', name = 'PSAR',
                                marker = {'color': sar_color}),
              row = 1, col = 1)
fig.add_trace(go.Scatter(x = date_list, y = rsi_list, mode = 'lines', name = 'RSI',
                          marker_color = 'cornflowerblue'),
              row = 2, col = 1)
fig.update_xaxes(rangebreaks = [
                        dict(bounds=['sat','mon']), # hide weekends
                        #dict(bounds=[16, 9.5], pattern='hour'), # for hourly chart, hide non-trading hours (24hr format)
                        dict(values=["2021-12-25","2022-01-01"]) #hide Xmas and New Year
                                ])
fig.add_hrect(y0 = 70, y1 = 30, line_width = 0.02, fillcolor = '#ffb3b3', opacity = 0.2, row = 2, col = 1)
fig.update_layout(template="plotly_dark",
                  xaxis_rangeslider_visible=False,
                  xaxis2_rangeslider_visible=True,
                  xaxis2_rangeslider_thickness=0.1,
                  xaxis_range=[datetime.strptime('2022/01/01', '%Y/%m/%d').date(), datetime.today().date()])
fig.show()

dp.upload_report([dp.Plot(fig)], name="PSAR")

# return graph for PSAR/PSAR+RSI
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
                         x = 25,
                         y = 1100,
                         font = dict(size=16)),
                    showarrow=False)
fig2.show()

dp.upload_report([dp.Plot(fig2)], name="PSARRSI_return")


''' END OF PSAR '''
