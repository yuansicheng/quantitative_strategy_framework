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


def setBenchmark(benchmark_dict):
    if not benchmark_dict:
        return None
    benchmark = Benchmark(benchmark_name=benchmark_dict['name'])
    for asset in benchmark_dict['asset']:
        benchmark.addAsset(asset['asset_file'], asset['weight'])
    return benchmark

def runSingleStrategy(Strategy, strategy_args, constants={}, global_args={}, strategy_name=''):
    global dataset, date_manager
    global strategy_dict
    assert strategy_name, 'strategy_name must not be empty'

    this_strategy = Strategy(constants=constants, global_args=global_args, strategy_args=strategy_args, strategy_name=strategy_name, dataset=dataset, date_manager=date_manager)
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
            strategy_args[k] = list(set(strategy_args[k]))
        locals = {}
        product_cmd = 'from itertools import product\nproducts = product({})'.format(','.join([str(v) for v in strategy_args.values()]))
        exec(product_cmd, {}, locals)
        keys = list(strategy_args.keys())
        for tmp in locals['products']:
            this_strategy_args = {keys[i]: tmp[i] for i in range(len(tmp))}
            # drop k with len(k)=1 to make strategy name shorter
            runSingleStrategy(Strategy, strategy_args, strategy_name='{}_{}'.format(yaml_data['strategy']['strategy_name'], '_'.join(['{}_{}'.format(k,v) for k,v in this_strategy_args.items() if len(strategy_args[k])>1])), constants=constants, global_args=global_args)
        
def daemon():
    global strategy_dict, result_path, date_list, benchmark_value, yaml_data
    strategy_values = pd.DataFrame(index=date_list)
    strategy_threads = [s.thread_id for s in strategy_dict.values()]
    while 1:
        running_threads = [t.ident for t in threading.enumerate()]
        running_strategy_num = sum([x in running_threads for x in strategy_threads])
        # logging.debug('{} strategies are now running'.format(running_strategy_num))

        # all strategy stopped
        if running_strategy_num == 0:
            for k,v in strategy_dict.items():
                strategy_values[k] = v.historical_values
            # draw all_in_one values
            asset_close_df = list(strategy_dict.values())[0].asset_close_df
            drawValues(strategy_values, os.path.join(result_path, 'all_in_one.png'),asset_close_df=asset_close_df, )
            # evaluator
            evaluation = Evaluator(strategy_value=strategy_values, benchmark_value=benchmark_value, asset_close_df=asset_close_df, constants=yaml_data['constants']).evaluate()
            evaluation.to_csv(os.path.join(result_path, 'evaluation.csv'), encoding='utf_8_sig')
            break

        sleep(3)

    

def checkPath(result_path):
    if not os.path.isdir(result_path):
        os.makedirs(result_path)


if __name__ == '__main__':
    args = getParser()
    yaml_file = args.yaml_file

    yaml_data = getYamlData(yaml_file)

    # generate date range
    if yaml_data['global_args']['generation_date_range']:
        yaml_data['global_args']['generation_date_range'] = [datetime(d[0], d[1], d[2]) for d in yaml_data['global_args']['generation_date_range']]
    # backtest date range
    yaml_data['global_args']['backtest_date_range'] = [datetime(d[0], d[1], d[2]) for d in yaml_data['global_args']['backtest_date_range']]

    loglevel = yaml_data['global_args']['loglevel'] if 'loglevel' in yaml_data['global_args'] else 20
    setLogLevel(loglevel)

    # import your strategy
    Strategy = importStrategy(yaml_data['strategy'])
    logging.debug(yaml_data)

    # dataset
    dataset = setDataset(yaml_data['dataset'])
    
    # benchmark
    benchmark = setBenchmark(yaml_data['benchmark'])

    date_manager = DateManager(yaml_data['global_args']['transection_date_file'])
    date_list = date_manager.getDateList(yaml_data['global_args']['backtest_date_range'])
    benchmark_value = benchmark.getValue(date_list) if benchmark else None

    # check result path
    result_path = yaml_data['global_args']['result_path']
    checkPath(result_path)

    # run strategy
    strategy_dict = {}
    runStrategy(yaml_data)

    # set daemon thread
    daemon_thread = threading.Thread(target=daemon)
    daemon_thread.start()





    


    