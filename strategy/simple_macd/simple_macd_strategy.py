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


class SimpleMacd(Strategy):
    def __init__(self, *args, strategy_args={}, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_args = strategy_args

        # This signal represents ma5>=ma20
        self.last_signal = None
        

    def backtestOneDay(self):
        # You can use self.current_date, self.user_close, self.user_yield and self.user_raw_data
        # save target weights to self.weights
        # set orders to self.orders
        # 20220520 update: self.user_asset_ages were added to user-data

        # first day
        if self.last_signal is None:
            self.last_signal = self.getSignal()
            return
        if self.current_date in self.update_date:
            self.update()    


    def update(self):
        this_signal = self.getSignal()
        # ma5 cross up ma20
        if this_signal and not self.last_signal:
            self.weights[:] = 1
        # ma5 cross down ma20
        elif not this_signal and self.last_signal:
            self.weights[:] = 0
        self.last_signal = this_signal


    def rebalance(self):
        pass 

    def afterBacktest(self):
        pass 


    # ##########################################
    def getSignal(self):
        def ma(x):
            return self.user_close.iloc[-x:, 0].mean()
        return ma(5) >= ma(20)



