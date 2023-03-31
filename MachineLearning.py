#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  8 12:14:02 2023

@author: jasonlcyy
"""

import yfinance as yf
from selenium import webdriver
import pandas as pd
from sklearn.preprocessing import StandardScaler
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM
from tensorflow.keras.layers import Dense
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_percentage_error
from matplotlib import pyplot as plt


def top_100_by_market_cap():
    driver_path = "..."

    browser = webdriver.Chrome(executable_path = driver_path)
    
    ranking_link = "https://companiesmarketcap.com/usa/largest-companies-in-the-usa-by-market-cap/"
    
    browser.get(ranking_link)
    
    stock_list = []
    
    for row in range(1, 101):
        temp = browser.find_element_by_xpath('//*[@id="cmkt"]/div[5]/table/tbody/tr[{}]/td[2]/div[2]/a/div[2]'.format(str(row)))
        stock_list.append(temp.text)
    
    browser.quit()
    
    return stock_list

def lstm_split(x_data, y_data, n_steps):
    X, y = [], []
    for i in range(len(y_data)-n_steps+1):
        X.append(x_data.iloc[i:i+n_steps-1, :])
        y.append(y_data.iloc[i+n_steps-1])
    return np.array(X), np.array(y)

companies = top_100_by_market_cap()

history_df = {}

for company in companies:
    ticker = yf.Ticker(company)
    ticker_hist = ticker.history(period = "10y")
    history_df[company] = ticker_hist
    
rmse_list = {}
mape_list = {}
y_pred_list = {}
y_test_list = {}
X_test_date_list = {}
predictions_next_day = {}

for company in companies:
    temp = history_df[company]

    y_temp = temp["Close"]
    X_temp = temp.iloc[:, 0:4]
    
    sc = StandardScaler()
    y_std = sc.fit_transform(y_temp.values.reshape(-1, 1))
    X_std = sc.fit_transform(X_temp.values)
    
    n_steps = 5
    
    X, y = lstm_split(X_temp, y_temp, n_steps)
    
    train_split = 0.8
    split_index = int(np.ceil(len(X)*train_split))
    date_index = X_temp.index
    
    X_train, X_test = X[:split_index], X[split_index:]
    y_train, y_test = y[:split_index], y[split_index:]
    X_train_date, X_test_date = date_index[n_steps-1:split_index+n_steps-1], date_index[split_index+n_steps-1:]
    
    print(X_train.shape, X_test.shape, y_train.shape, y_test.shape, X_train_date.shape, X_test_date.shape)
    
    lstm = Sequential()
    lstm.add(LSTM(32, input_shape = (4, 4),
                  activation = 'relu', return_sequences=True))
    lstm.add(LSTM(32, activation = 'relu'))
    lstm.add(Dense(1))
    lstm.compile(loss = 'mean_squared_error', optimizer = 'adam')
    lstm.summary()
    
    history = lstm.fit(X_train, y_train, epochs=40, verbose=2, shuffle=False)
    
    y_pred = lstm.predict(X_test)
    rmse_list[company] = mean_squared_error(y_test, y_pred, squared=False)
    mape_list[company] = mean_absolute_percentage_error(y_test, y_pred)
    y_pred_list[company] = y_pred
    y_test_list[company] = y_test
    X_test_date_list[company] = X_test_date
    
    # predicting stock price of the following day
    predict_next_day = lstm.predict(np.array([np.array(temp.iloc[len(temp)-4:, 0:4]),]))
    predictions_next_day[company] = predict_next_day[0][0]
    

plt.style.use("tableau-colorblind10")
# tickers with incomplete data
del y_pred_list['ABNB']
del y_pred_list['PYPL']
del y_test_list['ABNB']
del y_test_list['PYPL']

for company in y_pred_list.keys():
    y_pred_list[company] = y_pred_list[company].ravel()
    
predictions = pd.DataFrame(y_pred_list).mean(axis=1)
validations = pd.DataFrame(y_test_list).mean(axis=1)

# average price plot
plt.plot(X_test_date, predictions, label = "Predictions Average")
plt.plot(X_test_date, validations, label = "Actual Average")
plt.xlabel("Time")
plt.ylabel("Stock Price (USD)")
plt.xticks(rotation = 45, ha="right")
plt.legend(loc = "upper right")
plt.title("Average for 98 out of Top 100 US Stocks by Market Cap")
plt.show()

mape_df = pd.DataFrame(data = mape_list.values(), index = mape_list.keys(), columns=["MAPE"]).reset_index()

average_prices = {}

for company in history_df.keys():
    average_prices[company] = history_df[company]['Close'].mean()
    
average_df = pd.DataFrame(data = average_prices.values(), index = average_prices.keys(), columns=["Average Stock Price"]).reset_index()

error_df = pd.merge(mape_df, average_df, on = "index").rename(columns={"index": "Ticker"}).sort_values(by = "MAPE", ascending=False)

error_df_red = error_df[error_df['Average Stock Price']>1000]
average_mape = error_df['MAPE'].mean()
# MAPE plot
plt.text(3, 1000, "average mean absolute percentage error \n= " + str(round(average_mape*100, 2)) + "%")
plt.xticks(np.arange(0.5, 7, 0.5))
plt.xlabel("Mean Absolute Percentage Error (%)")
plt.ylabel("Average Stock Price (USD)")
plt.title("Correlation between Prediction Error and Average Stock Price")
plt.scatter(error_df['MAPE']*100.0, error_df['Average Stock Price'])
plt.scatter(error_df_red['MAPE']*100.0, error_df_red['Average Stock Price'], color = 'red')
plt.show()

# MAPE plot without outliers
plt.scatter(error_df['MAPE']*100, error_df['Average Stock Price'])
plt.ylim(0, 500)
z = np.polyfit(error_df['MAPE']*100, error_df['Average Stock Price'], 1)
p = np.poly1d(z)
plt.plot(error_df['MAPE']*100, p(error_df['MAPE']*100), color = 'red')
plt.title("Correlation between Prediction Error and Average Stock Price")
plt.xticks(np.arange(0.5, 7, 0.5))
plt.xlabel("Mean Absolute Percentage Error (%)")
plt.ylabel("Average Stock Price (USD)")
plt.show()

