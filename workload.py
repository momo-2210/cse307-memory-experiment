import time
import numpy as np

N_MB = 1500
n = N_MB * 1024 * 1024 // 8        # int64 element count
stride = 4096 // 8                  # one element per 4 KB page

t0 = time.time()
a = np.ones(n, dtype=np.int64)      # allocate and touch all pages
t_alloc = time.time() - t0

t0 = time.time()
s = 0
for _ in range(3):                  # 3 sequential sweeps, every page
    s += int(a[::stride].sum())
t_seq = time.time() - t0

t0 = time.time()
rng = np.random.default_rng(42)
total = 20_000_000
chunk = 1_000_000
for _ in range(total // chunk):     # random reads
    idx = rng.integers(0, n, chunk)
    s += int(a[idx].sum())
t_rand = time.time() - t0

print(f"Alloc s: {t_alloc:.3f}")
print(f"Seq s: {t_seq:.3f}")
print(f"Rand s: {t_rand:.3f}")
print(f"checksum: {s}")
