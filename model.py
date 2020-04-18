from tqdm import tqdm
import numpy as np

def get_model_name(model: str):
    if model == 'ransac':
        return 'RANSAC Linear Regression'
    elif model == 'lreg':
        return 'Linear Regression'
    elif model == 'svr':
        return 'Support Vector Regression'
    else:
        return ''

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

def generate_diff(config, predictors, predictor, dataset):
    pbar = tqdm(predictors)
    result = {}
    _dataset = dataset['predict']

    if 'lreg' in predictor and config['sm_add_constant']:
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

    return np.array(diffs)


def save_diff(config, out_dir, predictor, diff):
    diff_sorted_idx = np.argsort(diff, axis=0)
    diff_sorted_idx = diff_sorted_idx[config['skip_value']:]
        
    with open('./{}/{}-diff-cdf.dat'.format(out_dir, predictor, diff), 'w') as f:
        pbar = tqdm(enumerate(diff_sorted_idx))
        for cur, idx in pbar:
            f.write('%.10f,%.3f\n' % (float(cur / (len(diff_sorted_idx) - 1)), float(diff[idx])))
        f.close()
            
    return diff_sorted_idx

def save_plot(config, cdf_dir, gnuplot_dir, output_dir, predictor, diff, sorted_indexes):
    import subprocess

    lower_bound = diff[sorted_indexes[0]] + 0.35
    upper_bound = diff[sorted_indexes[-1]] + 0.35

    if (upper_bound - lower_bound) < 1.0:
        upper_bound = upper_bound + 1.0

    title = '{/*1.2 Diff = Predicted GC Time - Real GC Time}'

    model_name = get_model_name(predictor)
    pred_title = '{/*0.8' + model_name + '}'

    if config['subtitle'] and config['subtitle'] != '':
        subtitle = '\\n{/*0.75 ' + config['subtitle'] + '}'
    else:
        subtitle = ''
    gnuplot_title = 'set title "{}\\n{}{}"\n'.format(title, pred_title, subtitle)
    with open('{}/{}-{}.plt'.format(gnuplot_dir, predictor, 'diff'), 'w') as f:
        f.write('set term pos eps color solid font ",27"\n')
        f.write('set size 2,2\n')
        f.write(gnuplot_title)
        f.write('set key Left\n')
        f.write('set xlabel "Predicted GC Pause - Real GC Pause (ms)"\n')
        f.write('set ylabel "CDF of differences"\n')
        f.write('set output "{}/{}-{}.eps"\n'.format(output_dir, predictor, 'diff'))
        f.write('set key top left\n')
        f.write('set datafile separator ","\n')
        f.write('set xrange [{}:{}]\n'.format(lower_bound, upper_bound))
        f.write('set yrange [0:1]\n')
        f.write('set grid ytics\n')
        f.write('set grid xtics\n')
        f.write('plot \\\n')
        f.write(' "{}/{}-{}-cdf.dat" u 2:1 with lines t "Diff" dt 1 lw 5 lc rgb "blue"'
                .format(cdf_dir, predictor, 'diff'))
        f.close()
    subprocess.Popen('gnuplot {}/{}-{}.plt'.format(gnuplot_dir, predictor, 'diff').split())
