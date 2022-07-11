#!/usr/bin/python
# -*- coding: utf-8 -*-

# @Author	:	yuansc
# @Contact	:	yuansicheng@ihep.ac.cn
# @Date		:	2022-04-15 

import os, sys, argparse, logging

import re
import yaml

class YamlLoader():
    def __init__(self) -> None:
        pass
    
    def parseYaml(self, yaml_file):
        yaml_data = self.loadYaml(yaml_file)
        self.checkYaml(yaml_data)
        return yaml_data

    def checkYaml(self, yaml_data):
        for key in ['constants', 'global_args', 'strategy', 'strategy_args', 'dataset', 'benchmark']:
            assert key in yaml_data, '{} must be set in yaml'.format(key)


    def loadYaml(self, yaml_file):
        assert os.path.isfile(yaml_file), 'yaml_file {} do not exists'.format(yaml_file)
        assert re.match('^.+\.ya?ml$', yaml_file), 'yaml_file must endswith .yaml or .yml'
        return yaml.load(open(yaml_file, encoding='utf-8'), Loader=yaml.Loader)