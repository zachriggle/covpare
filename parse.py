#!/usr/bin/env python2
import argparse
import os, sys
import pymongo # pip install pymongo
import fileinput
import subprocess
import re

def function(filename, name, calls, retns, blocks):
    return {
        'filename': filename.replace('.gcov',''),
        'name':     subprocess.check_output(['c++filt', name]).strip(),
        'calls':    calls,
        'retns':    retns,
        'blocks':   blocks,
        'lines':    []
    }

def sourceline(lineno, source, hits):
    return {
        'lineno':   int(lineno),
        'source':   source,
        'hits':     int(hits),
        'branches': [],
        'blocks':   []
    }

def branch(number, taken):
    return {
        'number': number,
        'taken':  taken
    }

block = branch

def main():
    a    = argparse.ArgumentParser()
    a.add_argument('name')
    a.add_argument('gcov', nargs='+', metavar='file.c.gcov', help='.c.gcov file')
    args = a.parse_args()

    db = pymongo.MongoClient().gcov[args.name]
    db.drop()

    # Filter out missing files
    for file in [f for f in args.gcov if not os.path.exists(f)]:
        print "File %r does not exist" % file
        sys.exit()

    # Read input line-by-line
    finput = fileinput.FileInput(args.gcov, mode='r')
    func   = None
    for line in finput:
        words    = re.split('[\s:]+', line.strip())

        # Reset everything on a new file or when a new function is found.
        if finput.isfirstline():
            if func:
                if func['lines']:
                    func['start'] = func['lines'][0]['lineno']
                db.save(func)
            func = None

        # Line was not executed.  Fake a 'zero' count.
        # -:   54:#ifndef PR_MCE_KILL_SET
        if words[0] in ('#####','-','$$$$$'):
            if not func:
                continue
            words[0] = '0'

        # Line is an unconditional jump, and always taken
        # Its statistics are accounted for already.
        # This is only emitted with the '-u' flag
        if words[0] == 'unconditional':
            pass

        # Function statistics
        # function cpu_thread_is_idle called 38 returned 100% blocks executed 91%
        elif words[0] == 'function':
            if func:
                if func['lines']:
                    func['start'] = func['lines'][0]['lineno']
                db.save(func)
            func = function(finput.filename(), words[1], int(words[3]), int(words[5][:-1]), int(words[-1][:-1]))

        # Begin a source line
        # 1:   10:    if(argc == 1) {
        elif words[0].isdigit() and words[1].isdigit():
            count  = int(words[0])
            lineno = int(words[1])
            source = line.split(':',2)[-1].rstrip()

            func['lines'].append(sourceline(lineno, source, count))

        # Begin a block within a source line
        # 1:   10-block  0
        elif words[1].endswith('-block'):
            count    = int(words[0].rstrip(':'))
            number   = int(words[2])
            func['lines'][-1]['blocks'].append(block(number, count))

        # Begin a branch within a source line
        #         3:   17:        x++ && x++;
        #         3:   17-block  0
        # branch  0 taken 3
        # branch  1 taken 0
        #         3:   17-block  1
        # unconditional  2 taken 3
        #
        # branch  0 never executed
        elif words[0] == 'branch':
            number = int(words[1])
            count  = 0
            if words[2] != 'never':
                count = int(words[3])
            func['lines'][-1]['branches'].append(branch(number, count))

        else:
            print "Got unknown line!\n%r" % line
            sys.exit()

    print "Parsed %i lines" % finput.lineno()


if __name__ == '__main__':
    main()