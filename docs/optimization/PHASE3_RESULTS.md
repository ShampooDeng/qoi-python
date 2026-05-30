# Phase 3 Results

Phase 3 buffered encoder output into a `bytearray` and wrote the completed file once at the end.

## Changes made

- Replaced repeated hot-loop `f.write(...)` calls in `qoi_encode()` with a `bytearray` buffer.
- Appended the QOI header to the output buffer first.
- Appended chunk bytes to the buffer during encode.
- Appended `END_MARKER` to the buffer at the end.
- Wrote the completed buffer once with a single `f.write(out)` call.

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
| photographic_rgb | `(1080, 1920, 3)` | 3.52 MiB | 1512.014 ms | 1087.160 ms |
| flat_regions | `(256, 256, 3)` | 5.53 KiB | 18.948 ms | 11.173 ms |
| small_sanity | `(3, 5, 3)` | 56 B | 0.414 ms | 0.213 ms |

## Comparison to Phase 2

| case | phase 2 encode mean | phase 3 encode mean | phase 2 size | phase 3 size |
|---|---:|---:|---:|---:|
| photographic_rgb | 1605.801 ms | 1512.014 ms | 3.52 MiB | 3.52 MiB |
| flat_regions | 18.916 ms | 18.948 ms | 5.53 KiB | 5.53 KiB |
| small_sanity | 0.425 ms | 0.414 ms | 56 B | 56 B |

## Notes

- Output sizes are unchanged, as expected.
- Encode performance improved modestly on the large photographic case.
- This phase keeps behavior the same while simplifying the write path for later low-level tuning.
