from datetime import datetime

import math

import numpy as np
import pandas as pd
import seaborn as sbn

import subprocess

from tqdm import tqdm

from model import save_diff

import utilities

DATA_COL = [
    'allocation_size',
    'young_gen_total_objects',
    'stringtable_size',
    'gc_time',
]

def prepare_dataset(config, columns = DATA_COL):
    print('Reading data...')
    dataset = utilities.read_data([
        '{}/{}'.format(config['dir']['data'], data['name']) for data in config['data']
    ], columns)
    return dataset

def test_predictor(dataset, main_predictor, stringtable_predictor):
    from sklearn.metrics import mean_squared_error, r2_score
    X_main = dataset.iloc[:, :-2]
    X_stringtable = dataset.iloc[:, 2:-1]
    y = dataset.iloc[:, -1]
    main_y_pred = main_predictor.predict(X_main)
    stringtable_y_pred = stringtable_predictor.predict(X_stringtable)
    y_pred = main_y_pred + stringtable_y_pred
    mse = mean_squared_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    print('Mean squared error: %.8f' % mse)
    print('Coefficient of determination: %.8f' % r2)
    return mse, r2

def generate_diff(dataset, main_predictor, stringtable_predictor):
    X_main = dataset.iloc[:, :-2]
    X_stringtable = dataset.iloc[:, 2:-1]
    y = dataset.iloc[:, -1]
    main_y_pred = np.asarray(main_predictor.predict(X_main), dtype=float)
    stringtable_y_pred = np.asarray(stringtable_predictor.predict(X_stringtable), dtype=float)
    pred = main_y_pred + stringtable_y_pred
    diffs = []
    for i in range(len(y.values)):
        real = y.values[i]
        try:
            pr = pred.values[i]
        except:
            pr = pred[i]
        rem = pr - real
        diffs.append(rem)
    return np.array(diffs)

def save_plot(config_model, config_data, cdf_dir, gnuplot_dir, output_dir, diff, sorted_indexes):
    import subprocess

    lower_bound = diff[sorted_indexes[0]]
    upper_bound = diff[sorted_indexes[-1]]

    title = '{/*1.2 Diff = Predicted GC Time - Real GC Time}'
    name = config_data['name']

    color = 'black'

    if 'color' in config_data:
        color = config_data['color']

    pred_title = '{/*0.8 MainModel = ' + config_model['main']['name'] + ', StringTableModel = ' + config_model['stringtable']['name'] + '}'

    if 'subtitle' in config_data and config_data['subtitle'] != '':
        subtitle = '\\n{/*0.75 ' + config_data['subtitle'] + '}'
    else:
        subtitle = ''
    gnuplot_title = 'set title "{}\\n{}{}"\n'.format(title, pred_title, subtitle)
    with open('{}/{}-diff.plt'.format(gnuplot_dir, name), 'w') as f:
        f.write('set term pos eps color solid font ",27"\n')
        f.write('set size 2,2\n')
        f.write(gnuplot_title)
        f.write('set key Left\n')
        f.write('set xlabel "Predicted GC Pause - Real GC Pause (ms)"\n')
        f.write('set ylabel "CDF of differences"\n')
        f.write('set output "{}/{}-diff.eps"\n'.format(output_dir, name))
        f.write('set key top left\n')
        f.write('set datafile separator ","\n')
        f.write('set xrange [{}:{}]\n'.format(lower_bound, upper_bound))
        f.write('set yrange [0:1]\n')
        f.write('set grid ytics\n')
        f.write('set grid xtics\n')
        f.write('plot \\\n')
        f.write(' "{}/{}-diff-cdf.dat" u 2:1 with lines t "Diff" dt 1 lw 6 lc rgb "{}"'
                .format(cdf_dir, name, color))
        f.close()
    subprocess.Popen('gnuplot {}/{}-diff.plt'.format(gnuplot_dir, name).split())


# save_plots(CSV_FILES, OUTPUT_NAME, -500, 500, COLORS, 'Heap Size 4G. StringTableSize is 60013.')

