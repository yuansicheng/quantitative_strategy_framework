#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-05-10 

import os, sys, argparse, logging

import pandas as pd

class PositionManager():
    def __init__(self, asset_name) -> None:
        self.asset_name = asset_name

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

    def setCloseAndReturn(self, close=None, daily_return=None):
        assert close and daily_return
        self.close = close
        self.daily_return = daily_return

    def executeOrder(self, order, transection_cost):
        assert self.asset_name == order.asset_name
        cost = abs(order.money) * transection_cost
        self.total_transection_cost += cost
        self.total_investment += order.money
        self.position += order.money - cost
        self.number_of_position += (order.money-cost) / self.close
        

    def updateBeforeOrders(self, daily_yield):
        self.position *= daily_yield

    def updateAfterOrders(self, stragy_value):
        self.total_return = self.position - self.total_investment
        self.total_yield = self.total_return / self.total_investment if self.total_investment != 0 else 0.
        self.weight = self.position / stragy_value if stragy_value != 0 else 0.
        self.cost_price = self.position / self.number_of_position if self.number_of_position != 0 else 0.

        self.updateHistoricalData()

