import os
import argparse
import json
import pandas as pd

import joblib
import jsonschema
from tqdm import tqdm

config_schema =  {
    '"type' : 'object',
    'properties' : {
        'name' : {'type' : 'string'},
        'skip_value' : {'type' : 'number'},
        'sm_add_constant' : {'type' : 'boolean'},
        'dir' : {
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
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type' : 'string'},
                    'file': {'type' : 'string'},
                    'color': {'type' : 'string'},
                    'label': {'type' : 'string'},
                },
                'required': ['name', 'file'],
            },
            'minItems': 1,             
        },
     },
}

def read_json_config(path: str):
    with open(path) as f:
        config = json.load(f)
        jsonschema.validate(config, config_schema)
        return config    

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Model joblib file', required=True)
    args = parser.parse_args()
    return args

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
