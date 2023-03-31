#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 24 11:20:09 2023

@author: jasonlcyy
"""

import pytz
import datetime
from selenium import webdriver
import yfinance as yf
from stock_indicators import indicators
from stock_indicators import Quote
import pandas as pd
import smtplib, ssl

def scrap_companies():
    driver_path = "/Users/jasonlcyy/Downloads/chromedriver"

    browser = webdriver.Chrome(executable_path = driver_path)
    
    ranking_link = "https://www.slickcharts.com/sp500"
    
    browser.get(ranking_link)
    
    stock_list = []

    for row in range(1, 506):
        try:
            temp = browser.find_element_by_xpath('/html/body/div[2]/div[3]/div[1]/div/div/table/tbody/tr[{}]/td[3]/a'.format(str(row)))
            stock_list.append(temp.text)
        except:
            break
    browser.quit()
    
    return stock_list

def check_availability(flag):
    ticker = yf.Ticker("AAPL")
    return pd.to_datetime(
            ticker.history(
                period = "1mo").reset_index()['Date']).dt.tz_localize(
                    None).iloc[-1].date() == flag.date()
                        
    
stock_list = scrap_companies()
flag = datetime.datetime(2023, 3, 30, 20, 0)

port = 465  # For SSL
password = 'gjfasssihjqswgmn'
smtp_server = "smtp.gmail.com"
sender_email = '643325jason@gmail.com'
receiver_email = '643325@gmail.com'

# Create a secure SSL context
context = ssl.create_default_context()

ty_NY = pytz.timezone('America/New_York')

while True:
    if (datetime.datetime.now(ty_NY) >= ty_NY.localize(flag)):
        if check_availability(flag) == True:
            message = """\
                Subject: """ + str(flag.date())
            for company in stock_list:
                ticker = yf.Ticker(company)
                ticker_hist = ticker.history(period = "1mo")
                try:
                    ticker_hist = ticker_hist.drop(['Dividends', 'Stock Splits'], axis=1).reset_index()
                    ticker_hist['Date'] = pd.to_datetime(ticker_hist['Date']).dt.tz_localize(None)
                    
                    quotes_list = [
                        Quote(d,o,h,l,c,v) 
                        for d,o,h,l,c,v 
                        in zip(ticker_hist['Date'], ticker_hist['Open'], ticker_hist['High'], 
                               ticker_hist['Low'], ticker_hist['Close'], ticker_hist['Volume'])
                    ]
                    ticker_hist['Date'] = ticker_hist['Date'].apply(lambda x: x.date())
                    
                    psar = indicators.get_parabolic_sar(quotes_list)
                    rsi = indicators.get_rsi(quotes_list)
                    
                    psar_current = psar[-1]
                    rsi_current = rsi[-1].rsi
                    rsi_trailing = rsi[-2].rsi
                    price = ticker_hist['Close'].iloc[-1]
                    
                    if psar_current.is_reversal == True and psar_current.sar < price:
                        # and rsi_trailing <= 30 and rsi_current >= 30:
                            message = message + "\nBuy " + company
                            message = message + "\nTrailing RSI: " + str(round(rsi_trailing, 2))
                            message = message + "\nCurrent RSI: " + str(round(rsi_current, 2))
                    if psar_current.is_reversal == True and psar_current.sar > price:
                        # and rsi_trailing >= 70 and rsi_current >= 70:
                            message = message + "\nSell " + company
                            message = message + "\nTrailing RSI: " + str(round(rsi_trailing, 2))
                            message = message + "\nCurrent RSI: " + str(round(rsi_current, 2))
                except:
                    message = message + '\n' + company + " no data"
                    continue
            print(str(flag.date()) + " Finished")
        else:
            message = message + "\nNot Trading Day"
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)
        flag = flag + datetime.timedelta(days = 1)
                
    
                            
        