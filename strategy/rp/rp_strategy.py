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


class RP(Strategy):
    def __init__(self, *args, strategy_args={}, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_args = strategy_args
        self.last_weights = None
        

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
        std = self.user_yield.std()
        self.weights = (1/std) / (1/std).sum() 
        self.last_weights = self.weights[:]

    def rebalance(self):
        self.weights = self.last_weights[:]
        pass 

    def afterBacktest(self):
        pass 


