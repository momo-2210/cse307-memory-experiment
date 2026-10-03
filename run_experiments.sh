#!/bin/bash
CFG=$1
if [ -z "$CFG" ]; then echo "Usage: sudo ./run_experiments.sh <config_name>"; exit 1; fi
mkdir -p results/raw
get() { grep -E '^(pgmajfault|pswpin|pswpout) ' /proc/vmstat; }

for RUN in 1 2 3; do
  echo "=== $CFG run $RUN ==="
  sync; echo 3 > /proc/sys/vm/drop_caches
  swapoff -a; swapon -a; swapon /swapfile 2>/dev/null
  vmstat 1 > results/raw/vmstat_${CFG}_${RUN}.log &
  VP=$!
  get > /tmp/before.txt
  /usr/bin/time -v timeout 900 python3 workload.py > results/raw/out_${CFG}_${RUN}.txt 2> results/raw/time_${CFG}_${RUN}.txt
  echo "exit=$?" >> results/raw/time_${CFG}_${RUN}.txt
  get > /tmp/after.txt
  kill $VP
  paste /tmp/before.txt /tmp/after.txt | awk '{print $1, $4-$2}' > results/raw/delta_${CFG}_${RUN}.txt
  cat results/raw/out_${CFG}_${RUN}.txt
  grep -E "Elapsed|Maximum resident|exit=" results/raw/time_${CFG}_${RUN}.txt
  cat results/raw/delta_${CFG}_${RUN}.txt
done