def save_plots(config, cdf_dir: str, gnuplot_dir: str, output_dir: str):
    output_name = '{}-combined'.format(config['name'])
    config_combined = config['combined_plot']
    config_model = config['model']
    
    title = '{/*1.2 Diff = Predicted GC Time - Real GC Time}'
    pred_title = '{/*0.8 MainModel = ' + config_model['main']['name'] + ', StringTableModel = ' + config_model['stringtable']['name'] + '}'
    
    subtitle = ''
    if 'subtitle' in config_combined:
        subtitle = config_combined['subtitle']

    if subtitle != '':
        subtitle = '{/*0.75 ' + subtitle + '}'

    min_bound = config_combined['min']
    max_bound = config_combined['max']

    with open('{}/{}-diff.plt'.format(gnuplot_dir, output_name), 'w') as f:
        f.write('set term pos eps color solid font ",27"\n')
        f.write('set size 2,2\n')
        f.write('set title "{}\\n{}\\n{}"\n'.format(title, pred_title, subtitle))
        f.write('set key Left\n')
        f.write('set xlabel "Predicted GC Pause - Real GC Pause (ms)"\n')
        f.write('set ylabel "CDF of differences"\n')
        f.write('set output "{}/{}-diff.eps"\n'.format(output_dir, output_name))
        f.write('set key top left\n')
        f.write('set datafile separator ","\n')
        f.write('set xrange [{}:{}]\n'.format(min_bound, max_bound))
        f.write('set yrange [0:1]\n')
        f.write('set grid ytics\n')
        f.write('set grid xtics\n')
        f.write('plot \\\n')
        for file_idx in range(len(config['data'])):
            data_config = config['data'][file_idx]
            data_name = data_config['name']
            data_label = data_config['label'] if 'label' in data_config else dataset_name 
            data_color = data_config['color']
            if file_idx == 0:
                f.write('    "{}/{}-diff-cdf.dat" u 2:1 with lines t "{}" dt 1 lw 6 lc rgb "{}", \\\n'
                    .format(cdf_dir, data_name, data_label, data_color))
            elif file_idx < len(config['data']) - 1:
                f.write('    "{}/{}-diff-cdf.dat" u 2:1 with lines t "{}" dt 1 lw 6 lc rgb "{}", \\\n'
                    .format(cdf_dir, data_name, data_label, data_color))
            else:
                f.write('    "{}/{}-diff-cdf.dat" u 2:1 with lines t "{}" dt 1 lw 6 lc rgb "{}"'
                    .format(cdf_dir, data_name, data_label, data_color))
        f.close()
    subprocess.Popen('gnuplot {}/{}-diff.plt'.format(gnuplot_dir, output_name).split())

def main(args):
    print('Reading config...')
    config = utilities.read_json_config(args.config, utilities.Task.inference)
    print('Preparing output directory...')
    output_dir = '{}/{}/inference'.format(config['dir']['output'], config['name'])
    utilities.create_dir(output_dir)
    print('Preparing dataset...')
    datasets = prepare_dataset(config, DATA_COL)
    print('Preparing predictors...')
    main_predictor = utilities.load(config['model']['main']['file'])
    stringtable_predictor = utilities.load(config['model']['stringtable']['file'])

    print('Preparing other output dirs')
    cdf_dir = '{}/cdf'.format(output_dir)
    gnuplot_dir = '{}/gnuplot'.format(output_dir)
    plot_dir = '{}/plot'.format(output_dir)
    
    utilities.create_dir(cdf_dir)
    utilities.create_dir(gnuplot_dir)
    utilities.create_dir(plot_dir)
    
    pbar = tqdm(range(len(datasets)))
    for idx in pbar:
        name = config['data'][idx]['name']
        pbar.set_description('Outputting performance metrics for dataset {}'.format(name))
        mse, r2 = test_predictor(datasets[idx], main_predictor, stringtable_predictor)
        pbar.set_description('Generating diffs for dataset {}'.format(name))
        diff = generate_diff(datasets[idx], main_predictor, stringtable_predictor)
        pbar.set_description('Saving diffs for dataset {} prediction'.format(name))
        sorted_indexes = save_diff(config, cdf_dir, config['data'][idx]['name'], diff)
        pbar.set_description('Creating plot for database {} prediction'.format(name))
        save_plot(config['model'], config['data'][idx], cdf_dir, gnuplot_dir, plot_dir, diff, sorted_indexes)

    print('Saving combined plot')
    save_plots(config, cdf_dir, gnuplot_dir, plot_dir)
        
if __name__ == '__main__':
    main(utilities.get_args())
    
