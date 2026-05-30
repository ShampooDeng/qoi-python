# Phase 5 Results

Phase 5 focused on correctness hardening before deeper optimization work.

## Changes made

- Corrected DIFF packing to use the QOI bias rules explicitly:
  - stored values as `(diff + 2)` for each 2-bit field
- Corrected LUMA packing to use the QOI bias rules explicitly:
  - stored `dg + 32`
  - stored `drg + 8` and `dbg + 8`
- Corrected decode helpers to mirror those bias rules directly.
- Fixed index table updates so every pixel-producing path updates the index cache during both encode and decode.
- Added explicit RGB-only support policy:
  - `qoi_encode()` rejects RGBA input with `NotImplementedError`
  - `qoi_decode()` rejects RGBA headers/chunks with `NotImplementedError`
- Added end-marker validation in `qoi_decode()`.

## Added tests

- DIFF boundary bias encoding
- LUMA boundary bias encoding
- RUN boundary round-trip behavior
- INDEX reuse after DIFF/LUMA-produced pixels
- Invalid end-marker rejection
- RGBA encode rejection
- RGBA decode rejection

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
| photographic_rgb | `(1080, 1920, 3)` | 3.44 MiB | 1001.648 ms | 841.330 ms |
| flat_regions | `(256, 256, 3)` | 5.53 KiB | 18.592 ms | 11.389 ms |
| small_sanity | `(3, 5, 3)` | 53 B | 0.448 ms | 0.225 ms |

## Notes

- Output sizes changed for some cases because the encoder is now more spec-aligned and reuses the index table correctly after all pixel-producing paths.
- The photographic benchmark size dropped from 3.52 MiB to 3.44 MiB.
- The small sanity case dropped from 56 B to 53 B.
- These changes are expected correctness improvements, not regressions.
