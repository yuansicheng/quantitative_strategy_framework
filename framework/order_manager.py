#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-05-10 

import os, sys, argparse, logging

import pandas as pd

class Order():
    def __init__(self, date=None, asset_name=None, money=None, mark='') -> None:
        assert date
        self.date = date
        assert asset_name
        self.asset_name = asset_name

        assert money
        self.money = money

        self.mark = mark

class OrderManager():
    def __init__(self) -> None:
        self.index = 0
        self.historical_order = pd.DataFrame(columns=['date', 'asset_name', 'money', 'mark'])

    def addOrder(self, order):
        self.historical_order.loc[self.index] = [order.date, order.asset_name, order.money, order.mark]
        self.index += 1