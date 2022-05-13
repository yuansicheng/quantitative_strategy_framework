#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-05-10 

import os, sys, argparse, logging

import pandas as pd

class AssetPositionManager():
    def __init__(self, asset) -> None:
        self.asset = asset
        self.asset_name = asset.asset_name

        self.current_date = None
        self.weight = 0.
        self.position = 0.
        self.close = None
        self.daily_return = None
        self.total_investment = 0.
        self.cost_price = 0.
        self.total_yield = 0.
        self.total_return = 0.
        self.number_of_position = 0.
        self.total_transection_cost = 0.

        self.historical_data = pd.DataFrame(columns=['weight', 'position', 'close', 'daily_return', 'total_investment', 'cost_price', 'total_yield', 'total_return', 'number_of_position', 'total_transection_cost', ])

    def setCurrentDate(self, date):
        self.current_date = date

    def updateHistoricalData(self, ):
        assert self.current_date not in self.historical_data.index
        self.historical_data.loc[self.current_date] = [self.weight, self.position, self.close, self.daily_return, self.total_investment, self.cost_price, self.total_yield, self.total_return, self.number_of_position, self.total_transection_cost]

    def setClose(self, close):
        assert close
        self.daily_return = close / self.close
        self.close = close
        

    def executeOrder(self, order, transection_cost):
        assert self.asset_name == order.asset_name
        cost = abs(order.money) * transection_cost
        self.total_transection_cost += cost
        self.position += order.money - cost
        self.number_of_position += (order.money-cost) / self.close

        if order.money >= 0:
            self.total_investment += order.money
        else:
            self.total_investment *= (1 + order.money/self.position)
        

    def updateBeforeOrders(self):
        self.position *= self.daily_return

    def updateAfterOrders(self, stragy_value):
        self.total_return = self.position - self.total_investment
        self.total_yield = self.total_return / self.total_investment if self.total_investment != 0 else 0.
        self.weight = self.position / stragy_value if stragy_value != 0 else 0.
        self.cost_price = self.position / self.number_of_position if self.number_of_position != 0 else 0.

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
        self.historical_data.loc[date, 'total_yield'] = self.historical_data.loc[date, 'total_return'] / self.historical_data.loc[date, 'total_investment'] if self.historical_data.loc[date, 'total_investment'] != 0 else 0.
        
        for key in self.columns:
            setattr(self, key, self.historical_data.loc[date, key])


        
