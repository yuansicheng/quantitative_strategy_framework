#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-05-21

import os
import sys
import argparse
import logging

import pandas as pd

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# select Huitianfu funds, and save to a new dir for backtest
fund_root_dir = 'data/fund'
fund_mktinfo_file = os.path.join(fund_root_dir, 'market_info/fund_info_20220513.xlsx')
fund_data_dir = os.path.join(fund_root_dir, 'quotation')

type_dict = {
    '普通股票型基金': 'stocks', 
    '中长期纯债型基金': 'bonds'}
target_root_dir = 'data_selected'
if not os.path.isdir(target_root_dir):
    os.makedirs(target_root_dir)
for t in type_dict:
    type_dict[t] = os.path.join(target_root_dir, type_dict[t])
    if not os.path.isdir(type_dict[t]): 
        os.makedirs(type_dict[t])

###########################################################################
###########################################################################
mktinfo = pd.read_excel(fund_mktinfo_file)

# select
mktinfo = mktinfo.loc[mktinfo['基金管理人'].str.contains('汇添富')]
mktinfo = mktinfo.loc[mktinfo['投资类型(二级分类)'].isin(list(type_dict.keys()))]
mktinfo = mktinfo.loc[mktinfo['是否初始基金'].str.contains('是')]

# print(mktinfo)

###########################################################################
###########################################################################

# find data file
all_file = os.listdir(fund_data_dir)
for i in mktinfo.index:
    data_file = '{}.csv'.format(mktinfo.loc[i, '证券代码'])
    if not data_file in all_file:
        continue
    tmp = pd.read_csv(os.path.join(fund_data_dir, data_file))
    # set close data
    tmp['CLOSE'] = tmp['NAV']
    tmp.to_csv(os.path.join(type_dict[mktinfo.loc[i, '投资类型(二级分类)']], data_file))


