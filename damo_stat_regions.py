#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_stat

import _damo_fmt_str
import _damo_subcmds
import _damon

def out_of_range(minval, val, maxval):
    return val < minval or maxval < val

def pr_schemes_tried_regions(kdamond_name, monitoring_scheme,
        access_pattern, raw_nr):
    for kdamond in _damon.current_kdamonds():
        if kdamond.name != kdamond_name:
            continue
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                if scheme == monitoring_scheme:
                    access_pattern.convert_for_units(
                            _damon.unit_sample_intervals,
                            _damon.unit_aggr_intervals, ctx.intervals)
                    for region in scheme.tried_regions:
                        if out_of_range(access_pattern.min_sz_bytes,
                                region.end - region.start,
                                access_pattern.max_sz_bytes):
                            continue
                        if out_of_range(access_pattern.min_nr_accesses,
                                region.nr_accesses,
                                access_pattern.max_nr_accesses):
                            continue
                        if out_of_range(access_pattern.min_age, region.age,
                                access_pattern.max_age):
                            continue
                        print(region.to_str(raw_nr, ctx.intervals))
                    return

def monitoring_kdamond_scheme():
    monitoring_kdamond = None
    monitoring_scheme = None
    kdamonds = _damon.current_kdamonds()
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                if _damon.is_monitoring_scheme(scheme, ctx.intervals):
                    return kdamond.name, scheme
    return None, None

def update_pr_schemes_tried_regions(access_pattern, raw_nr):
    if _damon.every_kdamond_turned_off():
        print('no kdamond running')
        exit(1)

    monitoring_kdamond, monitoring_scheme = monitoring_kdamond_scheme()
    if monitoring_kdamond == None:
        print('no kdamond is having monitoring scheme')
        exit(1)

    err = _damon.update_schemes_tried_regions([monitoring_kdamond])
    if err != None:
        print('update schemes tried regions fail: %s', err)
        exit(1)

    pr_schemes_tried_regions(monitoring_kdamond, monitoring_scheme,
            access_pattern, raw_nr)

def set_argparser(parser):
    damo_stat.set_common_argparser(parser)
    parser.add_argument('--sz_region', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max size of scheme target regions (bytes)')
    parser.add_argument('--access_rate', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max access rate of scheme target regions (percent)')
    parser.add_argument('--age', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max age of scheme target regions (microseconds)')

def __main(args):
    if not _damon.feature_supported('schemes_tried_regions'):
        print('schemes_tried_regions feature not supported')
        exit(1)
    access_pattern = _damon.DamosAccessPattern(args.sz_region,
            args.access_rate, _damon.unit_percent, args.age, _damon.unit_usec)
    update_pr_schemes_tried_regions(access_pattern, args.raw)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    damo_stat.run_count_delay(__main, args)

    for i in range(args.count):
        if i != args.count - 1:
            time.sleep(args.delay)

if __name__ == '__main__':
    main()
