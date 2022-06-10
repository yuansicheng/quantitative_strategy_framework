#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-02-05

import os
import sys
import argparse
import logging

from framework.strategy import Strategy


class SimpleRP(Strategy):
    def __init__(self, *args, strategy_args={}, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_args = strategy_args
        self.last_weights = None

        self.first_update_flag = True
        self.first_rebalance_flag = True
        

    def backtestOneDay(self):
        # You can use self.current_date, self.user_close, self.user_yield and self.user_raw_data
        # save target weights to self.weights
        # set orders to self.orders
        # 20220520 update: self.user_asset_ages were added to user-data

        if self.current_date in self.update_date:
            self.update()    
            return
        if not self.last_weights is None and self.current_date in self.rebalance_date:
            self.rebalance()
            return

    def update(self):
        if self.first_update_flag:
            logging.info('执行第一次update操作')
            self.showVariables()
            self.first_update_flag = False
        std = self.user_yield.std()
        self.weights = (1/std) / (1/std).sum()
        self.last_weights = self.weights[:]

    def rebalance(self):
        if self.first_rebalance_flag:
            logging.info('执行第一次再平衡操作，将资产权重恢复为上次执行update时的权重')
            self.first_rebalance_flag = False
        self.weights = self.weights.loc[self.on_sale_assets]
        pass 

    def afterBacktest(self):
        pass 

    def showVariables(self):
        pass
        # 当前日期
        key = '当前日期: self.current_date'
        self.printVariable(key, self.current_date)

        # 可使用的资产
        key = '可使用的资产: self.on_sale_assets'
        self.printVariable(key, self.on_sale_assets)

        # 资产年龄
        key = '资产年龄: self.user_asset_ages'
        self.printVariable(key, self.user_asset_ages)

        # 资产原始数据（截止到昨天，框架自动截取）
        key = '资产原始数据（截止到昨天，框架自动截取）: self.user_raw_data'
        self.printVariable(key, self.user_raw_data)

        # 资产收盘价（截止到昨天，框架自动截取）
        key = '资产收盘价（截止到昨天，框架自动截取）: self.user_close'
        self.printVariable(key, self.user_close)

        # 资产收益率（截止到昨天，框架自动截取）
        key = '资产收益率（截止到昨天，框架自动截取）: self.user_yield'
        self.printVariable(key, self.user_yield)

        # 资产状态
        key = '资产状态（以仓位为例）： self.asset_positions[self.on_sale_assets[0]].position'
        self.printVariable(key, self.asset_positions[self.on_sale_assets[0]].position)

        # 资产组状态
        key = '资产组状态（以仓位为例）: self.group_positions[self.group_list[0]].position'
        self.printVariable(key, self.group_positions[self.group_list[0]].position)

        # 资产权重
        key = '资产权重限制: self.dataset.asset_dict[self.on_sale_assets[0]].weight_range'
        self.printVariable(key, self.dataset.asset_dict[self.on_sale_assets[0]].weight_range)

    def printVariable(self, key, value):
        print('#'*50)
        print(key)
        print(value)
        print('#'*50)


