#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-04-28 

import os, sys, argparse, logging
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
try:
    plt.set_loglevel("info") 
except Exception as e:
    logging.error(e)

def drawWeights(weights, marked_date, fig_name):
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

def drawValuesPng(values, fig_name, asset_close_df=None, benchmark=None, init_value=1):
    # draw values
    plt.figure(figsize=(16,4), dpi=256)
    ax = plt.axes()
    values = init_value * (values / values.iloc[0])
    values.plot(ax=ax, zorder=1000, linewidth=2)
    if not benchmark is None:
        benchmark = init_value * (benchmark / benchmark.iloc[0])
        benchmark.plot(ax=ax, zorder=500, linewidth=2, style='--')
    if not asset_close_df is None:
        asset_close_df = init_value * (asset_close_df / asset_close_df.iloc[0])
        asset_close_df.plot(ax=ax, zorder=100, linewidth=1, alpha=0.6)
    plt.grid()
    plt.legend(loc=2, bbox_to_anchor=(1.05,1.0),borderaxespad = 0.)
    plt.title('Historical Values')
    plt.tight_layout()
    plt.savefig(fig_name)
    plt.close()

def drawValuesHtml(values, fig_name, asset_close_df=None, benchmark=None, init_value=1):
    from pyecharts.charts import Line
    from pyecharts import options as opts

    values = init_value * (values / values.iloc[0])
    values = values.round(decimals=5)

    Line = Line(opts.InitOpts(
        width='1000px', 
        height='400px', 
    ))
    Line.add_xaxis([x.strftime('%Y-%m-%d') for x in list(values.index)])

    for c in values.columns:
        Line.add_yaxis(c, replaceNan(values[c]), is_smooth=True, z_level=100, symbol_size=2, linestyle_opts=opts.LineStyleOpts(
            width=3, 
        ))
    if not benchmark is None:
        for c in benchmark.columns:
            Line.add_yaxis(c, replaceNan(benchmark[c]), is_smooth=True, z_level=10, symbol_size=2, linestyle_opts=opts.LineStyleOpts(
                type_='-',   
                width=2,
            ))

    if not asset_close_df is None:
        for c in asset_close_df.columns:  
            Line.add_yaxis(c, replaceNan(asset_close_df[c]), is_smooth=True, z_level=1, symbol_size=2, linestyle_opts=opts.LineStyleOpts(
                opacity=0.6, 
            ), )

    Line.set_global_opts(xaxis_opts=opts.AxisOpts(
        type_='time', 
        split_number=10,
        name='日期' , 
        name_location='center', 
        name_gap=50, 
    ))
    Line.set_global_opts(yaxis_opts=opts.AxisOpts(
        min_='dataMin', 
        max_='dataMax', 
        split_number=10, 
        name='净值' , 
        name_location='center', 
        name_gap=50, 
    ))
    Line.set_series_opts(label_opts=opts.LabelOpts(
        is_show=False,  
    ))
    Line.set_series_opts(tooltip_opts=opts.TooltipOpts(
        formatter='{a}: {c}'
    ))


    Line.render(fig_name)

def drawValues(values, fig_name, asset_close_df=None, benchmark=None, init_value=1, type='png'):
    assert type in ['png', 'html']
    fig_name = '{}.{}'.format(fig_name, type)
    if type == 'png':
        drawValuesPng(values, fig_name, asset_close_df=asset_close_df, benchmark=benchmark, init_value=init_value)
    if type == 'html':
        drawValuesHtml(values, fig_name, asset_close_df=asset_close_df, benchmark=benchmark, init_value=init_value)


def replaceNan(s):
    tmp = s
    if tmp.dropna().shape[0] == 0:
        return [None for x in tmp.values]
    first_value = tmp.dropna().iloc[0]
    tmp /= first_value
    tmp = tmp.round(decimals=5)
    return [x if not np.isnan(x) else None for x in tmp.values]