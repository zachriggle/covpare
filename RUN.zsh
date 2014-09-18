#!/usr/bin/env zsh
sudo rm -rf **/*.gcda **/*.gcov
sudo qemu-system-x86_64 -enable-kvm -drive file=/home/user/ubuntu/hda,if=virtio  -m 512 -smp 4 -cpu host -netdev type=tap,script=/etc/qemu-ifup,id=net0 -device virtio-net-pci,netdev=net0
for file in **/*.gcda; do llvm-cov-3.5 -a -b -c -stats -f ${file/d$/c$}; done
python ~/parse.py $1 **/*.gcov