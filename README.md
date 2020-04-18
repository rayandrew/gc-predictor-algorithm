# GC Predictor Algorithm

## Requirements

### Barebones

- Python 3
- Python packages, can be installed with

``` shell
pip install -r requirements.txt
```

### Using Nix?

``` shell
nix-shell
```

## Configuration

### Parse

``` json
// example: parse.json

{
  "name": "benchmarks",
  "dir": {
    "data": "./data",
    "output": "./output"
  },
  "data": [
        {
      "name": "1T-16MB-1",
      "file": "./raw_data/randomize/1T-16MB/1/ucare.log",
      "old_format": true
    },
    {
      "name": "3_30006",
      "file": "./raw_data/stringtable/3_30006/ucare.log",
      "old_format": true
    },
    {
      "name": "3_120026",
      "file": "./raw_data/stringtable/3_120026/ucare.log",
      "old_format": true
    },
    {
      "name": "renaissance",
      "file": "./raw_data/benchmarks/renaissance/ucare.log"
    },
    {
      "name": "dacapo",
      "file": "./raw_data/benchmarks/dacapo/ucare.log"
    },
    {
      "name": "specjvm",
      "file": "./raw_data/benchmarks/specjvm/ucare.log"
    }
  ]
}
```

- `old_format` key is for backward compatibility with old version of `ucare.log`

### Training

``` json
// example: training.json

{
  "name": "benchmarks",
  "skip_value": 7,
  "sm_add_constant": false,
  "dir": {
    "data": "./data/benchmarks",
    "output": "./output"
  },
  "models": [
    "ransac",
    "lreg"
  ],
  "subtitle": "",
  "data": {
    "main": [
      "1T-16MB-1",
      "..."
    ],
    "stringtable": [
      "1",
      "..."
    ]
  }
}
```

- `models` key can be `ransac`, `lreg`, and `svr`
- `data` consists of two key which entries will be prepended by `dir/data` key :
  - `main`
  - `stringtable`

### Inference

``` json
// example: inference.json

{
  "name": "benchmarks",
  "skip_value": 0,
  "sm_add_constant": false,
  "dir": {
    "data": "./data/benchmarks",
    "output": "./output"
  },
  "model": {
    "main": {
      "name": "ransac",
      "file": "./output/benchmarks/train/main/model/ransac.joblib"
    },
    "stringtable": {
      "name": "ransac",
      "file": "./output/benchmarks/train/stringtable/model/ransac.joblib"
    }
  },
  "combined_plot": {
    "max": 500,
    "min": -500,
    "subtitle": "Heap Size 4G"
  },
  "data": [
    {
      "name": "renaissance",
      "color": "green",
      "label": "Renaissance",
      "subtitle": ""
    },
    {
      "name": "dacapo",
      "color": "blue",
      "label": "DaCapo",
      "subtitle": ""
    },
    {
      "name": "specjvm",
      "color": "red",
      "label": "Specjvm2008",
      "subtitle": ""
    }
  ]
}
```

### Notes

- `dir_output` will be appended with `name` key

> the output dir will be `${dir_output}/${name}`

- `skip_value` is number of value that will be skipped in cdf plot (in case of anomaly)


## Running

### Parse

``` shell
python parse.py -c <parse.json>
```

### Train

``` shell
python train.py \
    -c <train.json> -t [main|stringtable]
    
# equals with

python train.py \
    --config <train.json> --type [main|stringtable]
```

### Inference

``` shell
python inference.py -c <inference.json>
```

## Authors

- Ray Andrew
- Cesar Stuardo
