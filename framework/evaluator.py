#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-01-01 

import os, sys, argparse, logging

from datetime import datetime, timedelta, date

import pandas as pd
import numpy as np

def strfTime(t):
    return t.strftime("%Y%m%d")

class Evaluator:
    def __init__(self, strategy_value=None, benchmark_value = None, asset_close_df=None, indicator_calculator=None) -> None:
        self.strategy_value = strategy_value
        self.benchmark_value = benchmark_value
        self.asset_close_df = asset_close_df

        self.close_data = pd.concat((self.strategy_value, self.benchmark_value, self.asset_close_df), axis=1)

        assert indicator_calculator, 'indicator_calculator is None'
        self.indicator_calculator = indicator_calculator

        self.evaluation = pd.DataFrame(
            columns=self.close_data.columns,
        )

    def calculateReturnDevideYear(self) -> None:
        self.evaluation = pd.concat((self.evaluation, self.indicator_calculator.returnDevideYear(self.close_data) * 100))

    def calculateTotalReturn(self) -> None:
        self.evaluation.loc['累计收益率'] = self.indicator_calculator.totalReturn(self.close_data) * 100

    def calculateAnnualizedReturn(self) -> None:
        self.evaluation.loc['年化收益率'] = self.indicator_calculator.annualizedReturn(self.close_data) * 100

    def calculateAnnualizedVolatility(self) -> None:
        self.evaluation.loc['年化波动率'] = self.indicator_calculator.annualizedVolatility(self.close_data) * 100

    def calculateSharpeRatio(self) -> None:
        self.evaluation.loc['sharp比率'] = self.indicator_calculator.sharpeRatio(self.close_data)

    def calculateCalmarRatio(self) -> None:
        self.evaluation.loc['calmar比率'] = self.indicator_calculator.calmarRatio(self.close_data)

    def calculateSortinoRatio(self) -> None:
        self.evaluation.loc['sortino比率'] = self.indicator_calculator.sortinoRatio(self.close_data)

    def calculateMaxLoss(self) -> None:
        result = self.indicator_calculator.maxLoss(self.close_data)
        self.evaluation.loc['最大回撤'] = result.loc['max_loss'] * 100
        self.evaluation.loc['最大回撤发生区间'] = result.loc['max_loss_range']

    def calculateLongestLoss(self) -> None:
        result = self.indicator_calculator.longestLoss(self.close_data)
        self.evaluation.loc['最长回撤持续时间'] = result.loc['longest_loss']
        self.evaluation.loc['最长回撤发生区间'] = result.loc['longest_loss_range']

    def calculateInformationRatio(self) -> None:
        self.evaluation = pd.concat((self.evaluation, self.indicator_calculator.informationRatio(self.close_data, target_columns=self.benchmark_value.columns)))
        

    def evaluate(self) -> pd.DataFrame:
        self.calculateReturnDevideYear()
        self.calculateTotalReturn()
        self.calculateAnnualizedReturn()
        self.calculateAnnualizedVolatility()
        self.calculateMaxLoss()
        self.calculateLongestLoss()
        self.calculateSharpeRatio()
        self.calculateCalmarRatio()
        self.calculateSortinoRatio()
        self.calculateInformationRatio()

        return self.evaluation



