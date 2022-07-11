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

from pypfopt import EfficientFrontier
from pypfopt import risk_models
from pypfopt import expected_returns
from pypfopt import plotting


class MVO(Strategy):
    def __init__(self, *args, strategy_args={}, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_args = strategy_args
        self.last_weights = None
        

    def backtestOneDay(self):
        # You can use self.current_date, self.user_close, self.user_yield and self.user_raw_data
        # save target weights to self.weights
        # set orders to self.orders
        # 20220520 update: self.user_asset_ages were added to user-data

        if self.current_date in self.update_date:
            try:
                self.update()    
            except:
                logging.error('{}, update failed'.format(self.current_date))
            return
        if not self.last_weights is None and self.current_date in self.rebalance_date:
            self.rebalance()
            return

    def update(self):
        df = self.user_close[:]
        mu = expected_returns.mean_historical_return(df)
        s = risk_models.sample_cov(df)
        ef = EfficientFrontier(mu, s) 

        if self.strategy_args['constraints']:

            # add constraints for single asset
            con = [self.dataset.asset_dict[asset].weight_range for asset in self.on_sale_assets]
            ef.add_constraint(lambda x: x >= [c[0] for c in con])
            ef.add_constraint(lambda x: x <= [c[1] for c in con])
            # constraints for group
            def addConstraintsForGroup(g):
                # print(g.name)
                nonlocal ef
                all_leaf_asset = [asset for asset in g.getAllLeafAsset() if asset in self.on_sale_assets]
                if not all_leaf_asset:
                    return
                sector_mapper = {a:'' for a in self.on_sale_assets}  
                sector_mapper.update({a:g.name for a in all_leaf_asset})
                ef.add_sector_constraints(sector_mapper, sector_lower={g.name:g.weight_range[0]}, sector_upper={g.name:g.weight_range[1]})
                for child in g.children.values():
                    addConstraintsForGroup(child)
            addConstraintsForGroup(self.dataset.group)

        tr = self.strategy_args['target_return']
        while(tr > 0):
            try:  
                weights = ef.efficient_return(tr)
                self.weights[:] = list(weights.values())
                # weights may contains some very small negative values like -1e-16, we need to clip those values to 0.
                self.weights.loc[self.weights<0] = 0.
                break
            except ValueError as e:
                pass
                # logging.warning(this_date)
                # logging.warning(e)
            tr -= 0.001
        self.last_weights = self.weights[:]

    def rebalance(self):
        self.weights = self.weights.loc[self.on_sale_assets]
        pass 

    def afterBacktest(self):
        pass 


