import json
import jsonschema

from enum import Enum

class Task(Enum):
    train = 'train'
    parse = 'parse'
    inference = 'inference'

    def __str__(self):
        return self.value

class TrainType(Enum):
    nmethod = 'nmethod'
    srt = 'srt'
    trt = 'trt'
    steal = 'steal'
    barrier = 'barrier'
    idle = 'idle'
    otyrt = 'otyrt'
    references = 'references'
    stringtable = 'stringtable'
    prune = 'prune'

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
                    'parallel': { 'type': 'boolean' }
                },
                'required': ['name', 'file'],
            },
            'minItems': 1,
        }
        parse_config_schema = {
            'name': {'type' : 'string'},
            'data': parse_data_schema,
        }
        return parse_config_schema

    def generate_train_schema():
        data_schema = {
            'type': 'array',
            'items': {
                'anyOf': [
                    {
                        'type': 'string',
                    },
                    {
                        'type': 'object',
                        'properties': {
                            'name': { 'type': 'string' },
                            'query': { 'type': 'string' },
                        },
                        'required': ['name'],
                    }
                ],
            },
            'minItems': 1,
        }

        train_config_schema =  {
            'type' : 'object',
            'properties' : {
                'name': {'type' : 'string'},
                'skip_value' : {'type' : 'number'},
                'sm_add_constant' : {'type' : 'boolean'},
                'data_dir': {'type' : 'string'},
                'subtitle': {'type' : 'string'},
                'parallel': { 'type': 'boolean' },
                'models': {
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'enum': ['ransac', 'lreg', 'svr', 'sm']
                    },
                    'minItems': 1,
                    'maxItems': 3,
                    'additionalItems': False,
                },
                'data': {
                    'type': 'object',
                    'properties': {
                        'srt': data_schema,
                        'trt': data_schema,
                        'otyrt': data_schema,
                        'references': data_schema,
                        'stringtable': data_schema,
                        'prune': data_schema,
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
                'sm_add_constant' : {'type' : 'boolean'},
            },
            'required': ['name', 'file'],
        }

        inference_config_schema = {
            'name': {'type' : 'string'},
            'skip_value' : {'type' : 'number'},
            'data_dir': {'type' : 'string'},
            'subtitle': {'type' : 'string'},
            'parallel': { 'type': 'boolean' },
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

def load_config(path: str, task: Task = Task.parse):
    with open(path) as f:
        config = json.load(f)
        jsonschema.validate(config, generate_schema(task))
        return config
