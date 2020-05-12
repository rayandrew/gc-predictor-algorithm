import sys
import os
import csv
import re
import json

from tqdm import tqdm

from gcpredictor.config import load_config, Task
import gcpredictor.utilities as utilities

# TODO this is pretty bulky

class Parser(object):
    def __init__(self):
        self.CSV_COL = [
            # general info
            'gc_id',
            'allocation_size',
            'phases',
            'parallel_workers',
            'need_full_gc',
            'total_threads', # includes java threads
           
            # nmethod
            'nmethod_epilogue_count',
            'nmethod_epilogue_elapsed',

            # tasks
            ## srt
            'srt_live',
            'srt_dead',
            'srt_total',
            'srt_stack_depth_counter',
            'srt_elapsed',

            ## trt
            'trt_live',
            'trt_dead',
            'trt_total',
            'trt_stack_depth_counter',
            'trt_elapsed',

            ## otyrt
            'otyrt_stripe_num',
            'otyrt_stripe_total',
            'otyrt_slice_width',
            'otyrt_slice_counter',
            'otyrt_dirty_card_counter',
            'otyrt_objects_scanned_counter',
            'otyrt_card_increment_counter',
            'otyrt_total_max_card_pointer_being_walked_through',
            'otyrt_stack_depth_counter',
            'otyrt_elapsed',

            ## steal
            'steal_stack_depth_counter',
            'steal_elapsed',

            ## barrier
            'barrier_busy_workers',
            'barrier_elapsed',

            ## idle
            'idle_elapsed',

            # references,
            'ref_soft_count',
            'ref_soft_elapsed',
            'ref_weak_count',
            'ref_weak_elapsed',
            'ref_final_count',
            'ref_final_elapsed',
            'ref_phantom_count',
            'ref_phantom_elapsed',
            'ref_total_elapsed',

            # stringtable
            'stringtable_size',
            'stringtable_processed',
            'stringtable_removed',
            'stringtable_elapsed',

            # prune
            'prune_nmethod_pointer_count',
            'prune_elapsed',

            # Heap
            'young_gen_heap_capacity',
            'young_gen_heap_used',
            'young_gen_heap_free',

            'old_gen_heap_capacity',
            'old_gen_heap_used',
            'old_gen_heap_free',

            # local stats (most prominent)
            'masked_pushes',
            'masked_steals',
            'arrays_chunked',
            'array_chunks_processed',
            'copied',
            'tenured',
            'worker_sum_copied',
            'worker_total_tenured',
            'estimated_copied',
            'estimated_tenured',
            'total_estimated_copied',
            'total_estimated_tenured',

            # task queue stats (most prominent)
            'qpush',
            'qpop',
            'qpops',
            'qattempt',
            'qsteal',
            'opush',
            'omax',

            # parallel task terminator
            'ptt_yields',
            'ptt_spins',
            'ptt_peeks',

            # parallel task terminator global
            'ptt_global_yields',
            'ptt_global_spins',
            'ptt_global_peeks',

            # ps promotion info
            'copy_rate',
            'tenure_rate',
            'current_gc_copied',
            'current_gc_tenured',
            'global_total_copied',
            'global_total_tenured',

            # gen time
            'young_gen_gc_time',
            'old_gen_gc_time',
            'scavenge_time',

            'gc_time_clean',
            'gc_time',
        ]

    def skip_prestr(self, line: str, prestr: str):
        first_index_of_prestr = line.find(prestr)
        last_index_of_prestr = first_index_of_prestr + len(prestr)
        return line[last_index_of_prestr:]

    def convert_time(self, line: str):
        time = 0.0
        if 'ms' in line:
            time = float(line[:-2]) * 1
        elif 'us' in line:
            time = float(line[:-2]) / 1000
        elif 's' in line:
            time = float(line[:-1]) * 1000
        return time

    def convert_size(self, line: str):
        size = float(line[:-1])
        unit = line[-1]
        if unit == 'K':
            size = size * 1.0
        elif unit == 'B':
            size = size / 1000.0
        return size

    def parse_line_summaries(self, line: str, skip_num: int):
        new_line = line.replace(',', '')
        infos = new_line.split()[skip_num:]
        result = {}
        for info in infos:
            if '=' not in info:
                continue
            # only contains two elements if splitted
            key, value, *rest = info.split('=')
            assert(len(rest) == 0)
            value = value.replace(']', '')
            if key == 'elapsed' \
               or key == 'elapsed_time' \
               or 'elapsed' in key \
               or 'time' in key \
               or 'estimated' in key:
                result[key] = self.convert_time(value)
            else:
                try:
                    result[key] = float(value)
                except:
                    result[key] = value
        return result

    def parse_gc_id(self, line: str, prestr: str):
        gc_id_str = self.skip_prestr(line, prestr).rstrip(']\n')
        gc_id = int(gc_id_str)
        return gc_id

    def parse_heap(self, line: str):
        heap_str = line.replace(',', '')
        heap_infos = heap_str.split()[3:]
        result = {}
        for info in heap_infos:
            # only contains two elements if splitted
            key, value, *rest = info.split('=')
            assert(len(rest) == 0)
            value = value.replace(']', '')
            result[key] = self.convert_size(value)
        return result

    def parse_allocation_size(self, line: str):
        prestr = 'Mem allocate size'
        alloc_size_str = self.skip_prestr(line, prestr).rstrip(']\n')
        if 'bytes' in alloc_size_str:
            alloc_size_str = alloc_size_str.replace('bytes', 'B')
        alloc_size_str = alloc_size_str.replace(' ', '')
        alloc_size = self.convert_size(alloc_size_str)
        return alloc_size

    def parse_phases(self, line: str):
        prestr = '{'
        phases_str = self.skip_prestr(line, prestr).rstrip('} ')
        phases = ';'.join(phases_str.split(' ')[1:-2])
        return phases

    def parse_trace_time(self, line: str, prestr: str):
        gc_time = prestr in 'GC Time'
        time_str = self.skip_prestr(line, prestr).rstrip(']\n')
        if ('secs' in time_str):
            time_str = time_str.replace('secs', 's')
        time_str = time_str.replace(' ', '').lstrip(',')
        if gc_time:
            time_str = time_str.split(',')[1]
        time = self.convert_time(time_str)
        return time

    def parse_stringtable_info(self, line: str):
        prestr = 'StringTableInfo'
        info_str = self.skip_prestr(line, prestr).rstrip(']\n')
        info_str = info_str.replace(',', '')
        infos = info_str.split()
        result = {}
        for info in infos:
            # only contains two elements if splitted
            key, value, *rest = info.split('=')
            assert(len(rest) == 0)
            value = value.replace(']', '')
            if key == 'elapsed':
                result[key] = self.convert_time(value)
            else:
                try:
                    result[key] = float(value)
                except:
                    result[key] = value
        return result

    def parse_number(self, line: str, prestr: str):
        # prestr = 'PruneScavengeRootNmethods'
        number_str = self.skip_prestr(line, prestr).rstrip(']\n')
        number_str = number_str.replace(',', '').strip()
        number = int(number_str)
        return number

    def check_worker(self, worker: dict):
        elapsed = 0.0

        for task in worker['tasks']:
            elapsed += task['elapsed']

        assert elapsed == worker['elapsed_time']

    def process_choosen_worker(self, worker: dict):
        result = {
            'srt': {
                'live': 0,
                'dead': 0,
                'total': 0,
                'stack_depth_counter': 0,
                'elapsed': 0.0,
            },
            'trt': {
                'live': 0,
                'dead': 0,
                'total': 0,
                'stack_depth_counter': 0,
                'elapsed': 0.0,
            },
            'steal': {
                'stack_depth_counter': 0,
                'elapsed': 0.0,
            },
            'barrier': {
                'busy_workers': 0,
                'elapsed': 0.0,
            },
            'otyrt': {
                'stripe_num': 0,
                'stripe_total': 0,
                'slice_width': 0,
                'slice_counter': 0,
                'dirty_card_counter': 0,
                'objects_scanned_counter': 0,
                'card_increment_counter': 0,
                'total_max_card_pointer_being_walked_through': 0,
                'stack_depth_counter': 0,
                'elapsed': 0.0,
            },
            'idle': {
                'elapsed': 0.0,
            }
        }

        for task in worker['tasks']:
            if task['type'] == 'SRT':
                result['srt']['live'] += task['live']
                result['srt']['dead'] += task['dead']
                result['srt']['total'] += task['total']
                result['srt']['stack_depth_counter'] += task['stack_depth_counter']
                result['srt']['elapsed'] += task['elapsed']
            elif task['type'] == 'TRT':
                result['trt']['live'] += task['live']
                result['trt']['dead'] += task['dead']
                result['trt']['total'] += task['total']
                result['trt']['stack_depth_counter'] += task['stack_depth_counter']
                result['trt']['elapsed'] += task['elapsed']
            elif task['type'] == 'OTYRT':
                result['otyrt']['stripe_num'] += task['stripe_num']
                result['otyrt']['stripe_total'] += task['stripe_total']
                result['otyrt']['slice_width'] += task['slice_width']
                result['otyrt']['slice_counter'] += task['slice_counter']
                result['otyrt']['dirty_card_counter'] += task['dirty_card_counter']
                result['otyrt']['objects_scanned_counter'] += task['objects_scanned_counter']
                result['otyrt']['card_increment_counter'] += task['card_increment_counter']
                result['otyrt']['total_max_card_pointer_being_walked_through'] += task['total_max_card_pointer_being_walked_through']
                result['otyrt']['stack_depth_counter'] += task['stack_depth_counter']
                result['otyrt']['elapsed'] += task['elapsed']
            elif task['type'] == 'STEAL':
                result['steal']['stack_depth_counter'] += task['stack_depth_counter']
                result['steal']['elapsed'] += task['elapsed']
            elif task['type'] == 'BARRIER':
                result['barrier']['busy_workers'] += task['busy_workers']
                result['barrier']['elapsed'] += task['elapsed']
            elif task['type'] == 'IDLE':
                result['idle']['elapsed'] += task['elapsed']
        return result

    def parse(self, filename, output, parallel: bool = False):
        gc_counter = 0
        gc_counter_parsed = 0
        with open(filename) as log_file, \
             tqdm(total=os.path.getsize(filename)) as pbar:
            with open(output, 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(self.CSV_COL)
            
                line = log_file.readline()

                start_gc_id = -99
                end_gc_id = -100

                gc_time = 0.0
                allocation_size = 0.0
                phases = None
                parallel_workers = 0

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

                old_to_young_roots_task = None

                start_of_gc = False
                end_of_gc = False

                start_of_worker = False
                end_of_worker = False

                start_of_local_stats = False
                end_of_local_stats = False

                start_of_task_queue_stats = False
                end_of_task_queue_stats = False

                references = None

                scavenge_time = 0.0

                need_full_gc = False

                nmethod = None

                worker_local_stats = []
                worker_task_queue_stats = []

                parallel_task_terminator = {}
                parallel_task_terminator_global = {}

                total_copied = 0
                total_tenured = 0

                total_threads = 0

                workers = []
                single_worker = {}

                pspromotion_info = None

                while line:
                    worker_start = re.findall(r'^\[WorkerTracker:(.*)start\]$', line)
                    # [YoungGen size, capacity=1388314624B used=1372782672B free=1000B]

                    if not start_of_gc and 'GC Start' in line:
                        start_of_gc = True
                        end_of_gc = False
                        start_gc_id = self.parse_gc_id(line, 'GC Start id=')
                        gc_counter += 1

                    if start_of_gc and not end_of_gc:
                        if 'GC Finish' in line:
                            end_gc_id = self.parse_gc_id(line, 'GC Finish id=')
                            if end_gc_id == start_gc_id:
                                end_of_gc = True
                                start_of_gc = False
                        elif 'GC Time' in line:
                            gc_time = self.parse_trace_time(line, 'GC Time')
                        elif 'OldGenTime' in line:
                            old_gen_gc_time = self.parse_trace_time(line, 'OldGenTime')
                        elif 'YoungGenTime' in line:
                            young_gen_gc_time = self.parse_trace_time(line, 'YoungGenTime')
                        elif 'PreScavengeTime' in line \
                             or 'PostScavengeTime' in line \
                             or 'PruneScavengeTime' in line:
                            pass
                        elif 'ScavengeTime' in line:
                            scavenge_time = self.parse_trace_time(line, 'ScavengeTime')
                        elif 'Mem allocate size' in line:
                            allocation_size = self.parse_allocation_size(line)
                        elif 'Phase gc_id' in line:
                            phases = self.parse_phases(line)
                        elif 'GCParallelWorkers' in line:
                            parallel_workers = self.parse_number(line, 'GCParallelWorkers')
                        elif 'StringTableTime' in line:
                            stringtable_time = self.parse_trace_time(line, 'StringTableTime')
                        elif 'StringTableInfo' in line:
                            stringtable_info = self.parse_stringtable_info(line)
                        elif 'ParallelTaskTerminatorGlobal' in line:
                            parallel_task_terminator_global = self.parse_line_summaries(line, 1)
                        elif 'ParallelTaskTerminator' in line:
                            parallel_task_terminator = self.parse_line_summaries(line, 1)

                        ### TODO changed this to serial or parallel
                        elif 'TraceCountRootOopClosureContainer: context=YoungGen' in line:
                            young_gen_summary = self.parse_line_summaries(line, 3)
                        ### END of changed this
                        ### FIX above
                        elif worker_start and len(worker_start) > 0:
                            start_of_worker = True
                            end_of_worker = False
                            single_worker = {}
                        elif start_of_worker and re.search(r'^\[WorkerTracker:(.*)end\]$', line):
                            workers.append(single_worker)
                            end_of_worker = True
                            start_of_worker = False
                        ###
                        elif 'TraceCountRootOopClosureContainer: context=OldGen' in line:
                            old_gen_summary = self.parse_line_summaries(line, 3)
                        elif 'OldToYoungRootsTaskGeneralInfo' in line:
                            iterate = 0
                            success = False
                            while not success:
                                try:
                                    new_old_to_young_roots_task = self.parse_line_summaries(line, iterate)
                                    success = True
                                except:
                                    iterate += 1

                            if old_to_young_roots_task:
                                # compare elapsed
                                if old_to_young_roots_task['elapsed'] < new_old_to_young_roots_task['elapsed']:
                                    old_to_young_roots_task = new_old_to_young_roots_task
                            else:
                                old_to_young_roots_task = new_old_to_young_roots_task
                        elif 'YoungGen size' in line:
                            young_gen_heap = self.parse_heap(line)
                        elif 'OldGen size' in line:
                            old_gen_heap = self.parse_heap(line)
                        elif 'PruneScavengeRootNmethods' in line:
                            prune_pointer_count = self.parse_number(line, 'PruneScavengeRootNmethods')
                        elif 'PruneScavenge' in line:
                            prune_time = self.parse_trace_time(line, 'PruneScavengeTime,')
                        elif 'ReferencesTime' in line:
                            pass
                        elif 'References' in line:
                            references = self.parse_line_summaries(line, 2)
                        elif 'Need full gc' in line:
                            need_full_gc = self.parse_number(line, 'Need full gc') == 1
                        elif 'nmethod_epilogue' in line:
                            nmethod = self.parse_line_summaries(line, 2)
                        elif 'Start of TaskQueueStats' in line:
                            start_of_task_queue_stats = True
                            end_of_task_queue_stats = False
                        elif 'End of TaskQueueStats' in line:
                            start_of_task_queue_stats = False
                            end_of_task_queue_stats = True
                        elif 'Start of TaskQueueLocalStats' in line:
                            start_of_local_stats = True
                            end_of_local_stats = False
                        elif 'End of TaskQueueLocalStats' in line:
                            start_of_local_stats = False
                            end_of_local_stats = True
                        elif 'Num of threads' in line:
                            splitted_line = line.split('=')
                            total_threads = int(splitted_line[1])
                        elif 'PSPromotionManagerInfo' in line:
                            pspromotion_info = self.parse_line_summaries(line, 1)

                        # parse local stats
                        if start_of_local_stats and not end_of_local_stats:
                            if 'Start of TaskQueueLocalStats' in line:
                                pass # noop
                            elif 'TaskQueueLocalStats' in line:
                                local_stats = self.parse_line_summaries(line, 1)
                                worker_local_stats.append(local_stats)

                        # parse task queue stats
                        if start_of_task_queue_stats and not end_of_task_queue_stats:
                            if 'Start of TaskQueueStats' in line:
                                pass # noop
                            elif 'TaskQueueStats' in line:
                                task_queue_stats = self.parse_line_summaries(line, 1)
                                worker_task_queue_stats.append(task_queue_stats)

                        # parse worker tracker
                        if start_of_worker and not end_of_worker:
                            if re.search(r'^\[WorkerTracker:(.*)s\]$', line):
                                single_worker = self.parse_line_summaries(line, 2)
                                single_worker['is_containing_sr_tasks'] = single_worker['is_containing_sr_tasks'] == 1.0
                                single_worker['tasks'] = []
                            # 1. parse srt
                            elif 'SRT' in line:
                                srt = self.parse_line_summaries(line, 1)
                                srt['type'] = 'SRT'
                                single_worker['tasks'].append(srt)
                            # 2. parse trt
                            elif 'TRT' in line:
                                trt = self.parse_line_summaries(line, 1)
                                trt['type'] = 'TRT'
                                single_worker['tasks'].append(trt)
                            # 3. parse otyrt
                            elif 'OTYRT' in line:
                                otyrt = self.parse_line_summaries(line, 1)
                                otyrt['type'] = 'OTYRT'
                                single_worker['tasks'].append(otyrt)
                            # 4. parse steal
                            elif 'STEAL' in line:
                                steal = self.parse_line_summaries(line, 1)
                                steal['type'] = 'STEAL'
                                single_worker['tasks'].append(steal)
                            elif 'BARRIER' in line:
                                barrier = self.parse_line_summaries(line, 1)
                                barrier['type'] = 'BARRIER'
                                single_worker['tasks'].append(barrier)

                    line = log_file.readline()
                    pbar.update(len(line.encode('utf-8')))

                    if end_of_gc:
                        end_of_gc = False
                        if parallel_workers != len(workers):
                            continue
                        if phases != '1;3':
                            continue
                        if len(workers) == 0:
                            continue

                        assert parallel_workers == len(workers), 'sanity'
                        # assert len(workers) == len(worker_local_stats), 'sanity'
                        # assert len(workers) == len(worker_task_queue_stats), 'sanity'

                        if parallel:
                            choosen_worker = None
                            choosen_worker_entry = None
                            for worker in workers:
                                if len(worker['tasks']) == 0:
                                    continue

                                if choosen_worker is not None:
                                    # note: last task must be steal task
                                    # if worker['tasks'][-1]['type'] != 'STEAL':
                                    #     continue
                                    # if worker['tasks'][-1]['stack_depth_counter'] > \
                                    #    choosen_worker['tasks'][-1]['stack_depth_counter']:
                                    #     choosen_worker = worker
                                    current_worker_entry = self.process_choosen_worker(worker)
                                    if current_worker_entry['trt']['elapsed'] \
                                       > choosen_worker_entry['trt']['elapsed']:
                                        choosen_worker = worker
                                        choosen_worker_entry = self.process_choosen_worker(choosen_worker)
                                else:
                                    choosen_worker = worker if worker['tasks'][-1]['type'] == 'STEAL' else None
                                    choosen_worker_entry =  None if choosen_worker is None else self.process_choosen_worker(choosen_worker)

                            assert choosen_worker is not None, 'sanity'
                        else:
                            choosen_worker = workers[0]
                            choosen_worker_entry = self.process_choosen_worker(choosen_worker)

                        choosen_worker_stat_idx = 0

                        if parallel:
                            def calculate_total(stat):
                                return stat['copied'] + stat['tenured']
                            total_copied = worker_local_stats[choosen_worker_stat_idx]['copied']
                            total_tenured = worker_local_stats[choosen_worker_stat_idx]['tenured']
                            total_estimated_copied = worker_local_stats[choosen_worker_stat_idx]['estimated_copied']
                            total_estimated_tenured = worker_local_stats[choosen_worker_stat_idx]['estimated_tenured']
                            choosen_total = calculate_total(worker_local_stats[choosen_worker_stat_idx])
                            for stat_idx in range(1, len(worker_local_stats)):
                                total_copied += worker_local_stats[stat_idx]['copied']
                                total_tenured += worker_local_stats[stat_idx]['tenured']
                                total_estimated_copied += worker_local_stats[stat_idx]['estimated_copied']
                                total_estimated_tenured += worker_local_stats[stat_idx]['estimated_tenured']
                                current_total = calculate_total(worker_local_stats[stat_idx])
                                if choosen_total < current_total:
                                    choosen_total = current_total
                                    choosen_worker_stat_idx = stat_idx
                                # if worker_task_queue_stats[choosen_worker_stat_idx]['qpush'] \
                                #    < worker_task_queue_stats[stat_idx]['qpush']:
                                #     choosen_worker_stat_idx = stat_idx

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
                        if old_to_young_roots_task is None:
                            old_to_young_roots_task = {
                                'elapsed': 0,
                                'stripe_num': 0,
                                'stripe_total': 0,
                                'slice_width': 0,
                                'slice_counter': 0,
                                'dirty_card_counter': 0,
                                'objects_scanned_counter': 0,
                                'card_increment_counter': 0,
                                'total_max_card_pointer_being_walked_through': 0,
                                'stack_depth_counter': 0,
                            }
                        if references is None:
                            references = {
                                'soft_count': 0,
                                'soft_count_elapsed': 0.0,
                                'weak_count': 0,
                                'weak_count_elapsed': 0.0,
                                'final_count': 0,
                                'final_count_elapsed': 0.0,
                                'phantom_count': 0,
                                'phantom_count_elapsed': 0.0,
                                'total_process_elapsed': 0.0,
                                'execution_time': 0.0,
                            }

                        if nmethod is None:
                            nmethod = {
                                'count': 0,
                                'elapsed': 0.0,
                            }

                        if pspromotion_info is None:
                            pspromotion_info = {
                                'copying_rate': 0,
                                'tenuring_rate': 0,
                                'total_copied': 0,
                                'global_total_copied': 0,
                                'total_tenured': 0,
                                'global_total_tenured': 0,
                            }

                        gc_time_clean = 0

                        if parallel:
                            pass
                        else:
                            gc_time_clean = gc_time \
                                - nmethod['elapsed'] \
                                - stringtable_time \
                                - prune_time \
                                - references['execution_time'] \
                                - choosen_worker_entry['srt']['elapsed'] \
                                - choosen_worker_entry['trt']['elapsed'] \
                                - choosen_worker_entry['otyrt']['elapsed'] \
                                - choosen_worker_entry['steal']['elapsed'] \
                                - choosen_worker_entry['barrier']['elapsed'] \
                                - choosen_worker_entry['idle']['elapsed']

                        gc_counter_parsed += 1

                        writer.writerow([
                            start_gc_id,
                            allocation_size,
                            phases,
                            parallel_workers,
                            need_full_gc,
                            total_threads,

                            # nmethod
                            nmethod['count'],
                            nmethod['elapsed'],

                            # tasks
                            ## srt
                            choosen_worker_entry['srt']['live'],
                            choosen_worker_entry['srt']['dead'],
                            choosen_worker_entry['srt']['total'],
                            choosen_worker_entry['srt']['stack_depth_counter'],
                            choosen_worker_entry['srt']['elapsed'],

                            ## trt
                            choosen_worker_entry['trt']['live'],
                            choosen_worker_entry['trt']['dead'],
                            choosen_worker_entry['trt']['total'],
                            choosen_worker_entry['trt']['stack_depth_counter'],
                            choosen_worker_entry['trt']['elapsed'],

                            ## otyrt
                            choosen_worker_entry['otyrt']['stripe_num'],
                            choosen_worker_entry['otyrt']['stripe_total'],
                            choosen_worker_entry['otyrt']['slice_width'],
                            choosen_worker_entry['otyrt']['slice_counter'],
                            choosen_worker_entry['otyrt']['dirty_card_counter'],
                            choosen_worker_entry['otyrt']['objects_scanned_counter'],
                            choosen_worker_entry['otyrt']['card_increment_counter'],
                            choosen_worker_entry['otyrt']['total_max_card_pointer_being_walked_through'],
                            choosen_worker_entry['otyrt']['stack_depth_counter'],
                            choosen_worker_entry['otyrt']['elapsed'],

                            ## steal
                            choosen_worker_entry['steal']['stack_depth_counter'],
                            choosen_worker_entry['steal']['elapsed'],

                            ## barrier
                            choosen_worker_entry['barrier']['busy_workers'],
                            choosen_worker_entry['barrier']['elapsed'],

                            ## idle
                            choosen_worker_entry['idle']['elapsed'],

                            # references
                            references['soft_count'],
                            references['soft_count_elapsed'],
                            references['weak_count'],
                            references['weak_count_elapsed'],
                            references['final_count'],
                            references['final_count_elapsed'],
                            references['phantom_count'],
                            references['phantom_count_elapsed'],
                            references['execution_time'],

                            # Stringtable
                            stringtable_info['table_size'],
                            stringtable_info['processed'],
                            stringtable_info['removed'],
                            stringtable_time,

                            # Prune
                            prune_pointer_count,
                            prune_time,

                            # Heap
                            young_gen_heap['capacity'],
                            young_gen_heap['used'],
                            young_gen_heap['free'],

                            old_gen_heap['capacity'],
                            old_gen_heap['used'],
                            old_gen_heap['free'],

                            # local stats
                            worker_local_stats[choosen_worker_stat_idx]['masked_pushes'],
                            worker_local_stats[choosen_worker_stat_idx]['masked_steals'],
                            worker_local_stats[choosen_worker_stat_idx]['arrays_chunked'],
                            worker_local_stats[choosen_worker_stat_idx]['array_chunks_processed'],
                            worker_local_stats[choosen_worker_stat_idx]['copied'],
                            worker_local_stats[choosen_worker_stat_idx]['tenured'],
                            total_copied,
                            total_tenured,
                            worker_local_stats[choosen_worker_stat_idx]['estimated_copied'],
                            worker_local_stats[choosen_worker_stat_idx]['estimated_tenured'],
                            total_estimated_copied,
                            total_estimated_tenured,
                       
                            # task queue stats
                            worker_task_queue_stats[choosen_worker_stat_idx]['qpush'],
                            worker_task_queue_stats[choosen_worker_stat_idx]['qpop'],
                            worker_task_queue_stats[choosen_worker_stat_idx]['qpops'],
                            worker_task_queue_stats[choosen_worker_stat_idx]['qattempt'],
                            worker_task_queue_stats[choosen_worker_stat_idx]['qsteal'],
                            worker_task_queue_stats[choosen_worker_stat_idx]['opush'],
                            worker_task_queue_stats[choosen_worker_stat_idx]['omax'],

                            # parallel task terminator
                            parallel_task_terminator['yields'],
                            parallel_task_terminator['spins'],
                            parallel_task_terminator['peeks'],

                            # parallel task terminator global
                            parallel_task_terminator_global['yields'],
                            parallel_task_terminator_global['spins'],
                            parallel_task_terminator_global['peeks'],

                            # ps promotion info
                            pspromotion_info['copying_rate'],
                            pspromotion_info['tenuring_rate'],
                            pspromotion_info['total_copied'],
                            pspromotion_info['total_tenured'],
                            pspromotion_info['global_total_copied'],
                            pspromotion_info['global_total_tenured'],

                            # Gen time
                            young_gen_gc_time,
                            old_gen_gc_time,
                            scavenge_time,

                            # Time
                            gc_time_clean,
                            gc_time,
                        ])

                        start_gc_id = -99
                        end_gc_id = -100

                        gc_time = 0.0
                        allocation_size = 0.0
                        phases = None
                        parallel_workers = 0

                        scavenge_time = 0.0

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

                        old_to_young_roots_task = None

                        start_of_gc = False
                        end_of_gc = False

                        references = None

                        need_full_gc = False

                        nmethod = None

                        start_of_worker = False
                        end_of_worker = False

                        start_of_local_stats = False
                        end_of_local_stats = False
                        worker_local_stats = []

                        start_of_task_queue_stats = False
                        end_of_task_queue_stats = False
                        worker_task_queue_stats = []

                        total_copied = 0
                        total_tenured = 0
                        total_threads = 0

                        workers = []
                        single_worker = {}

                        pspromotion_info = None

                csv_file.close()
            log_file.close()
        return gc_counter, gc_counter_parsed

def main(args):
    print('Reading config')
    config = load_config(args.config, Task.parse)
    print('Starting parsing...')
    output_dir = './data/processed/{}'.format(config['name'])
    print('Creating data directory {}'.format(output_dir))
    utilities.create_dir(output_dir)
    print('Reading raw data...')
    threads = []
    pbar = tqdm(range(len(config['data'])))
    parser = Parser()
    for index in pbar:
        infile = config['data'][index]['file']
        outfile = '{}/{}.csv'.format(output_dir, config['data'][index]['name'])
        pbar.set_description('Processing raw_data in={} out={}'.format(infile, outfile))
        total, parsed = parser.parse(infile,
                                  outfile,
                                  config['data'][index]['parallel'] if 'parallel' in config['data'][index] else False)
        print('GC Counter: parsed={} total={}'.format(parsed, total))
        print()

if __name__ == '__main__':
    import time
    start_time = time.time()
    main(utilities.get_args())
    print("--- %s seconds ---" % (time.time() - start_time))
    # Threads: --- 71.97676062583923 seconds ---
    # No Thread : --- 64.11785078048706 seconds ---
