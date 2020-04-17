from datetime import datetime
import subprocess

import numpy as np
import pandas as pd
import seaborn as sbn

from sklearn.model_selection import train_test_split

from tqdm import tqdm

import utilities
from model import \
    prepare_trainer, \
    train_predictor, \
    test_predictor, \
    generate_diff, \
    save_diff

DATA_COL = [
#     'gc_id',
#     'before_gc_live_objects',
#     'before_gc_dead_objects',
#     'before_gc_total_objects',
#     'before_gc_roots_walk_elapsed',
    'allocation_size',
#     'young_gen_live_objects',
#     'young_gen_dead_objects',
    'young_gen_total_objects',
#     'young_gen_roots_walk_elapsed',
#     'total_young_gen_heap',
#     'used_young_gen_heap',
#     'old_gen_live_objects',
#     'old_gen_dead_objects',
#     'old_gen_total_objects',
#     'old_gen_roots_walk_elapsed',
#     'total_old_gen_heap',
#     'used_old_gen_heap',
#     'phases',
#     'stringtable_time',
#     'stringtable_size',
#     'stringtable_processed',
#     'stringtable_removed',
#     'gc_time',
    'gc_time_clean'
]

def prepare_dataset(config):
    print('Reading data')
    raw_dataset = utilities.read_data([
        '{}/{}/{}'.format(config['dir']['data'], config['name'], data['name']) for data in config['data']
    ], DATA_COL)
    dataset = pd.concat([dataset for dataset in raw_dataset])

    print()
    print('Data summaries')
    print(dataset.describe())

    print()
    print('Prepare dataset to predict')
    pred_dataset = (dataset.iloc[:, :-1], dataset.iloc[:, -1])
    
    print()
    print('Create cleaned dataset')
    clean_dataset = utilities.clean_data(dataset)

    print()
    print('Splitting dataset')
    splitted_dataset = train_test_split(
        dataset.iloc[:, :-1], 
        dataset.iloc[:, -1],
        test_size=0.25, 
        random_state=42)

    print()
    print('Splitting cleaned dataset')
    splitted_cleaned_dataset = train_test_split(
        clean_dataset.iloc[:, :-1], 
        clean_dataset.iloc[:, -1],
        test_size=0.25, 
        random_state=42)

    return {
        'raw': raw_dataset,
        'dataset': dataset,
        'predict': pred_dataset,
        'cleaned': clean_dataset,
        'splitted_dataset': splitted_dataset,
        'splitted_cleaned_dataset': splitted_cleaned_dataset,
    }

def main(args):
    print('Reading config...')
    config = utilities.read_json_config(args.config)
    print('Preparing output directory...')
    output_dir = '{}/{}/train'.format(config['dir']['output'], config['name'])
    utilities.create_dir(output_dir)
    print('Preparing dataset...')
    dataset = prepare_dataset(config)
    print('Preparing trainers...')
    trainers = prepare_trainer(config)
    print('There are {} models that needs to be trained'.format(len(trainers)))
    print()
    print('Training predictors...')
    predictors = train_predictor(config, trainers, dataset)
    print(predictors)
    print()
    print('Test predictors...')
    tests = test_predictor(predictors, dataset)
    print()
    print('Generate diffs...')
    diffs = generate_diff(predictors, dataset)
    print()
    print('Saving diffs...')
    save_diff(config, output_dir, diffs)
    
    
    
if __name__ == '__main__':
    main(utilities.get_args())


