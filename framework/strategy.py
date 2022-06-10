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
                 indicator_calculator=None, 
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

        assert indicator_calculator, 'indicator_calculator is None'
        self.indicator_calculator = indicator_calculator

        self.asset_list = list(self.dataset.asset_dict.keys())
        self.group_dict = {g.name: g for g in self.dataset.group.getAllGroup()}
        self.group_list = list(self.group_dict.keys())

        self.cash = self.global_args['cash'] if 'cash' in self.global_args else 10000

        # build-in dataframes
        self.historical_asset_weights = pd.DataFrame(columns=self.asset_list)
        self.historical_group_weights = pd.DataFrame(columns=self.group_list)
        self.value = self.cash
        self.shares = 0
        self.nav = 1
        self.total_asset_position = 0
        self.historical_values = pd.DataFrame(columns=['value', 'shares', 'nav', 'total_asset_position', 'cash', 'cash_weight'])

        # position manager dict
        self.asset_positions = {asset.asset_name: AssetPositionManager(asset) for asset in self.dataset.asset_dict.values()}
        self.group_positions = {group.name: GroupPositionManager(group, [self.asset_positions[asset] for asset in group.getAllLeafAsset()]) for group in self.group_dict.values()}

        self.order_manager = OrderManager()

        # asset ages
        self.asset_ages = {asset: -1 for asset in self.asset_list}

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
        self.update_date = self.date_manager.getUpdateDateList(self.global_args['backtest_date_range'], frequency=self.global_args['frequency'])
        if 'rebalance_frequency' in self.global_args:
            self.rebalance_date = self.date_manager.getUpdateDateList(self.global_args['backtest_date_range'], frequency=self.global_args['rebalance_frequency'])
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

    def beforeBacktest(self):
        self.setCloseAndYieldDf()
        self.setBackTestAndRebalanceDate()

    def getTotalAssetPosition(self):
        return sum([v.position for v in self.asset_positions.values()])

    def updateBeforeOrders(self):
        for k, v in self.asset_positions.items():
            v.setCurrentDate(self.current_date)
            v.setClose(self.asset_close_df.loc[self.current_date, k])
            v.updateBeforeOrders()
        self.value = self.getTotalAssetPosition() + self.cash

        # update weight
        for k, v in self.asset_positions.items():
            v.updateWeight(self.value)

        # update nav
        new_total_asset_position = self.getTotalAssetPosition()
        if self.total_asset_position:
            self.nav *= (new_total_asset_position / self.total_asset_position)
        self.total_asset_position = new_total_asset_position
        self.cash_brfore_order = self.cash

        # update asset ages
        for asset in self.asset_list:
            self.asset_ages[asset] = self.dataset.asset_dict[asset].getAge(self.current_date)

        self.on_sale_assets = [asset for asset in self.asset_list if self.dataset.asset_dict[asset].start_date <= self.current_date <= self.dataset.asset_dict[asset].stop_date]

    def updateAfterOrders(self):
        # if cash very small, set to 0
        if abs(self.cash) < 1e-3:
            self.cash = 0

        new_total_asset_position = self.getTotalAssetPosition()
        self.value = new_total_asset_position + self.cash
        # update shares and nav 
        if not new_total_asset_position:
            self.shares = 0      
        if self.total_asset_position == 0:
            self.shares = new_total_asset_position
        else:
            # print(self.current_date, self.shares, self.cash, self.cash_brfore_order, self.total_asset_position)
            self.shares *= (1 + (self.cash_brfore_order - self.cash) / self.total_asset_position)
        self.nav = new_total_asset_position / self.shares if self.shares else self.nav
        self.total_asset_position = new_total_asset_position
        
        self.historical_values.loc[self.current_date] = [self.value, self.shares, self.nav, self.total_asset_position, self.cash, self.cash/self.value]

        # update position managers, check weight range
        
        for k,v in self.asset_positions.items():
            v.updateAfterOrders(self.value)
            if self.orders:
                assert v.asset.weight_range[0] - 1e-3 <= v.weight <= v.asset.weight_range[1] + 1e-3, 'asset {} weight is {}, out of range {}'.format(k, v.weight, v.asset.weight_range)
        for k,v in self.group_positions.items():
            v.updateHistoricalData(date=self.current_date)
            if self.orders:
                assert v.group.weight_range[0] - 1e-3 <= v.weight <= v.group.weight_range[1] + 1e-3, 'group {} weight is {}, out of range {}'.format(k, v.weight, v.group.weight_range)

        self.weights = [self.asset_positions[asset].position/self.value for asset in self.asset_list]
        self.historical_asset_weights.loc[self.current_date] = self.weights
        self.historical_group_weights.loc[self.current_date] = [m.weight for m in self.group_positions.values()]
        

    def prepareUserData(self):
        # we can't use data on current_date
        self.user_close = self.asset_close_df.loc[:self.current_date, self.on_sale_assets].iloc[-self.global_args['buffer']-1: -1]
        self.user_yield = self.asset_daily_yield_df.loc[:self.current_date, self.on_sale_assets].iloc[-self.global_args['buffer']-1: -1]
        self.user_raw_data = {k: v.iloc[-self.global_args['buffer']-1: -1] for k, v in self.raw_data.items() if k in self.on_sale_assets}
        self.user_asset_ages = {k:v for k,v in self.asset_ages.items() if k in self.on_sale_assets}

        self.orders = []
        self.weights = pd.Series(index=self.on_sale_assets)
        self.weights[:] = np.nan

    def weights2Orders(self):
        for asset in self.weights.dropna().index:
            if self.weights[asset]-self.asset_positions[asset].weight != 0:
                self.orders.append(Order(date=self.current_date, asset_name=asset, money=self.value*self.weights[asset] - self.asset_positions[asset].position, mark='weight_converted'))

    def clearStopAsset(self):
        for asset in self.on_sale_assets:
            if not self.dataset.asset_dict[asset].stop_date == self.current_date:
                continue
            if not self.asset_positions[asset].position:
                continue
            self.orders.append(Order(date=self.current_date, asset_name=asset, money=-self.asset_positions[asset].position, mark='clear_all'))

    def groupOrder(self):
        order_dict = {}
        for order in self.orders:
            if order.mark == 'clear_all' or order.asset_name not in order_dict:
                order_dict[order.asset_name] = order
            elif order_dict[order.asset_name].mark != 'clear_all':
                order_dict[order.asset_name].money += order.money
        self.orders = list(order_dict.values())

    def executeOrders(self):
        self.weights2Orders()
        self.clearStopAsset()
        self.groupOrder()
        # sell first, then buy
        self.orders.sort(key=lambda x: x.money)
        for order in self.orders:
            if order.asset_name not in self.on_sale_assets:
                logging.error('{}-Trying to operate not on-sale asset: {}'.format(self.current_date, order.asset_name))
                continue
            if order.money > self.cash:
                order.money = self.cash
            # print(self.current_date, 'before', sum([v.position for v in self.asset_positions.values()]) + self.cash, self.cash)
            cost = self.asset_positions[order.asset_name].executeOrder(order, self.dataset.asset_dict[order.asset_name].transection_cost)
            self.cash -= cost
            # print(self.current_date, 'after', sum([v.position for v in self.asset_positions.values()]) + self.cash, self.cash)
            self.order_manager.addOrder(order)
                

    def saveResults(self):
        self.asset_close_df = self.asset_close_df.loc[self.backtest_date_list]
        self.setResultPath()

        # historical data
        with pd.ExcelWriter(os.path.join(self.result_path, 'historical_data.xlsx')) as writer:
            self.historical_values.to_excel(writer, sheet_name='values')
            self.order_manager.historical_order.to_excel(writer, sheet_name='orders')
            self.historical_asset_weights.to_excel(writer, sheet_name='asset_weights')
            self.historical_group_weights.to_excel(writer, sheet_name='group_weights')

        # positions
        with pd.ExcelWriter(os.path.join(self.result_path, 'asset_positions.xlsx')) as writer:
            for k,v in self.asset_positions.items():
                v.historical_data.to_excel(writer, sheet_name=k, )

        with pd.ExcelWriter(os.path.join(self.result_path, 'group_positions.xlsx')) as writer:
            for k,v in self.group_positions.items():
                v.historical_data.to_excel(writer, sheet_name=k, )
        

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
            self.updateBeforeOrders()

            # do backtest
            self.prepareUserData()
            self.backtestOneDay()
            self.executeOrders()

            self.updateAfterOrders()

        self.saveResults()
        self.afterBacktest()

 


        
                



        
