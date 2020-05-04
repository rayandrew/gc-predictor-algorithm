def get_args(train: bool = False):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Config file', required=True)
    if train:
        from gcpredictor.config import TrainType
        parser.add_argument('-t', '--type', type=TrainType, help='Config file', required=True, choices=list(TrainType))
    args = parser.parse_args()
    return args

def read_data(csv_files, prefix = ''):
    from tqdm import tqdm
    import pandas as pd
    datasets = []
    pbar = tqdm(csv_files)
    for csv_file in pbar:
        csvfile = '{}{}.csv'.format(prefix, csv_file)
        pbar.set_description('Reading csv file {}'.format(csvfile))
        dataset = pd.read_csv(csvfile)
        datasets.append(dataset)
    return datasets

def clean_data(dataframe, n_round: int = 2):
    df = dataframe.copy(deep=True)
    df = df.round(n_round)
    df = df.drop_duplicates()
    return df

def format_date(date):
    return '{}-{}-{}T{}:{}:{}'.format(date.day, date.month, date.year, date.hour, date.minute, date.second)

def create_dir(path: str):
    import os
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        print ('Creation of the directory %s failed' % path)
        return False
    else:
        print ('Successfully created the directory %s ' % path)
        return True

def save(filename: str, payload):
    import joblib
    joblib.dump(payload, filename)

def load(filename: str):
    import joblib
    return joblib.load(filename)
