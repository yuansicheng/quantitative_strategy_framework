#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-05-10 

import os, sys, argparse, logging

import pandas as pd
import numpy as np

class AssetPositionManager():
    def __init__(self, asset) -> None:
        self.asset = asset
        self.asset_name = asset.asset_name

        self.columns = ['weight', 'position', 'close', 'daily_return', 'total_investment', 'cost_price', 'current_yield', 'current_return', 'historical_return', 'total_return', 'number_of_position', 'total_transection_cost', ]
        for c in self.columns:
            setattr(self, c, 0)
        self.current_date = None
        self.close = np.nan

        self.historical_data = pd.DataFrame(columns=self.columns)

    def setCurrentDate(self, date):
        self.current_date = date

    def updateHistoricalData(self, ):
        assert self.current_date not in self.historical_data.index
        self.historical_data.loc[self.current_date] = [getattr(self, c) for c in self.columns]

    def setClose(self, close):
        if (not np.isnan(close)) and (not np.isnan(self.close)):
            self.daily_return = close / self.close if self.close else 0.
        self.close = close

    def executeOrder(self, order, transection_cost):
        assert self.asset_name == order.asset_name
        cost = abs(order.money) * transection_cost

        if -order.money > self.position - cost:
            return self.clearAll(transection_cost)
       
        self.total_transection_cost += cost
        
            
        if order.money >= 0:
            self.total_investment += order.money
            self.position += (order.money - cost)
            self.number_of_position += (order.money-cost) / self.close
        else:
            self.total_investment *= (1 + order.money/self.position)
            self.position += order.money
            self.number_of_position += order.money / self.close
            self.historical_return += -order.money * self.current_yield
        return order.money

    def clearAll(self, transection_cost):
        return_money = -self.position + self.position * transection_cost
        self.position = 0.
        self.total_investment = 0.
        self.number_of_position = 0.
        return return_money
        

    def updateBeforeOrders(self):
        self.position *= self.daily_return

    def updateWeight(self, stragy_value):
        self.weight = self.position / stragy_value if stragy_value else 0.

    def updateAfterOrders(self, stragy_value):
        self.current_return = self.position - self.total_investment
        self.current_yield = self.current_return / self.total_investment if self.total_investment else 0.
        self.total_return = self.historical_return + self.current_return
        self.updateWeight(stragy_value)
        self.cost_price = self.total_investment / self.number_of_position if self.number_of_position else 0.

        self.updateHistoricalData()

class GroupPositionManager():
    def __init__(self, group, positon_managers=[]) -> None:
        self.group = group
        self.positon_managers = positon_managers
        self.columns = ['weight', 'position', 'total_investment', 'total_yield', 'total_return', 'total_transection_cost', ]
        self.historical_data = pd.DataFrame(columns=self.columns)

        for key in self.columns:
            setattr(self, key, 0)

    def updateHistoricalData(self, date=None):
        assert date and date not in self.historical_data.index
        for key in self.columns:
            if key == 'total_yield':
                continue
            setattr(self, key, sum([getattr(m, key) for m in self.positon_managers]))
            self.historical_data.loc[date, key] = getattr(self, key)
        self.historical_data.loc[date, 'total_yield'] = self.total_return / self.total_investment if self.total_investment  else 0.
        self.total_yield = self.historical_data.loc[date, 'total_yield']


        
