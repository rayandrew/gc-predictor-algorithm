import sys
import os
import csv
import re
import json

from tqdm import tqdm

import utilities

HEAP_REGEX='(.*?)total(.*?), used(.[A-Za-z0-9_*-]*)'

CSV_COL = [
    # general info
    'gc_id',
    'allocation_size',
    'phases',

    # Oops
    'young_gen_live_objects',
    'young_gen_dead_objects',
    'young_gen_total_objects',
    'young_gen_roots_walk_elapsed',

    'old_gen_live_objects',
    'old_gen_dead_objects',
    'old_gen_total_objects',
    'old_gen_roots_walk_elapsed',

    # Heap
    'young_gen_heap_capacity',
    'young_gen_heap_used',
    'young_gen_heap_free',

    'old_gen_heap_capacity',
    'old_gen_heap_used',
    'old_gen_heap_free',

    # stringtable
    'stringtable_size',
    'stringtable_processed',
    'stringtable_removed',

    # prune
    'prune_nmethod_pointer_count',

    # gen time
    'young_gen_gc_time',
    'old_gen_gc_time',

    # time
    'stringtable_time',
    'prune_nmethod_time',
    'gc_time_clean',
    'gc_time',
]

def skip_prestr(line: str, prestr: str):
    first_index_of_prestr = line.find(prestr)
    last_index_of_prestr = first_index_of_prestr + len(prestr)
    return line[last_index_of_prestr:]

def convert_time(line: str):
    time = 0.0
    if 'ms' in line:
        time = float(line[:-2]) * 1
    elif 's' in line:
        time = float(line[:-1]) * 1000
    return round(time, 3)

def convert_size(line: str):
    size = float(line[:-1])
    unit = line[-1]
    if unit == 'K':
        size = size * 1.0
    elif unit == 'B':
        size = size / 1000.0
    return round(size, 3)

def parse_line_summaries(line: str):
    new_line = line.replace(',', '')
    infos = new_line.split()[3:]
    result = {}
    for info in infos:
        temp = {}
        # only contains two elements if splitted
        key, value, *rest = info.split('=')
        assert(len(rest) == 0)
        value = value.replace(']', '')
        if (key == 'elapsed'):
            result[key] = convert_time(value)
        else:
            try:
                result[key] = float(value)
            except:
                result[key] = value
    return result

def parse_gc_id(line: str, prestr: str):
    gc_id_str = skip_prestr(line, prestr).rstrip(']\n')
    gc_id = int(gc_id_str)
    return gc_id

def parse_heap(line: str):
    heap_str = line.replace(',', '')
    heap_infos = heap_str.split()[3:]
    result = {}
    for info in heap_infos:
        # only contains two elements if splitted
        key, value, *rest = info.split('=')
        assert(len(rest) == 0)
        value = value.replace(']', '')
        result[key] = convert_size(value)
    return result

def parse_gc_time(line: str, prestr = 'GC Time'):
    gc_time_str = skip_prestr(line, prestr).rstrip(']\n')
    if ('secs' in gc_time_str):
        gc_time_str = gc_time_str.replace('secs', 's')
    gc_time_str = gc_time_str.replace(' ', '')
    gc_time_str = gc_time_str.split(',')
    assert(len(gc_time_str) == 2)
    gc_time = convert_time(gc_time_str[1])
    return gc_time

def parse_allocation_size(line: str):
    prestr = 'Mem allocate size'
    alloc_size_str = skip_prestr(line, prestr).rstrip(']\n')
    if 'bytes' in alloc_size_str:
        alloc_size_str = alloc_size_str.replace('bytes', 'B')
    alloc_size_str = alloc_size_str.replace(' ', '')
    alloc_size = convert_size(alloc_size_str)
    return alloc_size

def parse_phases(line: str):
    prestr = '{'
    phases_str = skip_prestr(line, prestr).rstrip('} ')
    phases = ';'.join(phases_str.split(' ')[1:-2])
    return phases

def parse_trace_time(line: str, prestr: str):
    gc_time = prestr in 'GC Time'
    time_str = skip_prestr(line, prestr).rstrip(']\n')
    if ('secs' in time_str):
        time_str = time_str.replace('secs', 's')
    time_str = time_str.replace(' ', '')
    time = 0.0
    if gc_time:
        time_str = time_str.split(',')
        assert(len(time_str) == 2)
        time = convert_time(time_str[1])
    else:
        time = convert_time(time_str)
    return time

def parse_stringtable_info(line: str):
    prestr = 'StringTableInfo'
    info_str = skip_prestr(line, prestr).rstrip(']\n')
    info_str = info_str.replace(',', '')
    infos = info_str.split()
    result = {}
    for info in infos:
        # only contains two elements if splitted
        key, value, *rest = info.split('=')
        assert(len(rest) == 0)
        value = value.replace(']', '')
        if (key == 'elapsed'):
            result[key] = convert_time(value)
        else:
            try:
                result[key] = float(value)
            except:
                result[key] = value
    return result

def parse_prune_nmethod_pointer(line: str):
    prestr = 'PruneScavengeRootNmethods'
    prune_str = skip_prestr(line, prestr).rstrip(']\n')
    prune_str = prune_str.replace(',', '').strip()
    prune = int(prune_str)
    return prune

