# QOI Python Optimization Checklist

Concrete execution checklist for optimizing `qoi.py` while keeping `OPTIMIZATION_PLAN.md` unchanged.

## Phase 0 — Baseline and safety checks

- [x] Add a benchmark entry point (`bench_qoi.py` or extend `test_qoi.py`)
- [x] Measure current encode time on a photographic RGB image
- [x] Measure current decode time on a photographic RGB image
- [x] Measure current encode/decode time on an image with flat regions / long runs
- [x] Measure current encode/decode time on a small sanity-check image
- [x] Record output file sizes for each benchmark case
- [x] Add a round-trip check: `decoded.shape == original.shape`
- [x] Add a round-trip check: RGB pixel equality for supported inputs
- [x] Save baseline numbers in comments or a markdown note

### Added test coverage

- [x] Create `tests/test_qoi_unittest.py`
- [x] Cover header packing/parsing
- [x] Cover chunk packers and range validation
- [x] Cover decode helper behavior (`decode_rgb`, `decode_diff`, `decode_luma`, `decode_index`)
- [x] Cover encode/decode integration on small RGB images
- [x] Cover manual chunk sequence derived from `playground.py`

## Phase 1 — Eliminate byte-at-a-time decoding

- [ ] Refactor `qoi_decode()` to read payload bytes into memory once
- [ ] Introduce a byte-position cursor (`pos`) for parsing
- [ ] Replace `int.from_bytes(f.read(1), 'big')` in the decode loop
- [ ] Refactor `decode_rgb()` to consume in-memory bytes instead of a file handle
- [ ] Refactor `decode_luma()` to consume in-memory bytes instead of a file handle
- [ ] Remove other per-byte file reads from decode helpers
- [ ] Verify decode loop boundaries are correct (`pos` never overruns)
- [ ] Re-run round-trip tests after the refactor
- [ ] Re-measure decode performance and record improvement

## Phase 2 — Remove tiny NumPy ops from the hot path

- [ ] Replace current/previous pixel NumPy arrays with scalar RGB state in encode
- [ ] Replace current/previous pixel NumPy arrays with scalar RGB state in decode
- [ ] Replace `np.array_equal(px, px_pre)` with scalar comparisons
- [ ] Replace `np.array_equal(index_table[index_pos], px)` with scalar comparisons
- [ ] Remove repeated tiny `np.asarray([...], dtype=np.uint8)` allocations in decode
- [ ] Remove repeated tiny NumPy additions in `decode_diff()`
- [ ] Remove repeated tiny NumPy additions in `decode_luma()`
- [ ] Decide on index table representation:
  - [ ] Option A: packed RGB integers
  - [ ] Option B: RGB tuples
- [ ] Implement the chosen index table representation
- [ ] Ensure wraparound behavior is preserved for channel arithmetic
- [ ] Re-run round-trip tests after scalar-state conversion
- [ ] Re-measure encode and decode performance

## Phase 3 — Buffer encoder output

- [ ] Replace repeated hot-loop `f.write(...)` calls with a `bytearray`
- [ ] Append header to the output buffer first
- [ ] Append chunk bytes to the buffer during encode
- [ ] Append `END_MARKER` to the buffer at the end
- [ ] Write the completed buffer once to disk
- [ ] Confirm encoded files still decode correctly
- [ ] Compare output size before vs after buffering
- [ ] Re-measure encode performance and record improvement

## Phase 4 — Reduce helper-call overhead

- [ ] Identify hottest helper calls in encode/decode paths
- [ ] Inline the hottest decode branch logic where helpful
- [ ] Inline the hottest encode branch logic where helpful
- [ ] Replace `read_sign_byte()` with direct arithmetic for QOI field decoding
- [ ] Bind frequently used constants to local variables in hot functions
- [ ] Bind frequently used methods locally if it improves hot-path performance
- [ ] Minimize temporary allocations inside branch-heavy code
- [ ] Re-run tests after each small refactor batch
- [ ] Re-measure encode/decode performance

## Phase 5 — Correctness hardening

- [ ] Verify DIFF encoding matches QOI bias rules
- [ ] Verify DIFF decoding matches QOI bias rules
- [ ] Verify LUMA encoding matches QOI bias rules
- [ ] Verify LUMA decoding matches QOI bias rules
- [ ] Verify index table updates happen on all required pixel-producing paths
- [ ] Verify RUN handling at boundaries (1 and 62)
- [ ] Verify end-marker handling is correct
- [ ] Decide whether to explicitly reject RGBA for now or implement it later
- [ ] Add targeted tests for DIFF boundary values
- [ ] Add targeted tests for LUMA boundary values
- [ ] Add targeted tests for RUN behavior
- [ ] Add targeted tests for INDEX reuse behavior

## Final validation

- [ ] Re-run full benchmark suite
- [ ] Compare final numbers against baseline
- [ ] Confirm RGB round-trip tests all pass
- [ ] Confirm code remains readable and documented
- [ ] Summarize changes and performance results in a short note or README update

## Nice-to-have follow-ups

- [ ] Split demo code from test code
- [ ] Add proper automated tests
- [ ] Add reference interoperability tests against a known-good QOI implementation
- [ ] Consider RGBA support after RGB path is stable
