#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-02-24 

import os, sys, argparse, logging

from abc import ABC, abstractmethod

import pandas as pd
from tqdm import tqdm
import numpy as np

from collections import defaultdict

from framework.position_manager import AssetPositionManager, GroupPositionManager
from framework.order_manager import Order, OrderManager


class Strategy(ABC):
    def __init__(self,
                 strategy_name='', 
                 dataset = None, 
                 date_manager = None, 
                 constants = None, 
                 global_args = None, 
                 **kwargs, 
                 ) -> None:
        super().__init__()

        assert strategy_name, 'strategy_name must not be empty'
        self.strategy_name = strategy_name

        assert dataset, 'dataset is None'
        self.dataset = dataset

        assert date_manager, 'date_manager is None'
        self.date_manager = date_manager

        assert constants, 'constants is None'
        self.constants = constants

        assert global_args, 'global_args is None'
        self.global_args = global_args

        self.asset_list = list(self.dataset.asset_dict.keys())

        self.cash = self.global_args['cash'] if 'cash' in self.global_args else 10000
        self.historical_cash = pd.DataFrame(columns=['cash', 'cash_weight'])

        # build-in dataframes
        self.historical_weights = pd.DataFrame(columns=self.asset_list)
        self.value = self.cash
        self.historical_values = pd.DataFrame(columns=[self.strategy_name])

        # position manager dict
        self.asset_positions = {asset.asset_name: AssetPositionManager(asset) for asset in self.dataset.asset_dict.values()}
        self.group_positions = {group.name: GroupPositionManager(group, [self.asset_positions[asset] for asset in group.getAllLeafAsset()]) for group in self.dataset.group.getAllGroup()}

        self.order_manager = OrderManager()

    def setResultPath(self):
        self.result_path = os.path.join(self.global_args['result_path'], self.strategy_name)
        if not os.path.isdir(self.result_path):
            os.makedirs(self.result_path)

        
    @abstractmethod
    def backtestOneDay(self, *args, **kwargs):
        pass

    @abstractmethod
    def afterBacktest(self, *args, **kwargs):
        pass             

    def setBackTestAndRebalanceDate(self):
        self.update_date = self.date_manager.getUpdateDateList(self.global_args['backtest_date_range'], frequency=self.global_args['frequency'], missing_date=self.missing_date)
        if 'rebalance_frequency' in self.global_args:
            self.rebalance_date = self.date_manager.getUpdateDateList(self.global_args['backtest_date_range'], frequency=self.global_args['rebalance_frequency'], missing_date=self.missing_date)
        else:
            self.rebalance_date = []

    def setCloseAndYieldDf(self):
        # date list with buffer for get raw data
        # +1 for calculate daily yield
        self.backtest_date_list_with_buffer = self.date_manager.getDateList(self.global_args['backtest_date_range'], buffer=self.global_args['buffer']+1)
        self.backtest_date_list = self.date_manager.getDateList(self.global_args['backtest_date_range'], buffer=0)
        self.raw_data, self.missing_date = self.dataset.getData(self.backtest_date_list_with_buffer)
        self.asset_close_df = self.dataset.dict2CloseDf(self.raw_data)
        self.asset_daily_yield_df = self.asset_close_df / self.asset_close_df.shift()

    def setPositionPreclose(self):
        preclose = self.asset_close_df.loc[:self.backtest_date_list[0]].iloc[-1]
        for k,v in self.asset_positions.items():
            v.close = preclose[k]

    def beforeBacktest(self):
        self.setCloseAndYieldDf()
        self.setBackTestAndRebalanceDate()
        self.setPositionPreclose()

    def updatePositionBeforeOrder(self):
        for k, v in self.asset_positions.items():
            v.setCurrentDate(self.current_date)
            v.updateBeforeOrders(self.asset_daily_yield_df.loc[self.current_date, k])

    def updatePositionAfterOrder(self):
        self.value = sum([v.position for v in self.asset_positions.values()]) + self.cash
        self.historical_values.loc[self.current_date] = self.value
        self.historical_cash.loc[self.current_date] = [self.cash, self.cash/self.value]
        self.weights = [self.asset_positions[asset].position/self.value for asset in self.asset_list]
        self.historical_weights.loc[self.current_date] = self.weights

        # update position managers, check weight range
        for k,v in self.asset_positions.items():
            v.setCloseAndReturn(close=self.asset_close_df.loc[self.current_date, k], daily_return=self.asset_daily_yield_df.loc[self.current_date, k])
            v.updateAfterOrders(self.value)
            assert v.asset.weight_range[0] < v.weight < v.asset.weight_range[1], 'asset {} weight is {}, out of range {}'.format(k, v.weight, v.asset.weight_range)
        for k,v in self.group_positions.items():
            v.updateHistoricalData(date=self.current_date)
            assert v.group.weight_range[0] < v.weight < v.group.weight_range[1], 'group {} weight is {}, out of range {}'.format(k, v.weight, v.group.weight_range)
        

    def prepareUserData(self):
        # we can't use data on current_date
        self.user_close = self.asset_close_df.loc[:self.current_date].iloc[-self.global_args['buffer']-1: -1]
        self.user_yield = self.asset_daily_yield_df.loc[:self.current_date].iloc[-self.global_args['buffer']-1: -1]
        self.user_raw_data = {k: v.iloc[-self.global_args['buffer']-1: -1] for k, v in self.raw_data.items()}

        self.orders = []
        self.weights = None

    def weights2Orders(self):
        if self.weights is None:
            return
        for asset in self.asset_list:
            self.orders.append(Order(date=self.current_date, asset_name=asset, money=self.value*(self.weights[asset]-self.asset_positions[asset].weight), mark='weight_converted'))

    def executeOrders(self):
        self.weights2Orders()
        for order in self.orders:
            self.asset_positions[order.asset_name].executeOrder(order, self.dataset.asset_dict[order.asset_name].transection_cost)
            self.cash -= order.money
            self.order_manager.addOrder(order)

    def saveResults(self):
        self.asset_close_df = self.asset_close_df.loc[self.backtest_date_list]
        self.setResultPath()
        # weights and values and cash
        self.historical_weights.to_csv(os.path.join(self.result_path, 'weights.csv'))
        self.historical_values.to_csv(os.path.join(self.result_path, 'values.csv'))
        self.historical_cash.to_csv(os.path.join(self.result_path, 'cash.csv'))

        # positions
        with pd.ExcelWriter(os.path.join(self.result_path, 'asset_positions.xlsx')) as writer:
            for k,v in self.asset_positions.items():
                v.historical_data.to_excel(writer, sheet_name=k, )

        with pd.ExcelWriter(os.path.join(self.result_path, 'group_positions.xlsx')) as writer:
            for k,v in self.group_positions.items():
                v.historical_data.to_excel(writer, sheet_name=k, )

        # orders
        self.order_manager.historical_order.to_csv(os.path.join(self.result_path, 'orders.csv'))
        

    def run(self, *args, **kwargs):
        '''
        user api
        '''
        # do backtest
        logging.debug('backtesting {}'.format(self.strategy_name))
        self.beforeBacktest()
        
        for i in tqdm(range(len(self.backtest_date_list)),
                      desc='{}-backtest'.format(self.strategy_name), 
                      unit='days'):
            self.current_date = self.backtest_date_list[i]
            # update nav
            self.updatePositionBeforeOrder()

            if self.current_date in self.missing_date:
                return
            self.prepareUserData()
            self.backtestOneDay()
            self.executeOrders()
            self.updatePositionAfterOrder()

        self.saveResults()
        self.afterBacktest()

 


        
                



        