def parse(filename, output, old_format: bool = False):
    with open(filename) as log_file:
        with open(output, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(CSV_COL)
            
            line = log_file.readline()

            start_gc_id = -99
            end_gc_id = -100

            gc_time = 0.0
            allocation_size = 0.0
            phases = None

            need_full_gc = 0

            old_gen_summary = None
            old_gen_gc_time = 0.0
            old_gen_heap = None

            young_gen_summary = None
            young_gen_gc_time = 0.0
            young_gen_heap = None

            stringtable_time = 0.0
            stringtable_info = None

            prune_pointer_count = 0
            prune_time = 0.0

            post_scavenge_time = 0.0
            after_post_scavenge_time = 0.0

            start_of_gc = False
            end_of_gc = False

            while line:
                # [YoungGen size, capacity=1388314624B used=1372782672B free=1000B]

                if not start_of_gc and 'GC Start' in line:
                    start_of_gc = True
                    end_of_gc = False
                    start_gc_id = parse_gc_id(line, 'GC Start id=')

                if start_of_gc and not end_of_gc:
                    if 'GC Finish' in line:
                        end_gc_id = parse_gc_id(line, 'GC Finish id=')
                        if end_gc_id == start_gc_id:
                            end_of_gc = True
                            start_of_gc = False
                    elif 'GC Time' in line:
                        gc_time = parse_trace_time(line, 'GC Time')
                    elif 'OldGenTime' in line:
                        old_gen_gc_time = parse_gc_time(line, 'OldGenTime')
                    elif 'YoungGenTime' in line:
                        young_gen_gc_time = parse_gc_time(line, 'YoungGenTime')
                    elif 'Mem allocate size' in line:
                        allocation_size = parse_allocation_size(line)
                    elif 'Phase gc_id' in line:
                        phases = parse_phases(line)
                    elif 'StringTableTime' in line:
                        stringtable_time = parse_trace_time(line, 'StringTableTime],' if old_format else 'StringTableTime,')
                    elif 'StringTableInfo' in line:
                        stringtable_info = parse_stringtable_info(line)
                    elif 'TraceCountRootOopClosureContainer: context=YoungGen' in line:
                        young_gen_summary = parse_line_summaries(line)
                    elif 'TraceCountRootOopClosureContainer: context=OldGen' in line:
                        old_gen_summary = parse_line_summaries(line)
                    elif 'YoungGen size' in line:
                        young_gen_heap = parse_heap(line)
                    elif 'OldGen size' in line:
                        old_gen_heap = parse_heap(line)
                    elif 'PruneScavengeRootNmethods' in line:
                        prune_pointer_count = parse_prune_nmethod_pointer(line)
                    elif 'PruneScavenge' in line:
                        prune_time = parse_trace_time(line, 'PruneScavenge,')

                line = log_file.readline()

                if end_of_gc:
                    end_of_gc = False
                    if young_gen_summary is None:
                        young_gen_summary = {
                            'live_objects': 0,
                            'dead_objects': 0,
                            'total_objects': 0,
                            'elapsed': 0.0,
                        }
                    if old_gen_summary is None:
                        old_gen_summary = {
                            'live_objects': 0.0,
                            'dead_objects': 0.0,
                            'total_objects': 0.0,
                            'elapsed': 0.0,
                        }
                    if stringtable_info is None:
                        stringtable_info = {
                            'table_size': 0.0,
                            'processed': 0.0,
                            'removed': 0.0,
                        }
                    if young_gen_heap is None:
                        young_gen_heap = {
                            'capacity': 0.0,
                            'used': 0.0,
                            'free': 0.0,
                        }
                    if old_gen_heap is None:
                        old_gen_heap = {
                            'capacity': 0.0,
                            'used': 0.0,
                            'free': 0.0,
                        }

                    writer.writerow([
                        start_gc_id,
                        allocation_size,
                        phases,

                        # Oops
                        young_gen_summary['live_objects'],
                        young_gen_summary['dead_objects'],
                        young_gen_summary['total_objects'],
                        young_gen_summary['elapsed'],

                        old_gen_summary['live_objects'],
                        old_gen_summary['dead_objects'],
                        old_gen_summary['total_objects'],
                        old_gen_summary['elapsed'],

                        # Heap
                        young_gen_heap['capacity'],
                        young_gen_heap['used'],
                        young_gen_heap['free'],

                        old_gen_heap['capacity'],
                        old_gen_heap['used'],
                        old_gen_heap['free'],

                        # Stringtable
                        stringtable_info['table_size'],
                        stringtable_info['processed'],
                        stringtable_info['removed'],

                        # Prune
                        prune_pointer_count,

                        # Gen time
                        young_gen_gc_time,
                        old_gen_gc_time,

                        # Time
                        stringtable_time,
                        prune_time,
                        gc_time - stringtable_time - prune_time,
                        gc_time,
                    ])

            csv_file.close()
        log_file.close()

def main(args):
    print('Reading config')
    config = utilities.read_json_config(args.config, utilities.Task.parse)
    print('Starting parsing...')
    output_dir = '{}/{}'.format(config['dir']['data'], config['name'])
    print('Creating data directory {}'.format(output_dir))
    utilities.create_dir(output_dir)
    print('Reading raw data...')
    threads = []
    pbar = tqdm(range(len(config['data'])))
    for index in pbar:
        infile = config['data'][index]['file']
        outfile = '{}/{}.csv'.format(output_dir, config['data'][index]['name'])
        pbar.set_description('Processing raw_data in={} out={}'.format(infile, outfile))
        parse(infile, outfile, config['data'][index]['old_format'] if 'old_format' in config['data'][index] else False)

if __name__ == '__main__':
    import time
    start_time = time.time()
    main(utilities.get_args())
    print("--- %s seconds ---" % (time.time() - start_time))
    # Threads: --- 71.97676062583923 seconds ---
    # No Thread : --- 64.11785078048706 seconds ---
