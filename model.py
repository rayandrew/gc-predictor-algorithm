from tqdm import tqdm

import numpy as np

import utilities

def prepare_trainer(config):
    def train_sm(X, y, add_constant=False):
        import statsmodels.api as sm
        X_tr = X
        if add_constant:
            X_tr = sm.add_constant(X)
        res = sm.OLS(y, X_tr).fit()
        return res

    def train_sklearn(X, y):
        from sklearn.linear_model import RANSACRegressor
        reg = RANSACRegressor(random_state=42)
        reg.fit(X, y)
        return reg

    def train_svr(X, y):
        from sklearn.svm import SVR
        svr = SVR(C=1.0, epsilon=0.2)
        svr.fit(X, y)
        return svr

    predictor_trainers = {}

    if 'ransac' in config['models']:
        predictor_trainers['ransac'] = train_sklearn
        
    if 'lreg' in config['models']:
        predictor_trainers['lreg'] = train_sm

    if 'svr' in config['models']:
        predictor_trainers['svr'] = train_svr

    return predictor_trainers

def train_predictor(config, trainers, dataset):
    predictors = {}

    X_train, _, y_train, _ = dataset['splitted_dataset']
    clean_X_train, _, clean_y_train, _ = dataset['splitted_cleaned_dataset']

    pbar = tqdm(trainers)
    for trainer in pbar:
        pbar.set_description('Training predictor with algorithm {}'.format(trainer))
        if 'lreg' in trainer:
            predictors[trainer] = trainers[trainer](X_train, y_train, config['sm_add_constant'])
            predictors['cleaned_{}'.format(trainer)] = trainers[trainer](clean_X_train, clean_y_train, config['sm_add_constant'])
        else:
            predictors[trainer] = trainers[trainer](X_train, y_train)
            predictors['cleaned_{}'.format(trainer)] = trainers[trainer](clean_X_train, clean_y_train)

    return predictors

def test_predictor(predictors, dataset):
    def test(_model, X, y):
        from sklearn.metrics import mean_squared_error, r2_score
        y_pred = _model.predict(X)
        mse = mean_squared_error(y, y_pred)
        r2 = r2_score(y, y_pred)
        print('Mean squared error: %.8f' % mse)
        print('Coefficient of determination: %.8f' % r2)
        return mse, r2

    _, X_test, _, y_test = dataset['splitted_dataset']
    _, clean_X_test, _, clean_y_test = dataset['splitted_cleaned_dataset']

    result = {}
    
    pbar = tqdm(predictors)
    for predictor in pbar:
        pbar.set_description('Test plain dataset with algorithm {}'.format(predictor))
        mse, r2 = test(predictors[predictor], X_test, y_test)
        result['{}'.format(predictor)] = mse, r2
        pbar.set_description('Test cleaned dataset with algorithm {}'.format(predictor))
        clean_mse, clean_r2 = test(predictors[predictor], clean_X_test, clean_y_test)
        result['cleaned_{}'.format(predictor)] = clean_mse, clean_r2

    return result

def generate_diff(predictors, dataset, add_sm_constant=False):
    pbar = tqdm(predictors)
    
    result = {}

    _dataset = dataset['predict']
    
    for predictor in pbar:
        pbar.set_description('Generate diffs for {}'.format(predictor))
        if 'lreg' in predictor and add_sm_constant:
            pred = np.asarray(predictors[predictor].predict(sm.add_constant(_dataset[0])), dtype=float)
        else:
            pred = np.asarray(predictors[predictor].predict(_dataset[0]), dtype=float)
        diffs = []
        for i in range(len(_dataset[1].values)):
            real = _dataset[1].values[i]
            try:
                pr = pred.values[i]
            except:
                pr = pred[i]
            rem = (pr - real)
            diffs.append(rem)     
        result[predictor] = np.array(diffs)
    return result


def save_diff(config, output_dir, diffs):
    pbar = tqdm(diffs)

    cdf_dir = '{}/cdf'.format(output_dir)
    utilities.create_dir(cdf_dir)
    
    for diff in diffs:
        diff_sorted_idx = np.argsort(diff, axis=0)
        diff_sorted_idx = diff_sorted_idx[config['skip_value']:]

        with open('./{}/{}-diff-cdf.dat'.format(cdf_dir, diff), 'w') as f:
            pbar_2 = tqdm(enumerate(diff_sorted_idx))
            for cur, idx in pbar_2:
                f.write('%.10f,%.3f\n' % (float(cur / (len(diff_sorted_idx) - 1)), float(diff[idx])))
            f.close()

            import subprocess

def save_plot(model_name, model, dataset_name, dataset, diff, diff_sorted_idx):
    lower_bound = diff[diff_sorted_idx[0]] + 0.35
    upper_bound = diff[diff_sorted_idx[-1]] + 0.35
#     if upper_bound < 0.5:
#         upper_bound = 0.5
    if (upper_bound - lower_bound) < 1.0:
        upper_bound = upper_bound + 1.0
    print(lower_bound, upper_bound)
#     title = ' '.join(model_name.split('_'))
    title = '{/*1.2 Diff = Predicted GC Time - Real GC Time}'
    if 'ransac' in model_name:
        pred_title = '{/*0.8 RANSAC Linear Regression}'
    else:
        pred_title = '{/*0.8 Ordinary Linear Regresion}'

    subtitle = '1 thread allocates {} chunks in while true loop. Heap size is 10MB. Experiment time is 30s. GC algorithm : Parallel Scavenge.'.format(size)
    subtitle = '{/*0.75 ' + subtitle + '}'
    with open('./output/{}/{}-{}-{}.plt'.format(OUTPUT_DIR, model_name, dataset_name, 'diff'), 'w') as f:
        f.write('set term pos eps color solid font ",27"\n')
        f.write('set size 2,2\n')
        f.write('set title "{}\\n{}\\n{}"\n'.format(title, pred_title, subtitle))
#         f.write('set label "Subtitle" at screen 0.5, 0.9 font "Arial,8"\n')
        f.write('set key Left\n')
        f.write('set xlabel "Predicted GC Pause - Real GC Pause (ms)"\n')
        f.write('set ylabel "CDF of differences"\n')
        f.write('set output "./output/{}/plot/{}-{}-{}.eps"\n'.format(OUTPUT_DIR, model_name, dataset_name, 'diff'))
        f.write('set key top left\n')
        f.write('set datafile separator ","\n')
        f.write('set xrange [{}:{}]\n'.format(lower_bound, upper_bound))
        f.write('set yrange [0:1]\n')
        f.write('set grid ytics\n')
        f.write('set grid xtics\n')
        f.write('plot \\\n')
        f.write(' "./output/{}/cdf/{}-{}-{}-cdf.dat" u 2:1 with lines t "Diff" dt 1 lw 5 lc rgb "blue"'
                .format(OUTPUT_DIR, model_name, dataset_name, 'diff'))
        f.close()
    subprocess.Popen('gnuplot ./output/{}/{}-{}-{}.plt'.format(OUTPUT_DIR, model_name, dataset_name, 'diff').split())
