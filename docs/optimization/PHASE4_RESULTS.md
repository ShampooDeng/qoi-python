# Phase 4 Results

Phase 4 reduced helper-call overhead in the hot encode/decode paths by inlining the most frequently used logic and replacing generic sign decoding with direct arithmetic.

## Changes made

- Inlined the hottest encode branch logic in `qoi_encode()`:
  - direct byte emission with `bytearray.append`
  - direct chunk byte construction for RUN, DIFF, LUMA, and RGB paths
- Bound a frequently used method locally:
  - `out_append = out.append`
- Bound frequently used constants/state locally in hot functions:
  - cached `payload_len`
  - cached hash seed for RGB hashing
- Inlined the hottest decode branch logic in `qoi_decode()`:
  - direct RGB byte reads
  - direct INDEX unpacking
  - direct DIFF/LUMA signed field decoding
- Replaced `read_sign_byte()` usage inside decode hot paths with direct arithmetic.
- Minimized helper overhead and temporary object creation inside branch-heavy loops.

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
| photographic_rgb | `(1080, 1920, 3)` | 3.52 MiB | 1029.203 ms | 708.345 ms |
| flat_regions | `(256, 256, 3)` | 5.53 KiB | 18.092 ms | 10.885 ms |
| small_sanity | `(3, 5, 3)` | 56 B | 0.446 ms | 0.282 ms |

## Comparison to Phase 3

| case | phase 3 encode mean | phase 4 encode mean | phase 3 decode mean | phase 4 decode mean |
|---|---:|---:|---:|---:|
| photographic_rgb | 1512.014 ms | 1029.203 ms | 1087.160 ms | 708.345 ms |
| flat_regions | 18.948 ms | 18.092 ms | 11.173 ms | 10.885 ms |
| small_sanity | 0.414 ms | 0.446 ms | 0.213 ms | 0.282 ms |

## Notes

- The large photographic workload shows another strong improvement in both encode and decode.
- Small-case timings remain noisy, which is expected at sub-millisecond scales.
- The standalone helper functions remain available for tests and targeted validation, while the hot loops now avoid their per-pixel call overhead.
