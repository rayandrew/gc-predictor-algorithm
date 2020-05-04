from typing import Union
import pandas as pd
from sklearn.pipeline import Pipeline, make_pipeline, FeatureUnion

from gcpredictor.transformers import ColumnSelector, \
    Identity, PandasQuery, PandasFeatureUnion
import gcpredictor.utilities as utilities

SRT_COL = [
    'srt_total',
    'srt_elapsed',
]

TRT_COL = [
    'trt_total',
    'trt_elapsed',
]

OTYRT_COL = [
    'otyrt_card_increment_counter',
    'otyrt_elapsed',
]

NMETHOD_COL = [
    'nmethod_epilogue_count',
    'nmethod_epilogue_elapsed',
]

STEAL_COL = [
    'steal_stack_depth_counter',
    'steal_elapsed',
]

BARRIER_COL = [
    'barrier_busy_workers',
    'barrier_elapsed',
]

REFERENCES_COL = [
    'ref_soft_count',
    'ref_weak_count',
    'ref_final_count',
    'ref_phantom_count',
    'ref_total_elapsed',
]

STRINGTABLE_COL = [
    'stringtable_size',
    'stringtable_elapsed',
]

PRUNE_COL = [
    'prune_nmethod_pointer_count',
    'prune_elapsed',
]

TARGET_COL = [
    'gc_time',
]

def remove_last_col(col: [str]):
    return col[:-1]

def get_inference_preprocess_pipeline():
    preprocess_pipeline = make_pipeline(
        PandasQuery('need_full_gc == False'),
        PandasFeatureUnion([
            ("gc_id", make_pipeline(
                ColumnSelector(columns=['gc_id']),
                Identity(),
            )),
            ("nmethod", make_pipeline(
                ColumnSelector(columns=remove_last_col(NMETHOD_COL)),
                Identity(),
            )),
            ("srt", make_pipeline(
                ColumnSelector(columns=remove_last_col(SRT_COL)),
                Identity(),
            )),
            ("trt", make_pipeline(
                ColumnSelector(columns=remove_last_col(TRT_COL)),
                Identity(),
            )),
            ("otyrt", make_pipeline(
                ColumnSelector(columns=remove_last_col(OTYRT_COL)),
                Identity(),
            )),
            ("steal", make_pipeline(
                ColumnSelector(columns=remove_last_col(STEAL_COL)),
                Identity(),
            )),
            ("barrier", make_pipeline(
                ColumnSelector(columns=remove_last_col(BARRIER_COL)),
                Identity(),
            )),
            # ("idle", make_pipeline(
            #     ColumnSelector(columns=remove_last_col(IDLE_COL)),
            #     Identity(),
            # )),
            ("stringtable", make_pipeline(
                ColumnSelector(columns=remove_last_col(STRINGTABLE_COL)),
                Identity(),
            )),
            ("references", make_pipeline(
                ColumnSelector(columns=remove_last_col(REFERENCES_COL)),
                Identity(),
            )),
            ("prune", make_pipeline(
                ColumnSelector(columns=remove_last_col(PRUNE_COL)),
                Identity(),
            )),
            ("need_full_gc", make_pipeline(
                ColumnSelector(columns=['need_full_gc']),
                Identity(),
            )),
            ("target", make_pipeline(
                ColumnSelector(columns=TARGET_COL),
                Identity(),
            )),
        ]),
    )
    return preprocess_pipeline

def get_train_preprocess_pipeline(train_type: str, query: Union[str, None] = None):
    specific_data_pipeline = []
    target_col = []

    if train_type == 'nmethod':
        target_col = NMETHOD_COL[-1]
        specific_data_pipeline = [
            ("nmethod", make_pipeline(
                ColumnSelector(columns=remove_last_col(NMETHOD_COL)),
                Identity(),
            )),
        ]
    elif train_type == 'srt':
        target_col = SRT_COL[-1]
        specific_data_pipeline = [
            ("srt", make_pipeline(
                ColumnSelector(columns=remove_last_col(SRT_COL)),
                Identity(),
            )),
        ]
    elif train_type == 'trt':
        target_col = SRT_COL[-1]
        specific_data_pipeline = [
            ("trt", make_pipeline(
                ColumnSelector(columns=remove_last_col(TRT_COL)),
                Identity(),
            )),
        ]
    elif train_type == 'steal':
        target_col = STEAL_COL[-1]
        specific_data_pipeline = [
            ("steal", make_pipeline(
                ColumnSelector(columns=remove_last_col(STEAL_COL)),
                Identity(),
            )),
        ]
    elif train_type == 'barrier':
        target_col = BARRIER_COL[-1]
        specific_data_pipeline = [
            ("barrier", make_pipeline(
                ColumnSelector(columns=remove_last_col(BARRIER_COL)),
                Identity(),
            )),
        ]
    elif train_type == 'idle':
        target_col = IDLE_COL[-1]
        specific_data_pipeline = [
            ("idle", make_pipeline(
                ColumnSelector(columns=remove_last_col(IDLE_COL)),
                Identity(),
            )),
        ]
    elif train_type == 'otyrt':
        target_col = OTYRT_COL[-1]
        specific_data_pipeline = [
            ("otyrt", make_pipeline(
                ColumnSelector(columns=remove_last_col(OTYRT_COL)),
                Identity(),
            )),
        ]
    elif train_type == 'stringtable':
        target_col = STRINGTABLE_COL[-1]
        specific_data_pipeline = [
            ("stringtable", make_pipeline(
                ColumnSelector(columns=remove_last_col(STRINGTABLE_COL)),
                Identity(),
            )),
        ]
    elif train_type == 'references':
        target_col = REFERENCES_COL[-1]
        specific_data_pipeline = [
            ("references", make_pipeline(
                ColumnSelector(columns=remove_last_col(REFERENCES_COL)),
                Identity(),
            )),
        ]
    elif train_type == 'prune':
        target_col = PRUNE_COL[-1]
        specific_data_pipeline = [
            ("prune", make_pipeline(
                ColumnSelector(columns=remove_last_col(PRUNE_COL)),
                Identity(),
            )),
        ]

    preprocess_pipeline = make_pipeline(
        PandasQuery(query),
        PandasFeatureUnion([
            *specific_data_pipeline,
            ("target", make_pipeline(
                ColumnSelector(columns=target_col),
                Identity(),
            )),
        ]),
    )
    return preprocess_pipeline

def prepare_train_dataset(config: dict, train_type: str):
    print('Reading data')
    raw_dataset = utilities.read_data([
        '{}/{}'.format(
            config['data_dir'],
            data['name'] if isinstance(data, dict) else data,
        ) for data in config['data'][train_type]
    ])

    processed_dataset = []
    for idx in range(len(raw_dataset)):
        dataset = raw_dataset[idx]
        query = None
        if isinstance(config['data'][train_type][idx], dict):
            if 'query' in config['data'][train_type][idx]:
                query = config['data'][train_type][idx]['query']
        pipeline = get_train_preprocess_pipeline(train_type, query)
        dataset = pipeline.transform(dataset)
        processed_dataset.append(dataset)

    dataset = pd.concat(processed_dataset)

    return raw_dataset, dataset

def prepare_inference_dataset(config: dict):
    print('Reading data')
    raw_dataset = utilities.read_data([
        '{}/{}'.format(
            config['data_dir'],
            data['name'],
        ) for data in config['data']
    ])

    pipeline = get_inference_preprocess_pipeline()
    datasets = [pipeline.transform(dataset) for dataset in raw_dataset]
    return datasets
