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

import numpy as np
from scipy.optimize import minimize


class RP(Strategy):
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
            self.update()    
            return
        if not self.last_weights is None and self.current_date in self.rebalance_date:
            self.rebalance()
            return

    def update(self):
        on_sale_assets = [asset for asset in self.on_sale_assets if self.asset_ages[asset]>self.global_args['buffer']]
        user_yield = self.user_yield[on_sale_assets]
        std = user_yield.std()
        w0 = (1/std) / (1/std).sum()
        w0 = np.matrix(w0)
        self.cov = np.matrix(user_yield.cov())
        # w0 = np.matrix([1/len(self.asset_list)] * len(self.asset_list)) 
        self.sigma = np.sqrt(w0 * self.cov * w0.T)[0,0]
        
        #set constraints
        cons = []
        cons.append({'type': 'eq', 'fun': lambda x: sum(x) - 1})

        # add constraints for single asset
        bounds = tuple(self.dataset.asset_dict[asset].weight_range for asset in on_sale_assets)
        # constraints for group
        def addConstraintsForGroup(g):
            nonlocal cons
            all_leaf_asset = [asset for asset in g.getAllLeafAsset() if asset in on_sale_assets]
            all_leaf_asset_index = [i for i,a in enumerate(on_sale_assets) if a in all_leaf_asset]
            if not all_leaf_asset:
                return
            cons.append({'type': 'ineq', 'fun': lambda x: np.array(x)[all_leaf_asset_index].sum() - g.weight_range[0]})
            cons.append({'type': 'ineq', 'fun': lambda x: -np.array(x)[all_leaf_asset_index].sum() + g.weight_range[1]})
            for child in g.children.values():
                addConstraintsForGroup(child)
        addConstraintsForGroup(self.dataset.group)

        self.weights[on_sale_assets] = minimize(self.riskParity, w0, constraints=cons, bounds=bounds, method='SLSQP').x
        # print(self.weights)

        self.last_weights = self.weights[:]

    def rebalance(self):
        self.weights = self.weights.loc[self.on_sale_assets]
        pass 

    def afterBacktest(self):
        pass 

    def riskContribution(self, weights):
        weights = np.matrix(weights)
        mrc = self.cov * weights.T / self.sigma       
        rc = np.multiply(mrc, weights.T)
        return rc

    def riskParity(self, weights):
        rc = self.riskContribution(weights)
        # * a constant number for scale the result, otherwise minimize will not work
        return sum(np.square(rc - self.sigma/len(weights)))[0,0] * 1e5


