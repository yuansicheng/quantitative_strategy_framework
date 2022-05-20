#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-04-27 

import os, sys, argparse, logging
from glob import glob
from datetime import datetime
from framework import evaluator
import threading
from itertools import product
from time import sleep
import pandas as pd

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from framework.yaml_loader import YamlLoader
from framework.dataset import Dataset
from framework.benchmark import Benchmark
from framework.date_manager import DateManager
from framework.evaluator import Evaluator
from framework.drawFunc import *
from framework.indicator_calculator import IndecatorCalculator

def getParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-y', '--yaml_file', default='test.yaml')
    return parser.parse_args()

def getTimestamp():
    return datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

def importStrategy(strategy_dict):
    # Dynamically load the required classes according to the configuration of yaml file
    locals = {}
    exec("from {} import {} as Strategy".format(strategy_dict['strategy_file'], strategy_dict['strategy_name']), {}, locals)
    return locals['Strategy']

def setLogLevel(loglevel=20):
    logging.basicConfig(level=loglevel, format="%(asctime)s-%(filename)s[line:%(lineno)d]-%(funcName)s-%(levelname)s : %(message)s")

def getYamlData(yaml_file):
    yaml_loader = YamlLoader()
    return yaml_loader.parseYaml(yaml_file)

def setDataset(dataset_dict):
    dataset = Dataset()
    root_group = dataset_dict['group'][0]
    dataset.group.weight_range = root_group['weight_range']
    dataset.group.transection_cost = root_group['transection_cost']

    def addData(dataset, group_dict, current_group_name):
        if not group_dict:
            return dataset
        if 'group' in group_dict:
            for group in group_dict['group']:
                group_path = '{}/{}'.format(current_group_name, group['group_name'])
                dataset.addGroup(group=group_path, weight_range=group['weight_range'], transection_cost=group['transection_cost'])
                addData(dataset, group, group_path)
        if 'asset' in group_dict:
            for asset in group_dict['asset']:
                if asset['type'] == 'precision':
                    dataset.addAsset(asset['asset_file'], transection_cost=asset['transection_cost'], group=current_group_name, weight_range=asset['weight_range'])
                elif asset['type'] == 'fuzzy':
                    files = glob(asset['asset_file'])
                    for asset_file in files:
                        dataset.addAsset(asset_file, transection_cost=asset['transection_cost'], group=current_group_name, weight_range=asset['weight_range'])

    addData(dataset, root_group, '')
    dataset.printGroup(dataset.group)
    return dataset


def setBenchmark(benchmark_data):
    global date_manager
    date_list = date_manager.getDateList(yaml_data['global_args']['backtest_date_range'])
    if not benchmark_data:
        return None
    if not isinstance(benchmark_data, list):
        benchmark_data = [benchmark_data]
    benchmark_value = pd.DataFrame(index=date_list)
    for benchmark_dict in benchmark_data:
        benchmark = Benchmark(benchmark_name=benchmark_dict['name'])
        for asset in benchmark_dict['asset']:
            benchmark.addAsset(asset['asset_file'], asset['weight'])
        benchmark_value[benchmark_dict['name']] = benchmark.getValue(date_list)
    return benchmark_value

def runSingleStrategy(Strategy, strategy_args, constants={}, global_args={}, strategy_name=''):
    global dataset, date_manager, indicator_calculator
    global strategy_dict
    assert strategy_name, 'strategy_name must not be empty'

    this_strategy = Strategy(constants=constants, global_args=global_args, strategy_args=strategy_args, strategy_name=strategy_name, dataset=dataset, date_manager=date_manager, indicator_calculator=indicator_calculator)
    this_thread = threading.Thread(target=this_strategy.run)
    this_thread.start()
    this_strategy.thread_id = this_thread.ident
    strategy_dict[strategy_name] = this_strategy

