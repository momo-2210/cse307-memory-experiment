# CSE-307 Term Paper (Part B): Memory Pressure in a VMware Ubuntu Guest

Runs one fixed memory-heavy workload inside an Ubuntu VM under different VM RAM sizes and records
page faults, swap activity and runtime.

## Environment
- Host: Windows, VMware Workstation (fill in: CPU model, host RAM, VMware version)
- Guest: Ubuntu 26.04.1 LTS, kernel 7.0.0-38-generic, Python 3.14.4, NumPy 2.3.5
- 2 vCPU, 2 GB swapfile (`/swapfile`), `vm.swappiness=60`
- Details: `results/env.txt`

## Workload (`workload.py`)
Allocates a 1500 MB int64 array (touches every page), does 3 sequential sweeps (one read per 4 KB page),
then 2x10^7 random reads (seed 42). Identical in all experiments.

## Experiment runner (`run_experiments.sh <config>`)
For each of 3 runs: drop caches, reset swap, start `vmstat 1`, run the workload under `/usr/bin/time -v`
with a 900 s `timeout`, and store deltas of `/proc/vmstat` counters `pswpin`, `pswpout`, `pgmajfault`.
Runs that hit the timeout have `exit=124`; their counters cover only the first 900 s.

## How to reproduce
```
sudo apt install -y python3-numpy python3-matplotlib time
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
sudo ./run_experiments.sh ram2048_cpu2      # after setting VM RAM in VMware and booting
sudo chown -R $USER:$USER results
python3 analyze.py                          # table + figures into results/
```
RAM sizes tested (VMware setting): 4096, 2048, 1536, 1024 MB. 1024/1536/2048 were run in text mode
(`multi-user.target`) to avoid desktop interference.

## Layout
- `workload.py`, `run_experiments.sh`, `analyze.py`
- `results/raw/` raw logs (`time_`, `delta_`, `out_`, `vmstat_`)
- `results/table3.md`, `results/summary.csv`, `results/fig_*.png`
- `report/` LaTeX source and PDF

## Summary of results
| Config | Finished | Mean elapsed (s) | pswpout | Major faults |
|---|---|---|---|---|
| 4096 MB | 3/3 | 2.4 | 125,235 | 937 |
| 4096 MB (repeat) | 3/3 | 7.9 | 115,776 | 5,028 |
| 2048 MB | 3/3 | 557.9 | 4,255,176 | 4,192,310 |
| 1536 MB | 1/3 | >= 848.3 | 3,514,077 | 3,474,728 |
| 1024 MB | 0/3 | >= 900.2 | 6,607,944 | 5,156,843 |

Reducing guest RAM below the ~1.5 GB working set turns a seconds-long job into thrashing.

## Caveats
- 4096 MB runs were done on the original VM with the desktop running; the other sizes on a clone in text mode.
- CPU count was not varied. Only 3 runs per configuration.

## AI assistance disclosure
An AI assistant (Claude) was used for help with the shell scripts, the analysis script, troubleshooting
the VM setup, and drafting the report text. Experiments were run, and results checked, by the author.
