#!/bin/bash
rm -f *.gc*
clang++ hello.cc --coverage -ohello


./hello
for file in *.gcda; do llvm-cov-3.5 -a -b -c -stats -f ${file/d$/c$} 1>/dev/null ; done
python ../parse.py left hello.cc.gcov
rm -f *.gcda *.gcov

./hello mom dad
for file in *.gcda; do llvm-cov-3.5 -a -b -c -stats -f ${file/d$/c$} 1>/dev/null ; done
python ../parse.py right hello.cc.gcov
# rm -f *.gcda *.gcov

python ../compare.py left right --function-diff
python ../compare.py left right --call-diff
python ../compare.py left right --line-diff

