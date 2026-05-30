# Phase 2 Results

Phase 2 replaced tiny NumPy hot-loop operations with scalar RGB state and a packed integer index table.

## Changes made

- Replaced encode hot-loop pixel state with scalar integers:
  - previous pixel: `pr, pg, pb`
  - current pixel extracted as Python ints
- Replaced decode hot-loop pixel state with scalar integers:
  - current pixel: `r, g, b`
- Removed hot-path `np.array_equal(...)` checks in encode.
- Replaced the index table representation with packed RGB integers (`0xRRGGBB`).
- Added helpers:
  - `pack_rgb24(r, g, b)`
  - `unpack_rgb24(value)`
- Refactored decode helpers to use scalar arithmetic:
  - `decode_rgb(...) -> r, g, b, pos`
  - `decode_diff(...) -> r, g, b`
  - `decode_luma(...) -> r, g, b, pos`
  - `decode_index(...) -> (r, g, b)`
- Preserved wraparound behavior in decode using `& 0xFF` channel masking.

## Validation

Test command:

```sh
./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
```

Benchmark command:

```sh
./.venv/Scripts/python.exe bench_qoi.py --repeats 3 --warmups 1
```

## Performance snapshot

| case | shape | encoded size | encode mean | decode mean |
|---|---|---:|---:|---:|
| photographic_rgb | `(1080, 1920, 3)` | 3.52 MiB | 1605.801 ms | 1094.897 ms |
| flat_regions | `(256, 256, 3)` | 5.53 KiB | 18.916 ms | 11.542 ms |
| small_sanity | `(3, 5, 3)` | 56 B | 0.425 ms | 0.274 ms |

## Comparison to previous phases

### vs Phase 1

| case | phase 1 encode mean | phase 2 encode mean | phase 1 decode mean | phase 2 decode mean |
|---|---:|---:|---:|---:|
| photographic_rgb | 10350.103 ms | 1605.801 ms | 2842.321 ms | 1094.897 ms |
| flat_regions | 103.696 ms | 18.916 ms | 9.696 ms | 11.542 ms |
| small_sanity | 0.533 ms | 0.425 ms | 0.260 ms | 0.274 ms |

### vs Baseline

| case | baseline encode mean | phase 2 encode mean | baseline decode mean | phase 2 decode mean |
|---|---:|---:|---:|---:|
| photographic_rgb | 9493.805 ms | 1605.801 ms | 5940.218 ms | 1094.897 ms |
| flat_regions | 191.536 ms | 18.916 ms | 17.123 ms | 11.542 ms |
| small_sanity | 1.349 ms | 0.425 ms | 0.598 ms | 0.274 ms |

## Notes

- The largest win in this phase is encode speed, especially on the photographic image.
- Decode also improved substantially on the photographic workload.
- Small-case timing noise is visible, but the overall trend is strongly positive.
