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

from datetime import datetime, timedelta, date
import pandas as pd
import numpy as np
import math

from scipy.optimize import minimize


class GSVOYGR(Strategy):
    def __init__(self, *args, strategy_args={}, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.strategy_args = strategy_args
        

    def backtestOneDay(self):
        # You can use self.current_date, self.user_close, self.user_yield and self.user_raw_data
        # save target weights to self.weights
        # set orders to self.orders
        # 20220520 update: self.user_asset_ages were added to user-data

        if self.current_date in self.update_date:
            self.update()    
            return
        # if not self.last_weights is None and self.current_date in self.rebalance_date:
        #     self.rebalance()
        #     return

    def update(self):
        self.on_sale_assets = [asset for asset in self.on_sale_assets if self.asset_ages[asset]>self.global_args['buffer']]
        self.user_close = self.user_close[self.on_sale_assets]
        self.volatility = pd.DataFrame(columns=[self.strategy_name])

        self.weights[self.on_sale_assets] = self.getWeights()

        # print(self.weights)
        
        # smoothing
        if self.historical_asset_weights.shape[0] > self.constants['DAY_OF_MONTH']:
            self.weights[self.on_sale_assets] = pd.concat((self.historical_asset_weights.iloc[-self.constants['DAY_OF_MONTH']:], self.weights.to_frame().T)).mean(axis=0)[self.on_sale_assets]
        elif self.historical_asset_weights.shape[0] == 0:
            pass
        else:
            # print(self.weights.to_frame().T)
            # print(pd.concat((self.historical_asset_weights, self.weights.to_frame())))
            self.weights[self.on_sale_assets] = pd.concat((self.historical_asset_weights, self.weights.to_frame().T)).mean(axis=0)[self.on_sale_assets]
        asset_close = self.user_close[self.on_sale_assets].iloc[-(3*self.constants['DAY_OF_MONTH'] + 5):]

        # print(self.weights)
        
        # do rebalance
        while getAnnualizedVolatility(self.weights[self.on_sale_assets], asset_close, DAY_OF_YEAR=self.constants['DAY_OF_YEAR']) > self.strategy_args['volatility_ceil']:
            self.weights[self.on_sale_assets] = self.weights[self.on_sale_assets] * 0.9
                    
        self.volatility[self.on_sale_assets] = getAnnualizedVolatility(self.weights[self.on_sale_assets], asset_close, DAY_OF_YEAR=self.constants['DAY_OF_YEAR'])

        return

    def rebalance(self):
        self.weights = self.weights.loc[self.on_sale_assets]
        pass 

    def afterBacktest(self):
        pass 


    def getWeights(self):
        weights_with_largest_return = pd.DataFrame(
            np.zeros((3, len(self.on_sale_assets))),
            columns = self.on_sale_assets,
        )
        for i,period in enumerate([3,6,9]):
            self.asset_close = self.user_close[self.on_sale_assets].iloc[-(period*self.constants['DAY_OF_MONTH'] + 5):]
            self.uac = getAnnualizedUACMatrix(self.asset_close, DAY_OF_YEAR=self.constants['DAY_OF_YEAR'])
            weights_with_largest_return.iloc[i] = self.getBestWeights()
        return weights_with_largest_return.mean(axis=0)

    def getBestWeights(self):
        w0 = [1/len(self.on_sale_assets)] * len(self.on_sale_assets)

        #set constraints
        cons = []
        cons.append({'type': 'ineq', 'fun': lambda x: sum(x)})   
        cons.append({'type': 'ineq', 'fun': lambda x: -sum(x) + 1})   

        cons.append({'type': 'ineq', 'fun': lambda x: -getAnnualizedVolatility(x, self.user_close, DAY_OF_YEAR=self.constants['DAY_OF_YEAR'], uac=self.uac)+self.strategy_args['volatility_ceil']})

        # add constraints for single asset
        bounds = tuple(self.dataset.asset_dict[asset].weight_range for asset in self.on_sale_assets)
        # constraints for group
        def addConstraintsForGroup(g):
            nonlocal cons
            all_leaf_asset = [asset for asset in g.getAllLeafAsset() if asset in self.on_sale_assets]
            all_leaf_asset_index = [i for i,a in enumerate(self.on_sale_assets) if a in all_leaf_asset]
            if not all_leaf_asset:
                return
            cons.append({'type': 'ineq', 'fun': lambda x: np.array(x)[all_leaf_asset_index].sum() - g.weight_range[0]})
            cons.append({'type': 'ineq', 'fun': lambda x: -np.array(x)[all_leaf_asset_index].sum() + g.weight_range[1]})
            for child in g.children.values():
                addConstraintsForGroup(child)
        addConstraintsForGroup(self.dataset.group) 

        weights = minimize(getAnnualizedLogReturn, w0, constraints=cons, args=(self.asset_close, self.constants['DAY_OF_YEAR']), bounds=bounds,  method='SLSQP').x

        return weights


# util funcs
def getAnnualizedUACMatrix(close_data, DAY_OF_YEAR=252):
    # Annualized Underlying Asset Covariance
    tmp = np.log((close_data / close_data.shift(5))[5:])
    uac = np.zeros((tmp.shape[1], close_data.shape[1]))
    for i in range(close_data.shape[1]):
        for j in range(close_data.shape[1]):
            uac[i,j] = (DAY_OF_YEAR / (5 * tmp.shape[0])) * (tmp.iloc[:,i] * tmp.iloc[:,j]).sum()
    return uac

def getAnnualizedVolatility(weights, close_data, DAY_OF_YEAR=252, uac=None):
    if uac is None:
        uac = getAnnualizedUACMatrix(close_data,  DAY_OF_YEAR=DAY_OF_YEAR)
    weights = weights[:,np.newaxis]
    auacrv = np.multiply(weights * weights.T, np.matrix(uac)).sum()
    auacrv = math.sqrt(auacrv)

    return auacrv


def getAnnualizedLogReturn(weights, close_data, DAY_OF_YEAR=252):
    asset_log_returns = getAssetAnnualizedLogReturn(close_data, DAY_OF_YEAR=DAY_OF_YEAR)
    sum_log_returns = (asset_log_returns * weights).sum()
    return -sum_log_returns


def getAssetAnnualizedLogReturn(close_data,   DAY_OF_YEAR=252):
    asset_log_returns = (DAY_OF_YEAR / close_data.shape[0]) * np.log(close_data.iloc[-1] / close_data.iloc[0])
    return asset_log_returns


