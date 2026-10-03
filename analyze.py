#!/usr/bin/env python3
"""Analyze CSE307 memory experiment results.

Usage (from the cse307_experiment folder):
    python3 analyze.py

Reads results/raw/{time,delta,out,vmstat}_<config>_<run>.{txt,log}
Writes results/table3.md, results/summary.csv and results/*.png
"""
import re, glob, os, csv
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAW = "results/raw"
OUT = "results"
TIMEOUT_S = 900


def parse_elapsed(s):
    parts = s.strip().split(":")
    parts = [float(p) for p in parts]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def parse_time(path):
    d = {}
    for line in open(path):
        if "Elapsed (wall clock)" in line:
            d["elapsed"] = parse_elapsed(line.split(": ", 1)[1].split("):")[-1] if "):" in line else line.rsplit(": ", 1)[1])
        elif "Maximum resident set size" in line:
            d["rss_mb"] = int(line.rsplit(": ", 1)[1]) / 1024
        elif "Major (requiring I/O)" in line:
            d["major_time"] = int(line.rsplit(": ", 1)[1])
        elif line.startswith("exit="):
            d["exit"] = int(line.strip().split("=")[1])
    return d


def parse_delta(path):
    d = {}
    for line in open(path):
        p = line.split()
        if len(p) == 2:
            d[p[0]] = int(p[1])
    return d


def parse_out(path):
    d = {}
    if not os.path.exists(path):
        return d
    for line in open(path):
        m = re.match(r"(Alloc|Seq|Rand) s: ([\d.]+)", line)
        if m:
            d[m.group(1).lower()] = float(m.group(2))
    return d


def ram_of(cfg):
    return int(re.match(r"ram(\d+)_", cfg).group(1))


runs = defaultdict(list)
for tp in sorted(glob.glob(f"{RAW}/time_*.txt")):
    m = re.match(r"time_(.+)_(\d+)\.txt$", os.path.basename(tp))
    cfg, run = m.group(1), int(m.group(2))
    r = parse_time(tp)
    r.update({f"d_{k}": v for k, v in parse_delta(f"{RAW}/delta_{cfg}_{run}.txt").items()})
    r.update(parse_out(f"{RAW}/out_{cfg}_{run}.txt"))
    r["run"] = run
    r["completed"] = r.get("exit", -1) == 0
    runs[cfg].append(r)

cfgs = sorted(runs, key=lambda c: (-ram_of(c), c))

# ---- per-run CSV
with open(f"{OUT}/summary.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["config", "run", "exit", "elapsed_s", "max_rss_mb", "pswpin", "pswpout", "pgmajfault"])
    for c in cfgs:
        for r in runs[c]:
            w.writerow([c, r["run"], r.get("exit"), r.get("elapsed"), round(r.get("rss_mb", 0), 1),
                        r.get("d_pswpin"), r.get("d_pswpout"), r.get("d_pgmajfault")])

# ---- Markdown table (per config, mean of runs)
lines = ["| Config | Completed | Elapsed (s) mean | Max RSS (MB) | pswpin | pswpout | pgmajfault |",
         "|---|---|---|---|---|---|---|"]
agg = {}
for c in cfgs:
    rs = runs[c]
    done = sum(r["completed"] for r in rs)
    el = np.mean([r["elapsed"] for r in rs])
    rss = np.mean([r["rss_mb"] for r in rs])
    si = np.mean([r.get("d_pswpin", 0) for r in rs])
    so = np.mean([r.get("d_pswpout", 0) for r in rs])
    mf = np.mean([r.get("d_pgmajfault", 0) for r in rs])
    agg[c] = dict(done=done, n=len(rs), el=el, rss=rss, si=si, so=so, mf=mf,
                  el_all=[r["elapsed"] for r in rs], ok=[r["completed"] for r in rs])
    flag = "" if done == len(rs) else " (lower bound, timeouts)"
    lines.append(f"| {c} | {done}/{len(rs)} | {el:.1f}{flag} | {rss:.0f} | {si:,.0f} | {so:,.0f} | {mf:,.0f} |")
lines.append("")
lines.append(f"Runs killed at {TIMEOUT_S} s (exit=124) are counted as 900 s; their counters cover only the first 900 s.")
open(f"{OUT}/table3.md", "w").write("\n".join(lines))
print("\n".join(lines))

# ---- Figure 1: elapsed time vs config (log scale, timeouts hatched)
fig, ax = plt.subplots(figsize=(7, 4))
x = np.arange(len(cfgs))
for i, c in enumerate(cfgs):
    for j, (e, ok) in enumerate(zip(agg[c]["el_all"], agg[c]["ok"])):
        ax.scatter(i + (j - 1) * 0.12, e, marker="o" if ok else "x",
                   color="tab:blue" if ok else "tab:red", s=45)
    ax.plot([i - 0.25, i + 0.25], [agg[c]["el"]] * 2, color="k", lw=1)
ax.axhline(TIMEOUT_S, ls="--", color="gray")
ax.text(len(cfgs) - 0.5, TIMEOUT_S * 1.08, "900 s timeout", ha="right", fontsize=8)
ax.set_yscale("log")
ax.set_xticks(x)
ax.set_xticklabels([c.replace("_cpu2", "") for c in cfgs], rotation=20)
ax.set_ylabel("Elapsed time (s, log)")
ax.set_title("Workload runtime vs VM RAM (o = finished, x = timeout)")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_elapsed.png", dpi=200)

# ---- Figure 2: swap and major faults
fig, axs = plt.subplots(1, 2, figsize=(10, 4))
sw_in = [agg[c]["si"] for c in cfgs]
sw_out = [agg[c]["so"] for c in cfgs]
w = 0.38
axs[0].bar(x - w / 2, sw_in, w, label="pswpin")
axs[0].bar(x + w / 2, sw_out, w, label="pswpout")
axs[0].set_xticks(x)
axs[0].set_xticklabels([c.replace("_cpu2", "") for c in cfgs], rotation=20)
axs[0].set_ylabel("Pages (mean per run)")
axs[0].set_title("Swap activity")
axs[0].legend()
axs[1].bar(x, [agg[c]["mf"] for c in cfgs], color="tab:orange")
axs[1].set_xticks(x)
axs[1].set_xticklabels([c.replace("_cpu2", "") for c in cfgs], rotation=20)
axs[1].set_title("Major page faults")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_swap_faults.png", dpi=200)

# ---- Figure 3: vmstat timeline (si/so over time), run 1 of each config
fig, axs = plt.subplots(len(cfgs), 1, figsize=(8, 2.0 * len(cfgs)), sharex=False)
if len(cfgs) == 1:
    axs = [axs]
for ax, c in zip(axs, cfgs):
    p = f"{RAW}/vmstat_{c}_1.log"
    si, so = [], []
    for line in open(p):
        t = line.split()
        if len(t) >= 8 and t[0].isdigit():
            si.append(int(t[6]))
            so.append(int(t[7]))
    ax.plot(si, label="si (KB/s)", lw=0.8)
    ax.plot(so, label="so (KB/s)", lw=0.8)
    ax.set_ylabel(c.replace("_cpu2", ""), fontsize=8)
    ax.tick_params(labelsize=7)
axs[0].legend(fontsize=7)
axs[-1].set_xlabel("Time (s)")
fig.suptitle("vmstat swap-in/out timeline (run 1)", fontsize=10)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_vmstat_timeline.png", dpi=200)
print("\nSaved: table3.md, summary.csv, fig_elapsed.png, fig_swap_faults.png, fig_vmstat_timeline.png in results/")
