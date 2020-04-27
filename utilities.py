import os
import argparse
import json
import pandas as pd

import joblib
import jsonschema
from tqdm import tqdm

from enum import Enum

class Task(Enum):
    train = 'train'
    parse = 'parse'
    inference = 'inference'    

    def __str__(self):
        return self.value

class TrainType(Enum):
    main = 'main'
    stringtable = 'stringtable'
    prune = 'prune'
    otyrt = 'otyrt'

    def __str__(self):
        return self.value    

def generate_schema(task: Task):
    def generate_parse_schema():
        parse_data_schema = {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type' : 'string'},
                    'file': {'type' : 'string'},
                    'old_format': {'type': 'boolean'},
                },
                'required': ['name', 'file'],
            },
            'minItems': 1,
        }
        parse_config_schema = {
            'name': {'type' : 'string'},
            'dir': {
                'type' : 'object',
                'properties': {
                    'data': {'type' : 'string'},
                    'output': {'type' : 'string'},
                },
                'required': ['data', 'output'],
            },
            'data': parse_data_schema,
        }
        return parse_config_schema
        
    def generate_train_schema():
        data_schema = {
            'type': 'array',
            'items': {
                'type': 'string',
            },
            'minItems': 1,
        }

        train_config_schema =  {
            'type' : 'object',
            'properties' : {
                'name': {'type' : 'string'},
                'skip_value' : {'type' : 'number'},
                'sm_add_constant' : {'type' : 'boolean'},
                'subtitle': {'type' : 'string'},
                'dir': {
                    'type' : 'object',
                    'properties': {
                        'data': {'type' : 'string'},
                        'output': {'type' : 'string'},
                    },
                    'required': ['data', 'output'],
                },
                'models': {
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'enum': ['ransac', 'lreg', 'svr']
                    },
                    'minItems': 1,
                    'maxItems': 3,
                    'additionalItems': False,
                },
                'data': {
                    'type': 'object',
                    'properties': {
                        'main': data_schema,
                        'stringtable': data_schema,
                        'prune': data_schema,
                        'otyrt': data_schema,
                    },
                },
            },
        }
        return train_config_schema

    def generate_inference_schema():
        inference_data_schema = {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type' : 'string'},
                    # 'file': {'type' : 'string'},
                    'color': {'type' : 'string'},
                    'label': {'type' : 'string'},
                    'subtitle': {'type' : 'string'},
                },
                'required': ['name'],
            },
            'minItems': 1,
        }

        inference_model_schema = {
            'type': 'object',
            'properties': {
                'name': {'type' : 'string'},
                'file': {'type' : 'string'},
            },
            'required': ['name', 'file'],
        }

        inference_config_schema = {
            'name': {'type' : 'string'},
            'skip_value' : {'type' : 'number'},
            'sm_add_constant' : {'type' : 'boolean'},
            'subtitle': {'type' : 'string'},
            'dir': {
                'type' : 'object',
                'properties': {
                    'data': {'type' : 'string'},
                    'output': {'type' : 'string'},
                },
                'required': ['data', 'output'],
            },
            'combined_plot': {
                'type' : 'object',
                'properties': {
                    'max': {'type' : 'number'},
                    'min': {'type' : 'number'},
                    'subtitle': {'type': 'string'},
                },
                'required': ['max', 'min', 'subtitle'],
            },
            'models': {
                'type': 'object',
                'properties': {
                    'main': inference_model_schema,
                    'stringtable': inference_model_schema,
                    'prune': inference_model_schema,
                    'otyrt': inference_model_schema,
                }
            },
            'data': inference_data_schema,
        }
        return inference_config_schema

    if task == Task.train:
        return generate_train_schema()
    elif task == Task.parse:
        return generate_parse_schema()
    else:
        return generate_inference_schema()

def read_json_config(path: str, task: Task = Task.parse):
    with open(path) as f:
        config = json.load(f)
        jsonschema.validate(config, generate_schema(task))
        return config    

def get_args(train: bool = False):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Config file', required=True)
    if train:
        parser.add_argument('-t', '--type', type=TrainType, help='Config file', required=True, choices=list(TrainType))
    args = parser.parse_args()
    return args

# def is_main_train(train_type: TrainType = TrainType.main):
    # return train_type == TrainType.main

def read_data(csv_files, data_col, prefix = ''):
    datasets = []
    pbar = tqdm(csv_files)
    for csv_file in pbar:
        csvfile = '{}{}.csv'.format(prefix, csv_file)
        pbar.set_description('Reading csv file {}'.format(csvfile))
        dataset = pd.read_csv(csvfile)[data_col]
        datasets.append(dataset)
    return datasets

def clean_data(dataframe: pd.DataFrame, n_round: int = 2):
    df = dataframe.copy(deep=True)
    df = df.round(n_round)
    df = df.drop_duplicates()
    return df

def format_date(date):
    return '{}-{}-{}T{}:{}:{}'.format(date.day, date.month, date.year, date.hour, date.minute, date.second)

def create_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        print ('Creation of the directory %s failed' % path)
        return False
    else:
        print ('Successfully created the directory %s ' % path)
        return True

def save(filename: str, payload):
    joblib.dump(payload, filename)

def load(filename: str):
    return joblib.load(filename)
