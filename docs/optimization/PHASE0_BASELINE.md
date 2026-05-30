# Phase 0 Baseline

Baseline measurements captured on 2026-05-30 after adding `bench_qoi.py`.

## Environment

- Python: 3.12.13
- Platform: Windows-11-10.0.26200-SP0
- Benchmark command:

```sh
./.venv/Scripts/python.exe bench_qoi.py --repeats 3 --warmups 1
```

- Test command:

```sh
./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
```

## Results

| case | shape | encoded size | encode mean | encode median | decode mean | decode median |
|---|---|---:|---:|---:|---:|---:|
| photographic_rgb | `(1080, 1920, 3)` | 3.52 MiB | 9493.805 ms | 10583.248 ms | 5940.218 ms | 5955.708 ms |
| flat_regions | `(256, 256, 3)` | 5.53 KiB | 191.536 ms | 192.886 ms | 17.123 ms | 17.466 ms |
| small_sanity | `(3, 5, 3)` | 56 B | 1.349 ms | 1.333 ms | 0.598 ms | 0.596 ms |

## Notes

- `bench_qoi.py` validates RGB round-trip correctness before timing each case.
- Cases included for Phase 0:
  - photographic RGB image: `data/background.jpg`
  - flat regions / long runs: synthetic 256x256 block image
  - small sanity image: synthetic 3x5 RGB image
- These numbers are the comparison baseline for later optimization phases.
