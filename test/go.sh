#!/bin/bash
rm -f *.gc*
clang++ hello.cc --coverage -ohello


./hello
for file in *.gcda; do llvm-cov-3.5 -a -b -c -stats -f ${file/d$/c$} 1>/dev/null ; done
python ../parse.py first hello.cc.gcov
rm -f *.gcda *.gcov

./hello mom dad
for file in *.gcda; do llvm-cov-3.5 -a -b -c -stats -f ${file/d$/c$} 1>/dev/null ; done
python ../parse.py second hello.cc.gcov
# rm -f *.gcda *.gcov

python ../compare.py first second


