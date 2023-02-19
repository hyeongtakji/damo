#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Change human readable data access monitoring-based operation schemes input for
'damo' to a '_damon.Damos' object.  Currently,

- simple human-readable single line per scheme text and
- json string format

are supported.  Below are the example of the input.

Below are examples of simple human-readable single line per scheme text.

    # format is:
    # <min/max size> <min/max frequency (0-100)> <min/max age> <action>
    #
    # B/K/M/G/T for Bytes/KiB/MiB/GiB/TiB
    # us/ms/s/m/h/d for micro-seconds/milli-seconds/seconds/minutes/hours/days
    # 'min/max' for possible min/max value.

    # if a region keeps a high access frequency for >=100ms, put the region on
    # the head of the LRU list (call madvise() with MADV_WILLNEED).
    min    max      80      max     100ms   max willneed

    # if a region keeps a low access frequency for >=200ms and <=one hour, put
    # the region on the tail of the LRU list (call madvise() with MADV_COLD).
    min     max     10      20      200ms   1h  cold

    # if a region keeps a very low access frequency for >=60 seconds, swap out
    # the region immediately (call madvise() with MADV_PAGEOUT).
    min     max     0       10      60s     max pageout

    # if a region of a size >=2MiB keeps a very high access frequency for
    # >=100ms, let the region to use huge pages (call madvise() with
    # MADV_HUGEPAGE).
    2M      max     90      100     100ms   max hugepage

    # If a regions of a size >=2MiB keeps small access frequency for >=100ms,
    # avoid the region using huge pages (call madvise() with MADV_NOHUGEPAGE).
    2M      max     0       25      100ms   max nohugepage

Below is an exaple of the json string format.

    [
       {
            "comment": "just for monitoring",
            "name": "0",
            "action": "stat",
            "access_pattern": {
                "min_sz_bytes": "0 B",
                "max_sz_bytes": "max",
                "min_nr_accesses": "0 %",
                "max_nr_accesses": "100 %",
                "min_age": "0 ns",
                "max_age": "max"
            },
            "quotas": {
                "time_ms": 0,
                "sz_bytes": 0,
                "reset_interval_ms": 0,
                "weight_sz_permil": 0,
                "weight_nr_accesses_permil": 0,
                "weight_age_permil": 0
            },
            "watermarks": {
                "metric": "none",
                "interval_us": 0,
                "high_permil": 0,
                "mid_permil": 0,
                "low_permil": 0
            },
            "filters": []
        }
    ]
"""

import json
import os
import sys

import _damon

import _damo_fmt_str

def fields_to_v0_scheme(fields):
    scheme = _damon.Damos()
    scheme.access_pattern = _damon.DamosAccessPattern(
            sz_bytes = [_damo_fmt_str.text_to_bytes(fields[0]),
                _damo_fmt_str.text_to_bytes(fields[1])],
            nr_accesses = [_damo_fmt_str.text_to_percent(fields[2]),
                _damo_fmt_str.text_to_percent(fields[3])],
            nr_accesses_unit = _damon.unit_percent,
            age = [_damo_fmt_str.text_to_us(fields[4]),
                _damo_fmt_str.text_to_us(fields[5])],
            age_unit = _damon.unit_usec)
    scheme.action = fields[6].lower()
    return scheme

def warn_deprecation(nr_fields):
    sys.stderr.write('''
WARNING: scheme input of %d fields will be deprecated by 2023-Q2.  Please
report your usecase to sj@kernel.org, damon@liss.linux.dev and
linux-mm@kvack.org if you depend on those.''' % nr_fields)

def fields_to_v1_scheme(fields):
    warn_deprecation(len(fields))
    scheme = fields_to_v0_scheme(fields)
    scheme.quotas.sz_bytes = _damo_fmt_str.text_to_bytes(fields[7])
    scheme.quotas.reset_interval_ms = _damo_fmt_str.text_to_ms(
            fields[8])
    return scheme

def fields_to_v2_scheme(fields):
    warn_deprecation(len(fields))
    scheme = fields_to_v1_scheme(fields)
    scheme.quotas.weight_sz_permil = int(fields[9])
    scheme.quotas.weight_nr_accesses_permil = int(fields[10])
    scheme.quotas.weight_age_permil = int(fields[11])
    return scheme

def fields_to_v3_scheme(fields):
    warn_deprecation(len(fields))
    scheme = fields_to_v2_scheme(fields)
    scheme.watermarks.metric = fields[12].lower()
    scheme.watermarks.interval_us = _damo_fmt_str.text_to_us(
            fields[13])
    scheme.watermarks.high_permil = int(fields[14])
    scheme.watermarks.mid_permil = int(fields[15])
    scheme.watermarks.low_permil = int(fields[16])
    return scheme

def fields_to_v4_scheme(fields):
    scheme = fields_to_v0_scheme(fields)
    scheme.quotas.time_ms = _damo_fmt_str.text_to_ms(fields[7])
    scheme.quotas.sz_bytes = _damo_fmt_str.text_to_bytes(fields[8])
    scheme.quotas.reset_interval_ms = _damo_fmt_str.text_to_ms(
            fields[9])
    scheme.quotas.weight_sz_permil = int(fields[10])
    scheme.quotas.weight_nr_accesses_permil = int(fields[11])
    scheme.quotas.weight_age_permil = int(fields[12])
    scheme.watermarks.metric = fields[13].lower()
    scheme.watermarks.interval_us = _damo_fmt_str.text_to_us(
            fields[14])
    scheme.watermarks.high_permil = int(fields[15])
    scheme.watermarks.mid_permil = int(fields[16])
    scheme.watermarks.low_permil = int(fields[17])
    return scheme

def damo_single_line_scheme_to_damos(line, name):
    '''Returns Damos object and err'''
    fields = line.split()
    try:
        if len(fields) == 7:
            return fields_to_v0_scheme(fields), None
        elif len(fields) == 9:
            return fields_to_v1_scheme(fields), None
        elif len(fields) == 12:
            return fields_to_v2_scheme(fields), None
        elif len(fields) == 17:
            return fields_to_v3_scheme(fields), None
        elif len(fields) == 18:
            return fields_to_v4_scheme(fields), None
        else:
            return None, 'expected %s fields, but \'%s\'' % (
                    [7, 9, 12, 17, 18], line)
    except:
        return None, 'wrong input field'
    return None, 'unsupported version of single line scheme'

def damo_schemes_lines_except_comments(txt):
    return [l for l in txt.strip().split('\n')
            if not l.strip().startswith('#')]

def damo_schemes_to_damos(damo_schemes):
    if os.path.isfile(damo_schemes):
        with open(damo_schemes, 'r') as f:
            damo_schemes = f.read()

    try:
        kvpairs = json.loads(damo_schemes)
        return [_damon.kvpairs_to_Damos(kv) for kv in kvpairs], None
    except:
        # The input is not json file
        pass

    damo_schemes_lines = damo_schemes_lines_except_comments(damo_schemes)

    damos_list = []
    for idx, line in enumerate(damo_schemes_lines):
        line = line.strip()
        if line == '':
            continue
        damos, err = damo_single_line_scheme_to_damos(line, '%d' % idx)
        if err != None:
            return None, ('invalid schemes input (%s)' % err)
        damos_list.append(damos)
    return damos_list, None