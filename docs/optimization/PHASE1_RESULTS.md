# Phase 1 Results

Phase 1 refactored decoding to parse the QOI payload from memory with a byte-position cursor instead of using byte-at-a-time file reads in the hot loop.

## Changes made

- `qoi_decode()` now reads the payload once with `f.read()` after the header.
- Added a decode cursor `pos` into a `memoryview` payload.
- Replaced `int.from_bytes(f.read(1), 'big')` in the decode loop.
- Refactored:
  - `decode_rgb(payload, pos, index_table)`
  - `decode_luma(payload, pos, buffer, px)`
- Added explicit payload boundary checks so `pos` does not overrun.
- Updated unit tests for the in-memory helper interfaces.

## Validation

Test command:

```sh
./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
```

Benchmark command:

```sh
./.venv/Scripts/python.exe bench_qoi.py --repeats 3 --warmups 1
```

## Decode performance compared to baseline

| case | baseline decode mean | phase 1 decode mean | improvement |
|---|---:|---:|---:|
| photographic_rgb | 5940.218 ms | 2842.321 ms | 52.15% faster |
| flat_regions | 17.123 ms | 9.696 ms | 43.37% faster |
| small_sanity | 0.598 ms | 0.260 ms | 56.52% faster |

## Full phase 1 benchmark snapshot

| case | shape | encoded size | encode mean | decode mean |
|---|---|---:|---:|---:|
| photographic_rgb | `(1080, 1920, 3)` | 3.52 MiB | 10350.103 ms | 2842.321 ms |
| flat_regions | `(256, 256, 3)` | 5.53 KiB | 103.696 ms | 9.696 ms |
| small_sanity | `(3, 5, 3)` | 56 B | 0.533 ms | 0.260 ms |

## Notes

- Decode improved substantially, as expected for this phase.
- Encode timing fluctuated during these short benchmark runs, but Phase 1 only targeted decode behavior.
