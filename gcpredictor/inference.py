from datetime import datetime

import math

import numpy as np
import pandas as pd
import seaborn as sbn

import subprocess

from tqdm import tqdm

from gcpredictor.config import load_config, Task
from gcpredictor.model import save_diff
from gcpredictor.dataset import prepare_inference_dataset, \
    remove_last_col, \
    NMETHOD_COL, \
    SRT_COL, \
    TRT_COL, \
    OTYRT_COL, \
    REFERENCES_COL, \
    STRINGTABLE_COL, \
    PRUNE_COL, \
    TARGET_COL
import gcpredictor.utilities as utilities


FEATS = {
    'nmethod': remove_last_col(NMETHOD_COL),
    'srt': remove_last_col(SRT_COL),
    'trt': remove_last_col(TRT_COL),
    'otyrt': remove_last_col(OTYRT_COL),
    'prune': remove_last_col(PRUNE_COL),
    'stringtable': remove_last_col(STRINGTABLE_COL),
    'references': remove_last_col(REFERENCES_COL),
}

PREDICTORS = {} # cache
RESULT = {}
PREDICTIONS = {}

def generate_predictions(idx: int, config: dict, dataset: pd.DataFrame):
    global FEATS, PREDICTIONS, PREDICTORS
    if idx in PREDICTIONS:
        return PREDICTIONS[idx]
    else:
        if config['parallel']:
            from gcpredictor.dataset import STEAL_COL
            FEATS['steal'] = remove_last_col(STEAL_COL)

        PREDICTORS[idx] = {}
        RESULT[idx] = {}
        for feat in FEATS:
            assert isinstance(config['model'][feat], dict)
            name = config['model'][feat]['name']
            PREDICTORS[idx][feat] = \
                utilities.load(config['model'][feat]['file'])
            if name == 'sm' \
               and 'sm_add_constant' in config['model'][feat] \
               and config['model'][feat]['sm_add_constant']:
                import statsmodels.api as sm
                RESULT[idx][feat] = PREDICTORS[idx][feat].predict(sm.add_constant(dataset.loc[:, FEATS[feat]]))
            else:
                RESULT[idx][feat] = PREDICTORS[idx][feat].predict(dataset.loc[:, FEATS[feat]])

            if idx in PREDICTIONS:
                PREDICTIONS[idx] += RESULT[idx][feat]
            else:
                PREDICTIONS[idx] = RESULT[idx][feat]
        return PREDICTIONS[idx]


def test_predictor(idx: int, config: dict, dataset: pd.DataFrame):
    from sklearn.metrics import mean_squared_error, r2_score
    y = dataset[TARGET_COL[0]]
    y_pred = generate_predictions(idx, config, dataset)
    np.savetxt('./results/{}/inference/y_{}.txt'.format(config['name'], idx), y.values)
    np.savetxt('./results/{}/inference/y_pred_{}.txt'.format(config['name'], idx), y_pred)
    mse = mean_squared_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    print('Mean squared error: %.8f' % mse)
    print('Coefficient of determination: %.8f' % r2)
    return mse, r2

def generate_diff(idx: int, config: dict, dataset: pd.DataFrame):
    y = dataset[TARGET_COL[0]]
    pred = generate_predictions(idx, config, dataset)

    # np.savetxt('{}/{}/inference/main.txt'.format(config['dir']['output'], config['name']), main_y_pred)
    # np.savetxt('{}/{}/inference/stringtable.txt'.format(config['dir']['output'], config['name']), stringtable_y_pred)
    # np.savetxt('{}/{}/inference/otyrt.txt'.format(config['dir']['output'], config['name']), otyrt_y_pred)
    # np.savetxt('{}/{}/inference/pred.txt'.format(config['dir']['output'], config['name']), y)

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

    gnuplot_title = 'set title "{}\\nData = {}"\n'.format(title, name)
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

    min_bound = config_combined['min']
    max_bound = config_combined['max']

    with open('{}/{}-diff.plt'.format(gnuplot_dir, output_name), 'w') as f:
        f.write('set term pos eps color solid font ",27"\n')
        f.write('set size 2,2\n')
        f.write('set title "{}"\n'.format(title))
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
    config = load_config(args.config, Task.inference)
    print('Preparing dataset...')
    datasets = prepare_inference_dataset(config)
    print('Preparing output directory...')
    output_dir = './results/{}/inference'.format(config['name'])
    utilities.create_dir(output_dir)

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
        mse, r2 = test_predictor(idx,
                                 config,
                                 datasets[idx])
        pbar.set_description('Generating diffs for dataset {}'.format(name))
        diff = generate_diff(idx,
                             config,
                             datasets[idx])
        pbar.set_description('Saving diffs for dataset {} prediction'.format(name))
        sorted_indexes = save_diff(config,
                                   cdf_dir,
                                   config['data'][idx]['name'],
                                   diff)
        pbar.set_description('Creating plot for database {} prediction'.format(name))
        save_plot(config['model'],
                  config['data'][idx],
                  cdf_dir,
                  gnuplot_dir,
                  plot_dir,
                  diff,
                  sorted_indexes)

    print('Saving combined plot')
    save_plots(config, cdf_dir, gnuplot_dir, plot_dir)
        
if __name__ == '__main__':
    main(utilities.get_args())
    
