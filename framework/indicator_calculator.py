#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-05-12 

import os, sys, argparse, logging

import pandas as pd
import numpy as np
from functools import wraps

def strfTime(t):
    return t.strftime("%Y%m%d")

def outputDecorator(func):
    @wraps(func)
    def decorated(*args, **kwargs):    
        result = func(*args, **kwargs)
        if not (isinstance(result, pd.DataFrame) or isinstance(result, pd.Series)):
            return result
        if not (result.shape[0] == 1):
            return result
        if isinstance(result, pd.DataFrame) and result.shape[1] ==1:
            return result.values[0][0]
        if isinstance(result, pd.Series):
            return result.values[0]

        return result

    return decorated

class IndecatorCalculator():
    def __init__(self, constants=None):
        assert constants, 'Please set constants'
        self.constants = constants

    @outputDecorator
    def caculate(self, func, data, **kwargs):
        return func(data, **kwargs)
        

    def totalReturn(self, close_data):
        return self.caculate(totalReturn, close_data)

    def returnDevideYear(self, close_data):
        return self.caculate(returnDevideYear, close_data, DAY_OF_YEAR=self.constants['DAY_OF_YEAR'])

    def annualizedReturn(self, close_data):
        return self.caculate(annualizedReturn, close_data, DAY_OF_YEAR=self.constants['DAY_OF_YEAR'])

    def annualizedVolatility(self, close_data):
        return self.caculate(annualizedVolatility, close_data, DAY_OF_YEAR=self.constants['DAY_OF_YEAR'])

    def sharpeRatio(self, close_data):
        denominator = self.annualizedVolatility(close_data)
        return (self.annualizedReturn(close_data) - self.constants['RFR']) / (denominator+1e-6)

    @outputDecorator
    def calmarRatio(self, close_data):
        denominator = self.maxLoss(close_data).loc['max_loss']
        return (self.annualizedReturn(close_data) - self.constants['RFR']) / (denominator+1e-6)

    def maxLoss(self, close_data):
        return self.caculate(maxLoss, close_data)

    def longestLoss(self, close_data):
        return self.caculate(longestLoss, close_data)

    @outputDecorator
    def sortinoRatio(self, close_data):
        if isinstance(close_data, pd.Series):
            close_data = close_data.to_frame()
        RFR = self.constants['RFR']
        DAY_OF_YEAR = self.constants['DAY_OF_YEAR']
        def getSortinoDenominator(close_data):
            nonlocal RFR, DAY_OF_YEAR
            yield_data = close_data / close_data.shift() - 1
            daily_mar = (1+RFR) ** (1/DAY_OF_YEAR) - 1
            yield_data.loc[yield_data>daily_mar] = np.nan
            return (((yield_data.dropna() - daily_mar)**2).sum() / (yield_data.dropna().shape[0]-1)) ** 0.5
        denominator = close_data.apply(getSortinoDenominator)
        return (self.annualizedReturn(close_data) - RFR) / (denominator+1e-6)

    def informationRatio(self, close_data, target_columns=None):      
        if not isinstance(close_data, pd.DataFrame):
            return
        yield_data = close_data / close_data.shift() - 1
        result = pd.DataFrame(columns=close_data.columns)
        annualized_return = self.annualizedReturn(close_data)
        for column in target_columns:
            numerator = 0.01 * annualized_return.apply(lambda x: annualized_return[column] - x)
            denominator = yield_data.apply(lambda x: yield_data[column] - x).std()
            row_name = 'IR({})'.format(column)
            result.loc[row_name] = numerator / (denominator+1e-6)
            result.loc[row_name,column] = '--'
        return result

    def lastNdaysReturn(self, close_data, ndays):
        assert close_data.shape[0] >= ndays, 'close_data to short'
        close_data = close_data.iloc[-ndays:]
        return self.totalReturn(close_data)

    def lastOneYearReturn(self, close_data):
        return self.lastNdaysReturn(close_data, self.constants['DAY_OF_YEAR'])

    def lastHalfYearReturn(self, close_data):
        return self.lastNdaysReturn(close_data, self.constants['DAY_OF_MONTH'] * 6)

    def lastOneMonthReturn(self, close_data):
        return self.lastNdaysReturn(close_data, self.constants['DAY_OF_MONTH'])
        
##############################################
# basic functions

def returnDevideYear(close_data, DAY_OF_YEAR=252):
    # extract years
    if isinstance(close_data, pd.Series):
        close_data = close_data.to_frame()
    result = pd.DataFrame(columns=close_data.columns)
    years = set([i.year for i in close_data.index])
    last_year_value_flag = False
    for year in sorted(list(years)):
        tmp = close_data.loc[str(year)]
        if not last_year_value_flag:
            last_year_value = tmp.iloc[0]
            last_year_value_flag = True
        result.loc[year] = (tmp.iloc[-1] / last_year_value) ** (DAY_OF_YEAR/tmp.shape[0]) - 1
        last_year_value = tmp.iloc[-1]
    return result

def totalReturn(close_data):
    close_data = close_data.fillna(method='ffill').fillna(method='bfill')
    return close_data.iloc[-1] / close_data.iloc[0] -1

def annualizedReturn(close_data, DAY_OF_YEAR=252):
    not_na_num = close_data.notna().sum()
    return (totalReturn(close_data) + 1) ** (DAY_OF_YEAR/not_na_num) - 1


def annualizedVolatility(close_data, DAY_OF_YEAR=252):
    yield_data = close_data / close_data.shift()
    return yield_data.std() * (DAY_OF_YEAR**0.5) 

def maxLoss(close_data):
    if isinstance(close_data, pd.Series):
        close_data = close_data.to_frame()
    result = pd.DataFrame(columns=close_data.columns)
    def getAssetMaxLoss(data):
        data = np.array(data)
        max_loss = 0
        max_loss_range = ()
        # loop
        for i in range(1, len(data)):
            this_max_loss = (data[:i].max() - data[i:].min()) / data[:i].max()
            if this_max_loss > max_loss:
                max_loss = this_max_loss
                max_loss_range = (data[:i].argmax(), i+data[i:].argmin())
        return max_loss, max_loss_range

    for asset in close_data.columns:
        max_loss, max_loss_range = getAssetMaxLoss(close_data[asset].dropna())
        result.loc['max_loss', asset] = max_loss
        result.loc['max_loss_range', asset] = '{}-{}'.format(strfTime(close_data.index[max_loss_range[0]]), strfTime(close_data.index[max_loss_range[1]])) if max_loss_range else ''
    return result

def longestLoss(close_data):
    if isinstance(close_data, pd.Series):
        close_data = close_data.to_frame()
    result = pd.DataFrame(columns=close_data.columns)
    def getLongestLoss(data):
        index = list(data.index)
        data = list(data) + [1e6]
        longest_loss = 0
        longest_loss_range = None
        i_loss_start = 0
        for i in range(1, len(data)):
            if data[i] >= data[i_loss_start]:
                this_loss = (index[i-1]-index[i_loss_start]).days
                if this_loss > longest_loss:
                    longest_loss = this_loss 
                    longest_loss_range = (i_loss_start, i-1)
                i_loss_start = i
        return longest_loss, longest_loss_range
                
    for asset in close_data.columns:
        longest_loss, longest_loss_range = getLongestLoss(close_data[asset].dropna())
        result.loc['longest_loss', asset] = longest_loss
        result.loc['longest_loss_range', asset] = '{}-{}'.format(strfTime(close_data.index[longest_loss_range[0]]), strfTime(close_data.index[longest_loss_range[1]])) if longest_loss_range else ''
    return result


