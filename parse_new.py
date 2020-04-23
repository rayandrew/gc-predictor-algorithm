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
    'total_young_gen_heap',
    'used_young_gen_heap',
    'free_young_gen_heap',

    'total_old_gen_heap',
    'used_old_gen_heap',
    'free_old_gen_heap',

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
    infos = new_line.split()[1:]
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

def parse_heap_size(line: str):
    total = 0.0
    used = 0.0
    result = re.search(HEAP_REGEX, line)
    if result:
        total = convert_size(result[2])
        used = convert_size(result[3])
    return (total, used)

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
    prestr = '['
    phases_str = skip_prestr(line, prestr).rstrip(']\n')
    phases = ';'.join(phases_str.split(' ')[:-1])
    return phases

def parse_stringtable_time(line: str, old_format: bool = False):
    prestr = 'StringTableTime],' if old_format else 'StringTableTime,'
    time_str = skip_prestr(line, prestr).rstrip(']\n')
    if ('secs' in time_str):
        time_str = time_str.replace('secs', 's')
    time_str = time_str.replace(' ', '')
    time = convert_time(time_str)
    return time

def parse_stringtable_info(line: str):
    prestr = 'StringTableInfo'
    info_str = skip_prestr(line, prestr).rstrip(']\n')
    info_str = info_str.replace(',', '')
    infos = info_str.split()
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
    

def parse(filename, output, old_format: bool = False):
    with open(filename) as log_file:
        with open(output, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(CSV_COL)
            
            line = log_file.readline()

            write_summary = None
            last_summary = None
            summary = None
            old_gen_summary = None
            young_gen_summary = None
            young_gen = None
            old_gen = None
            gc_time = 0.0
            old_gen_gc_time = 0.0
            young_gen_gc_time = 0.0
            allocation_size = 0.0
            start_of_gc = False
            write_csv_row = False
            stringtable_time = 0.0
            stringtable_info = None

            start = False

            count = 0
            
            while line:
                if line.startswith('  summaries: context=OldGen'):
                    old_gen_summary = parse_line_summaries(line)
                elif line.startswith('  summaries: context=YoungGen'):
                    young_gen_summary = parse_line_summaries(line)            
                elif line.startswith('  summaries:'):
                    summary = parse_line_summaries(line)
                    count += 1
                else:
                    summary = None

                if line.startswith(' PSYoungGen'):
                    young_gen = parse_heap_size(line)
                elif line.startswith(' ParOldGen'):
                    old_gen = parse_heap_size(line)
                elif 'GC Time' in line:
                    gc_time = parse_gc_time(line)
                elif 'OldGenTime' in line and start:
                    old_gen_gc_time = parse_gc_time(line, 'OldGenTime')
                elif 'YoungGenTime' in line and start:
                    young_gen_gc_time = parse_gc_time(line, 'YoungGenTime')
                elif 'Mem allocate size' in line and start:
                    allocation_size = parse_allocation_size(line)
                # elif 'phase gc_id' in line and start:
                #     phases = parse_phases(line)
                elif 'StringTableTime' in line and start:
                    stringtable_time = parse_stringtable_time(line, old_format)
                elif 'StringTableInfo' in line and start:
                    stringtable_info = parse_stringtable_info(line)

                line = log_file.readline()

                # if summary and summary['context'] == 'AfterGC':
                #     if last_summary:
                #         print('LAST_SUM', last_summary['gc_id'])
                #     print('SUM', summary['gc_id'])

                if summary is not None:
                    if last_summary is not None:
                        if summary['context'] == 'AfterGC':
                        # if summary['gc_id'] != last_summary['gc_id']:
                            write_summary = last_summary
                            write_csv_row = True
                            start = False
                    if summary['context'] == 'BeforeGC':
                        start = True
                        last_summary = summary
                        write_csv_row = False
                        # write_csv_row = False

                # if write_summary:
                #     print('WRITE', write_summary['gc_id'])

                if write_csv_row and write_summary is not None:
                    write_csv_row = False
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
                    writer.writerow([
                        write_summary['gc_id'],
                        write_summary['live_objects'],
                        write_summary['dead_objects'],
                        write_summary['total_objects'],
                        write_summary['elapsed'],
                        allocation_size,
                        young_gen_summary['live_objects'],
                        young_gen_summary['dead_objects'],
                        young_gen_summary['total_objects'],
                        young_gen_summary['elapsed'],
                        young_gen[0],
                        young_gen[1],
                        old_gen_summary['live_objects'],
                        old_gen_summary['dead_objects'],
                        old_gen_summary['total_objects'],
                        old_gen_summary['elapsed'],
                        old_gen[0],
                        old_gen[1],
                        # phases,
                        stringtable_info['table_size'],
                        stringtable_info['processed'],
                        stringtable_info['removed'],
                        stringtable_time,
                        young_gen_gc_time,
                        old_gen_gc_time,
                        gc_time,
                        gc_time - stringtable_time,
                    ])
                    summary = None
                    write_summary = None
                    last_summary = None
                    write_summary = None
                    last_summary = None
                    summary = None
                    old_gen_summary = None
                    young_gen_summary = None
                    young_gen = None
                    old_gen = None
                    gc_time = 0.0
                    old_gen_gc_time = 0.0
                    young_gen_gc_time = 0.0
                    allocation_size = 0.0
                    start_of_gc = False
                    write_csv_row = False
                    # phases = None
                    stringtable_time = 0.0
                    stringtable_info = None

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
