# Final Validation

Final validation captured on 2026-05-30 after completing Phases 0 through 5.

## Validation commands

Tests:

```sh
./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
```

Benchmarks:

```sh
./.venv/Scripts/python.exe bench_qoi.py --repeats 3 --warmups 1
```

## Final test result

- Unit tests passed: `32 / 32`
- RGB round-trip validation passed in the benchmark suite for:
  - photographic RGB image
  - flat regions / long-run image
  - small sanity image

## Final benchmark results

| case | shape | encoded size | encode mean | decode mean |
|---|---|---:|---:|---:|
| photographic_rgb | `(1080, 1920, 3)` | 3.44 MiB | 986.467 ms | 816.267 ms |
| flat_regions | `(256, 256, 3)` | 5.53 KiB | 18.294 ms | 10.941 ms |
| small_sanity | `(3, 5, 3)` | 53 B | 0.413 ms | 0.206 ms |

## Final vs baseline

| case | baseline size | final size | baseline encode | final encode | encode improvement | baseline decode | final decode | decode improvement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| photographic_rgb | 3.52 MiB | 3.44 MiB | 9493.805 ms | 986.467 ms | 89.61% faster (`9.62x`) | 5940.218 ms | 816.267 ms | 86.26% faster (`7.28x`) |
| flat_regions | 5.53 KiB | 5.53 KiB | 191.536 ms | 18.294 ms | 90.45% faster (`10.47x`) | 17.123 ms | 10.941 ms | 36.10% faster (`1.57x`) |
| small_sanity | 56 B | 53 B | 1.349 ms | 0.413 ms | 69.38% faster (`3.27x`) | 0.598 ms | 0.206 ms | 65.55% faster (`2.90x`) |

## Summary

- Encode and decode are measurably faster than baseline across all benchmark cases.
- RGB round-trip tests pass consistently.
- Correctness was strengthened with explicit DIFF/LUMA bias handling, required index-table updates, RUN boundary coverage, end-marker validation, and explicit RGB-only support.
- Encoded output became smaller on some workloads after spec-aligned correctness fixes.

## Key implementation outcomes

- Decode no longer uses byte-at-a-time file reads.
- Hot paths use scalar RGB state instead of tiny NumPy operations.
- Encode writes are buffered through a `bytearray`.
- Hot helper logic is inlined where it improved performance.
- RGBA remains explicitly unsupported for now.