def runStrategy(yaml_data):
    strategy_args = yaml_data['strategy_args']
    constants = yaml_data['constants']
    global_args = yaml_data['global_args']

    if not strategy_args:
        runSingleStrategy(Strategy, strategy_args, strategy_name=yaml_data['strategy']['strategy_name'], constants=constants, global_args=global_args)
    else:
        # convert all args to list
        for k,v in strategy_args.items():
            strategy_args[k] = v if isinstance(v, list) else [v]
            # drop duplicate
            try: strategy_args[k] = list(set(strategy_args[k]))
            except: pass
        locals = {}
        product_cmd = 'from itertools import product\nproducts = product({})'.format(','.join([str(v) for v in strategy_args.values()]))
        exec(product_cmd, {}, locals)
        keys = list(strategy_args.keys())
        for tmp in locals['products']:
            this_strategy_args = {keys[i]: tmp[i] for i in range(len(tmp))}

            # drop k with len(k)=1 to make strategy name shorter
            strategy_name = '{}_{}'.format(yaml_data['strategy']['strategy_name'], '_'.join(['{}_{}'.format(k,v) for k,v in this_strategy_args.items() if len(strategy_args[k])>1]))
            if strategy_name.endswith('_'):
                strategy_name = strategy_name[:-1]
            runSingleStrategy(Strategy, this_strategy_args, strategy_name=strategy_name, constants=constants, global_args=global_args)
        
def daemon():
    global strategy_dict, result_path, date_manager, benchmark_value, yaml_data, indicator_calculator
    date_list = date_manager.getDateList(yaml_data['global_args']['backtest_date_range'])
    strategy_values = pd.DataFrame(index=date_list)
    strategy_threads = [s.thread_id for s in strategy_dict.values()]
    while 1:
        running_threads = [t.ident for t in threading.enumerate()]
        running_strategy_num = sum([x in running_threads for x in strategy_threads])
        # logging.debug('{} strategies are now running'.format(running_strategy_num))

        # all strategy stopped
        if running_strategy_num == 0:
            for k,v in strategy_dict.items():
                strategy_values[k] = v.historical_values['nav']
            # draw all_in_one values
            asset_close_df = list(strategy_dict.values())[0].asset_close_df
            drawValues(strategy_values, os.path.join(result_path, 'all_in_one'),asset_close_df=asset_close_df, benchmark=benchmark_value, type=yaml_data['global_args']['fig_type'])
            # evaluator
            evaluation = Evaluator(strategy_value=strategy_values, benchmark_value=benchmark_value, asset_close_df=asset_close_df, indicator_calculator=indicator_calculator).evaluate()
            with pd.ExcelWriter(os.path.join(result_path, 'evaluation.xlsx')) as writer:
                evaluation.to_excel(writer, sheet_name='evaluation')
            break

        sleep(3)

    

def checkPath(result_path):
    if not os.path.isdir(result_path):
        os.makedirs(result_path)


if __name__ == '__main__':
    args = getParser()
    yaml_file = args.yaml_file

    yaml_data = getYamlData(yaml_file)

    # backtest date range
    yaml_data['global_args']['backtest_date_range'] = [datetime(d[0], d[1], d[2]) for d in yaml_data['global_args']['backtest_date_range']]

    loglevel = yaml_data['global_args']['loglevel'] if 'loglevel' in yaml_data['global_args'] else 20
    setLogLevel(loglevel)

    # import your strategy
    Strategy = importStrategy(yaml_data['strategy'])
    logging.debug(yaml_data)

    # dataset
    dataset = setDataset(yaml_data['dataset'])

    # date_manager
    date_manager = DateManager(yaml_data['global_args']['transection_date_file'])
    
    # benchmark
    benchmark_value = setBenchmark(yaml_data['benchmark'])

    # indicator calculator
    indicator_calculator = IndecatorCalculator(constants=yaml_data['constants'])

    # check result path
    result_path = yaml_data['global_args']['result_path']
    checkPath(result_path)

    # run strategy
    strategy_dict = {}
    runStrategy(yaml_data)

    # set daemon thread
    daemon_thread = threading.Thread(target=daemon)
    daemon_thread.start()





    


    