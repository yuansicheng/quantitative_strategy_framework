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
from framework.order_manager import Order


class SimpleFixedInvestment(Strategy):
    def __init__(self, *args, strategy_args={}, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_args = strategy_args

        self.fixed_investment = self.strategy_args['fixed_investment']
        self.profit_stop = self.strategy_args['profit_stop']
        self.sell_proportion = self.strategy_args['sell_proportion']

        self.last_sell_weeks = {asset: -1 for asset in self.asset_list}
        

    def backtestOneDay(self):
        # You can use self.current_date, self.user_close, self.user_yield and self.user_raw_data
        # save target weights to self.weights
        # set orders to self.orders
        # 20220520 update: self.user_asset_ages were added to user-data

        # update sell dict
        for asset in self.last_sell_weeks:
            if self.last_sell_weeks[asset] != -1:
                self.last_sell_weeks[asset] += 1
        

        if self.current_date in self.update_date:
            self.update()    
            return
        # if not self.last_weights is None and self.current_date in self.rebalance_date:
        #     self.rebalance()
        #     return

    def update(self):
        for asset in self.on_sale_assets:
            # print(self.current_date, asset, self.asset_positions[asset].total_yield, self.last_sell_weeks[asset])
            if self.asset_positions[asset].current_yield > self.profit_stop and (self.last_sell_weeks[asset] > self.constants['DAY_OF_MONTH'] or self.last_sell_weeks[asset] == -1):
                self.orders.append(Order(date=self.current_date, asset_name=asset, money=-self.sell_proportion * self.asset_positions[asset].position, mark='Achieve target profit'))
                self.last_sell_weeks[asset] = 0
            else:
                self.orders.append(Order(date=self.current_date, asset_name=asset, money=self.fixed_investment, mark='Fixedinvestment'))


    # def rebalance(self):
    #     self.weights = self.weights.loc[self.on_sale_assets]
    #     pass 

    def afterBacktest(self):
        pass 


