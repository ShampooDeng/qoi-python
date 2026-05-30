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

- [x] Refactor `qoi_decode()` to read payload bytes into memory once
- [x] Introduce a byte-position cursor (`pos`) for parsing
- [x] Replace `int.from_bytes(f.read(1), 'big')` in the decode loop
- [x] Refactor `decode_rgb()` to consume in-memory bytes instead of a file handle
- [x] Refactor `decode_luma()` to consume in-memory bytes instead of a file handle
- [x] Remove other per-byte file reads from decode helpers
- [x] Verify decode loop boundaries are correct (`pos` never overruns)
- [x] Re-run round-trip tests after the refactor
- [x] Re-measure decode performance and record improvement

## Phase 2 — Remove tiny NumPy ops from the hot path

- [x] Replace current/previous pixel NumPy arrays with scalar RGB state in encode
- [x] Replace current/previous pixel NumPy arrays with scalar RGB state in decode
- [x] Replace `np.array_equal(px, px_pre)` with scalar comparisons
- [x] Replace `np.array_equal(index_table[index_pos], px)` with scalar comparisons
- [x] Remove repeated tiny `np.asarray([...], dtype=np.uint8)` allocations in decode
- [x] Remove repeated tiny NumPy additions in `decode_diff()`
- [x] Remove repeated tiny NumPy additions in `decode_luma()`
- [x] Decide on index table representation:
  - [x] Option A: packed RGB integers
  - [ ] Option B: RGB tuples
- [x] Implement the chosen index table representation
- [x] Ensure wraparound behavior is preserved for channel arithmetic
- [x] Re-run round-trip tests after scalar-state conversion
- [x] Re-measure encode and decode performance

## Phase 3 — Buffer encoder output

- [x] Replace repeated hot-loop `f.write(...)` calls with a `bytearray`
- [x] Append header to the output buffer first
- [x] Append chunk bytes to the buffer during encode
- [x] Append `END_MARKER` to the buffer at the end
- [x] Write the completed buffer once to disk
- [x] Confirm encoded files still decode correctly
- [x] Compare output size before vs after buffering
- [x] Re-measure encode performance and record improvement

## Phase 4 — Reduce helper-call overhead

- [x] Identify hottest helper calls in encode/decode paths
- [x] Inline the hottest decode branch logic where helpful
- [x] Inline the hottest encode branch logic where helpful
- [x] Replace `read_sign_byte()` with direct arithmetic for QOI field decoding
- [x] Bind frequently used constants to local variables in hot functions
- [x] Bind frequently used methods locally if it improves hot-path performance
- [x] Minimize temporary allocations inside branch-heavy code
- [x] Re-run tests after each small refactor batch
- [x] Re-measure encode/decode performance

## Phase 5 — Correctness hardening

- [x] Verify DIFF encoding matches QOI bias rules
- [x] Verify DIFF decoding matches QOI bias rules
- [x] Verify LUMA encoding matches QOI bias rules
- [x] Verify LUMA decoding matches QOI bias rules
- [x] Verify index table updates happen on all required pixel-producing paths
- [x] Verify RUN handling at boundaries (1 and 62)
- [x] Verify end-marker handling is correct
- [x] Decide whether to explicitly reject RGBA for now or implement it later
- [x] Add targeted tests for DIFF boundary values
- [x] Add targeted tests for LUMA boundary values
- [x] Add targeted tests for RUN behavior
- [x] Add targeted tests for INDEX reuse behavior

## Final validation

- [x] Re-run full benchmark suite
- [x] Compare final numbers against baseline
- [x] Confirm RGB round-trip tests all pass
- [x] Confirm code remains readable and documented
- [x] Summarize changes and performance results in a short note or README update

## Nice-to-have follow-ups

- [ ] Split demo code from test code
- [ ] Add proper automated tests
- [ ] Add reference interoperability tests against a known-good QOI implementation
- [ ] Consider RGBA support after RGB path is stable
