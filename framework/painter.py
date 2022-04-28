#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-04-28 

import os, sys, argparse, logging

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.set_loglevel("info") 

class Painter():
    def __init__(self) -> None:
        pass

    def summarize(self, strategy, result_path):
        # check result_path
        if not os.path.isdir(result_path):
            os.makedirs(result_path)

        strategy.weights.to_csv(os.path.join(result_path, 'weights.csv'), encoding='utf_8_sig')
        self.drawWeights(strategy.weights, strategy.marked_date, os.path.join(result_path, 'weights.png'))

        strategy.values.to_csv(os.path.join(result_path, 'values.csv'))
        self.drawValues(strategy.values, os.path.join(result_path, 'values.png'), asset_close_df=strategy.asset_close_df)

    def drawWeights(self, weights, marked_date, fig_name):
        # draw weights
        plt.cla()
        plt.figure(figsize=(16,4), dpi=256)
        ax = plt.axes()
        weights.plot.area(ax=ax)
        for k,v in marked_date.items():
            zorder = 100 if k=='update' else 10
            plt.scatter(v, [weights.sum(axis=1).max()+0.05]*len(v), marker='+', zorder=zorder, label=k)
        plt.legend(loc=2, bbox_to_anchor=(1.05,1.0),borderaxespad = 0.)
        plt.ylim(0, weights.sum(axis=1).max()+0.1)
        plt.title('Historical Weights')
        plt.tight_layout()
        plt.savefig(fig_name)
        plt.close()

    def drawValues(self, values, fig_name, asset_close_df=None, benchmark=None):
        # draw values
        plt.cla()
        plt.figure(figsize=(16,4), dpi=256)
        ax = plt.axes()
        values.plot(ax=ax, zorder=1000, linewidth=2)
        if not benchmark is None:
            benchmark.plot(ax=ax, zorder=500, linewidth=2, style='--')
        if not asset_close_df is None:
            asset_close_df /= asset_close_df.iloc[0]
            asset_close_df.plot(ax=ax, zorder=100, linewidth=1, alpha=0.6)
        plt.grid()
        plt.legend(loc=2, bbox_to_anchor=(1.05,1.0),borderaxespad = 0.)
        plt.title('Historical Values')
        plt.tight_layout()
        plt.savefig(fig_name)
        plt.close()

