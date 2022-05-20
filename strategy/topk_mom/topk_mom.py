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

import pandas as pd


class TopkMom(Strategy):
    def __init__(self, *args, strategy_args={}, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_args = strategy_args
        self.last_weights = None

        self.topk_args = self.strategy_args['topk_args']
        self.historical_data = self.historicalDataStr2Int(self.strategy_args['historical_data'])
        

    def backtestOneDay(self):
        # You can use self.current_date, self.user_close, self.user_yield and self.user_raw_data
        # save target weights to self.weights
        # set orders to self.orders

        if self.current_date in self.update_date:
            self.update()       
            return
        if not self.last_weights is None and self.current_date in self.rebalance_date:
            self.rebalance()
            return

    def update(self):
        group_topk = self.getGroupTopk()
        self.weights[:] = 0.
        for group, args in self.topk_args.items():
            for asset in group_topk[group]:
                self.weights[asset] = args[0] / args[1]
        self.last_weights = self.weights[:]

    def rebalance(self):
        self.weights = self.last_weights[:]
        pass 

    def afterBacktest(self):
        pass 

    def historicalDataStr2Int(self, s):
         if isinstance(s, str):
            if s=='year':
                return self.constants['DAY_OF_YEAR']
            elif s=='half_year':
                return self.constants['DAY_OF_MONTH'] * 6

    def getGroupTopk(self):
        used_assets = set()
        group_topk = {}
        for group, args in self.topk_args.items():
            topk = args[1]
            assets = self.group_dict[group].getAllLeafAsset()
            assert not (set(assets) & used_assets)
            used_assets.update(assets)
            assert len(assets) >= topk

            yields = [self.indicator_calculator.lastNdaysReturn(self.user_close[asset], self.historical_data) for asset in assets]
            tmp = pd.Series(yields, index=assets)
            group_topk[group] = tmp.sort_values(ascending=False).index[:topk]
        return group_topk