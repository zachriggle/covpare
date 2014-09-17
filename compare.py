#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import argparse
import os, sys
import pymongo # pip install pymongo
import fileinput
from pprint import pprint
from bson.code import Code
import re
from itertools import izip

p    = argparse.ArgumentParser()
p.add_argument('--function-diff', action='store_true')
p.add_argument('--line-diff', action='store_true')
p.add_argument('--call-diff', action='store_true')

p.add_argument('--call-scale', default=3, type=float)
p.add_argument('--file-regex', default=None)
p.add_argument('--func-regex', default=None)
p.add_argument('--no-scale', action='store_true')
p.add_argument('--ignore-zero', action='store_true')
p.add_argument('--ignore-same', action='store_true')
p.add_argument('--only-new', action='store_true')

p.add_argument('a')
p.add_argument('b')
args = p.parse_args()

print args

default_query = {}

if args.file_regex: default_query['filename'] = {'$regex': args.file_regex}
if args.func_regex: default_query['name']     = {'$regex': args.func_regex}

def Q(x):
    y = dict(default_query)
    y.update(x)
    return y

a = pymongo.MongoClient().gcov[args.a]
b = pymongo.MongoClient().gcov[args.b]

def total_calls(c):
    """For a given collection, determine the total number of calls invoked"""
    map    = Code("function()    { emit('total', this.calls) }")
    reduce = Code("function(k,v) { return Array.sum(v) }")
    return c.map_reduce(map, reduce, "total").find_one({'_id':'total'})['value']



def call_diff():
    a_total_calls = total_calls(a)
    b_total_calls = total_calls(b)

    a.ensure_index('name')
    b.ensure_index('name')

    a_cur = a.find(default_query).sort('name')
    b_cur = b.find(default_query).sort('name')

    for fna, fnb in izip(a_cur, b_cur):
        a_call = fna['calls'] / a_total_calls
        b_call = fnb['calls'] / b_total_calls

        if a_call and (args.call_scale * a_call) < b_call:
            print "%s %s" % (b_call/a_call, fna['name'])

def function_diff():
    # For each function that was called in both runs, collate info
    block_same     = set()
    block_differ   = set()

    # Collect the names of *all* functions which were actually called
    query = Q({'calls': {'$gt': 0}})
    a_func = set(a.find(query).distinct('name'))
    b_func = set(b.find(query).distinct('name'))

    # Show functions that only appear on either side
    for func in sorted(a_func - b_func): print '-100%% %s: %s' % (args.a, func)
    for func in sorted(b_func - a_func): print '+100%% %s: %s' % (args.b, func)

    # Functions to iterate through
    functions = sorted(a_func & b_func)

    for func in functions:
        query = Q({'name': func})
        fa = a.find_one(query, {'calls': 1, 'blocks': 1})
        fb = b.find_one(query, {'calls': 1, 'blocks': 1})

        a_blocks = fa['blocks']
        a_calls  = fa['calls']

        b_blocks = fb['blocks']
        b_calls  = fb['calls']

        delta_blocks = abs(a_blocks - b_blocks)

        # If the block coverage on both sides is the same...
        if not delta_blocks:
            block_same.add(func)

        # Coverage differs
        else:
            block_differ.add(func)

            sign = '+'    if b_blocks > a_blocks else '-'
            name = args.b if b_blocks > a_blocks else args.a

            print '%s%s%% %s: %s [%i %i%%] [%i:%i%%]' % (sign, delta_blocks, name, func, a_calls, a_blocks, b_calls, b_blocks)

def adjust(function):
    divisor = float(function['calls'] or 1)
    for i,line in enumerate(function['lines']):
        function['lines'][i]['hits'] /= divisor
        for j,block in enumerate(line['blocks']):
            function['lines'][i]['blocks'][j]['taken'] /= divisor
    return function

def line_diff():
    #
    # This gives us all of the functions, sorted by filename,
    # and then in file order.
    #
    keys = (('filename', 1), ('start', 1))
    a.ensure_index(keys)
    b.ensure_index(keys)
    a_functions = a.find(default_query).sort(keys)
    b_functions = b.find(default_query).sort(keys)

    for a_fn, b_fn in izip(a_functions, b_functions):
        filename = a_fn['filename']

        if not args.no_scale:
            a_fn = adjust(a_fn)
            b_fn = adjust(b_fn)

        if args.ignore_zero and a_fn['blocks'] == 0 and b_fn['blocks'] == 0:
            continue
        if args.ignore_same and a_fn['lines'] == b_fn['lines']:
            continue

        # Sanity check
        if a_fn['name'] != b_fn['name']:
            pprint(a_fn)
            pprint(b_fn)
            raise Exception("Mismatch, should not happen!")

        a_lines = a_fn['lines']
        b_lines = b_fn['lines']

        a_lines = sorted(a_lines, key=lambda x: x['lineno'])
        b_lines = sorted(b_lines, key=lambda x: x['lineno'])

        # PER LINE
        for al,bl in zip(a_lines, b_lines):
            lineno = al['lineno']
            source = al['source']

            delta  = al['hits'] - bl['hits']

            if args.only_new and al['hits'] != 0:
                continue
            if args.ignore_zero and delta == 0:
                continue

            stats = "%.2g" % (al['hits'])

            if delta != 0:
                sign  = '+' if delta < 0 else '-'
                stats += '%s%.2g' % (sign, abs(delta))

            try:
                print u'%s:%-4i | %10s | %s ' % (filename, lineno, stats, source.decode('utf-8'))
            except:
                print repr((filename, lineno, stats, source))

if args.line_diff:      line_diff()
if args.function_diff:  function_diff()
if args.call_diff:      call_diff()
sys.exit()


"""
for func_a in a.find():
    # pprint(func_a)
    name = func_a['name']
    func_b = b.find_one({'name': name})
    # pprint(func_b)

    # Did we hit more blocks in the second one?
    blocks_a = func_a['blocks']
    blocks_b = func_b['blocks']

    # pprint(func_a)
    # pprint(func_b)
    # break

    if 10*blocks_a < blocks_b:
        print '!! %i %i : %i : %s' % (blocks_a, blocks_b, func_a['lines'][0]['lineno'], name)

    # Just new lines?
    for line_a,line_b in zip(func_a['lines'], func_b['lines']):
        hits_a = line_a['hits']
        hits_b = line_b['hits']
        if hits_a < hits_b:
            print '%i %i : %i : %s' % (hits_a, hits_b, line_a['lineno'], line_a['source'].rstrip())

        # Maybe a new conditional (block or branch)
        for branch_a,branch_b in zip(line_a['branches'], line_b['branches']):
            taken_a = branch_a['taken']
            taken_b = branch_b['taken']
            if 10*taken_a < taken_b:
                print '%i %i : %i : %s' % (hits_a, hits_b, line_a['lineno'], line_a['source'].rstrip())

        for block_a,block_b in zip(line_a['blocks'], line_b['blocks']):
            taken_a = block_a['taken']
            taken_b = block_b['taken']
            if 10*taken_a < taken_b:
                print '%i %i : %i : %s' % (hits_a, hits_b, line_a['lineno'], line_a['source'].rstrip())

for func_b in b.find():
    # pprint(func_a)
    name = func_a['name']
    func_a = a.find_one({'name': name})

    blocks_a = func_a['blocks']
    blocks_b = func_b['blocks']
"""