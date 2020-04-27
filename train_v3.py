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
    save_diff, \
    save_plot

def prepare_dataset(config, train_type, columns):
    print('Reading data')
    raw_dataset = utilities.read_data([
        '{}/{}'.format(config['dir']['data'], data) for data in config['data'][train_type]
    ], columns)
    dataset = pd.concat([dataset for dataset in raw_dataset])

    if train_type == 'main':
        if 'specjvm' in config['name']:
            dataset = dataset.iloc[1000:2000]
        elif 'renaissance' in config['name']:
            pass
            # dataset = dataset[dataset['gc_time_clean'] < 100]
            # dataset = dataset.iloc[1500:]
            # dataset = dataset.iloc[2000:]
            # [dataset['gc_time_clean'] < 1500]
        elif 'dacapo' in config['name']:
            dataset = dataset.iloc[1000:2000]

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

def get_data_col(train_type: utilities.TrainType):
    def get_main_data_col():
        MAIN_DATA_COL = [
            'allocation_size',
            'young_gen_total_objects',
            # 'young_gen_heap_free',
            'gc_time_clean'
        ]
        return MAIN_DATA_COL

    def get_stringtable_data_col():
        STRINGTABLE_DATA_COL = [
            'stringtable_size',
            'stringtable_time',
        ]
        return STRINGTABLE_DATA_COL

    def get_prune_data_col():
        PRUNE_DATA_COL = [
            'prune_nmethod_pointer_count',
            'prune_nmethod_time',
        ]
        return PRUNE_DATA_COL

    def get_otyrt_data_col():
        OTYRT_DATA_COL = [
            # 'otyrt_stripe_total',
            # 'otyrt_ssize',
            # 'otyrt_start_card',
            # 'otyrt_end_card',
            # 'otyrt_slice_width',
            # 'otyrt_distance',
            # 'otyrt_slice_counter',
            # 'otyrt_dirty_card_counter',
            'otyrt_card_increment_counter',
            'otyrt_objects_scanned_counter',
            # 'otyrt_total_max_card_pointer_being_walked_through',
            'otyrt_time',
        ]
        return OTYRT_DATA_COL

    if train_type == utilities.TrainType.main:
        return get_main_data_col()
    elif train_type == utilities.TrainType.stringtable:
        return get_stringtable_data_col()
    elif train_type == utilities.TrainType.prune:
        return get_prune_data_col()
    elif train_type == utilities.TrainType.otyrt:
        return get_otyrt_data_col()

def main(args):
    print('Reading config...')
    config = utilities.read_json_config(args.config, utilities.Task.train)
    train_type = str(args.type)
    print('Preparing output directory...')
    output_dir = '{}/{}/train/{}'.format(config['dir']['output'], config['name'], train_type)
    utilities.create_dir(output_dir)
    print('Preparing dataset...')
    dataset = prepare_dataset(config, train_type, get_data_col(args.type))
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

    print('Preparing other output dirs')
    cdf_dir = '{}/cdf'.format(output_dir)
    gnuplot_dir = '{}/gnuplot'.format(output_dir)
    plot_dir = '{}/plot'.format(output_dir)
    model_dir = '{}/model'.format(output_dir)
    
    utilities.create_dir(cdf_dir)
    utilities.create_dir(gnuplot_dir)
    utilities.create_dir(plot_dir)
    utilities.create_dir(model_dir)

    print('Generate diff and plots...')

    pbar = tqdm(predictors)
    for predictor in pbar:
        pbar.set_description('Generate diffs for {}'.format(predictor))
        diff = generate_diff(config, predictors, predictor, dataset)
        pbar.set_description('Saving diffs for {}'.format(predictor))
        sorted_indexes = save_diff(config, cdf_dir, predictor, diff)
        pbar.set_description('Creating plot for {}'.format(predictor))
        save_plot(config, cdf_dir, gnuplot_dir, plot_dir, predictor, diff, sorted_indexes)
        pbar.set_description('Saving model for {}'.format(predictor))
        utilities.save('{}/{}.joblib'.format(model_dir, predictor), predictors[predictor])
        
    
if __name__ == '__main__':
    import time
    start_time = time.time()
    main(utilities.get_args(True))
    print("--- %s seconds ---" % (time.time() - start_time))


