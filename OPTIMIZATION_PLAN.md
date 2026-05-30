# QOI Python Optimization Plan

This plan is based on the identified `qoi.py` bottlenecks:

1. byte-at-a-time decoding
2. tiny NumPy operations in the hot loop
3. many tiny writes during encoding
4. too many helper calls / temporary allocations

## Goal

Improve the runtime performance of `qoi.py` while preserving behavior and keeping the implementation understandable.

## Guiding principles

- Prioritize changes with the highest impact on hot paths.
- Keep correctness verifiable after each step.
- Avoid mixing large refactors with behavior changes in the same pass.
- Measure before and after each phase where possible.

## Phase 0: Establish a baseline

### Tasks
- Add a small benchmark script or extend `test_qoi.py` to measure:
  - encode time
  - decode time
  - output size
- Use at least:
  - one photographic RGB image
  - one image with long runs / flat regions
  - one small sanity-check image
- Add round-trip checks:
  - `decoded.shape == original.shape`
  - pixel equality for supported RGB input

### Deliverables
- repeatable timing numbers
- round-trip validation for RGB paths

### Success criteria
- We can compare performance after every optimization phase.

---

## Phase 1: Remove byte-at-a-time decoding

### Problem
`qoi_decode()` currently performs repeated `f.read(1)` and `int.from_bytes(...)` calls in the inner loop, which adds heavy Python and file I/O overhead.

### Planned changes
- Read the encoded payload into memory once after the header.
- Parse bytes using an index pointer (`pos`) into `bytes` or `memoryview`.
- Replace patterns like:
  - `int.from_bytes(f.read(1), 'big')`
  - helper functions that depend on file reads
- Refactor decode helpers so they consume in-memory bytes rather than the file object.

### Expected impact
- Highest decode-side speedup.
- Simpler decode control flow.

### Risks
- Off-by-one parsing mistakes.
- End-marker handling bugs if parsing boundaries are not verified.

### Validation
- Round-trip test on multiple RGB images.
- Compare decoded arrays before vs after refactor.

---

## Phase 2: Replace tiny NumPy hot-loop operations with scalar state

### Problem
The codec uses NumPy for 3-element comparisons, tiny temporary arrays, and per-pixel arithmetic. This prevents vectorization benefits and adds overhead.

### Planned changes
- Replace per-pixel state arrays with Python integer scalars:
  - current pixel: `r, g, b`
  - previous pixel: `pr, pg, pb`
- Replace `np.array_equal(...)` pixel checks with scalar comparisons.
- Replace `np.asarray([r, g, b], dtype=np.uint8)` and tiny array additions with scalar arithmetic plus wraparound masking where needed.
- Consider storing the color index table as:
  - packed integers, or
  - tuples of RGB values

### Expected impact
- Significant speedup for both encode and decode hot loops.
- Reduced temporary allocations.

### Risks
- Wraparound behavior may change if masking logic is wrong.
- More manual state management can introduce subtle bugs.

### Validation
- Verify exact RGB round-trip behavior.
- Compare outputs from old and new implementations on the same sample set.

---

## Phase 3: Replace many tiny writes with buffered output assembly

### Problem
`qoi_encode()` writes many small chunks directly to the file, causing frequent Python calls and many small temporary `bytes` allocations.

### Planned changes
- Build encoded output in a `bytearray`.
- Append header, chunks, and end marker to the buffer.
- Write once at the end with a single `f.write(...)`.
- Replace `struct.pack(...)` use in the hottest chunk paths with direct byte append/extend where practical.

### Expected impact
- Noticeable encode-side speedup.
- Simpler output pipeline.

### Risks
- Higher peak memory use during encode.
- Incorrect chunk byte construction if refactoring is too aggressive.

### Validation
- Ensure generated files decode correctly.
- Compare encoded output against pre-refactor output for the same input, where behavior is unchanged.

---

## Phase 4: Reduce helper-call overhead and temporary allocations

### Problem
Small helper functions in tight loops create extra Python call overhead.

### Planned changes
- Inline the hottest encode/decode chunk handling logic where it improves clarity and speed.
- Replace `read_sign_byte()` with direct arithmetic for chunk decoding.
- Bind frequently used constants and methods to local variables inside hot functions where useful.
- Minimize temporary object creation in branch-heavy paths.

### Expected impact
- Moderate additional gain after Phases 1-3.
- Cleaner hot-path profiling results.

### Risks
- Reduced readability if inlining is overdone.

### Validation
- Keep branch-by-branch tests for RGB, INDEX, DIFF, LUMA, and RUN behavior.

---

## Phase 5: Correctness hardening before deeper optimization

### Problem
Performance work is less valuable if the implementation is not fully spec-aligned.

### Planned changes
- Review DIFF and LUMA encoding/decoding against QOI bias rules.
- Ensure index table updates happen for all required pixel-producing paths.
- Clarify supported input/output format assumptions.
- Keep RGBA explicitly unsupported until implemented, or add proper support later.

### Expected impact
- Better interoperability and safer optimization work.

### Risks
- Some “performance” regressions may actually be correctness fixes.

### Validation
- Add targeted tests for:
  - DIFF boundaries
  - LUMA boundaries
  - RUN boundaries
  - INDEX reuse behavior

---

## Suggested implementation order

1. Baseline measurement and round-trip checks
2. In-memory decode parsing
3. Scalar hot-loop state instead of tiny NumPy ops
4. Buffered encode output via `bytearray`
5. Helper inlining and temporary allocation cleanup
6. Correctness hardening and spec review

## Non-goals for the first pass

- Full RGBA support
- C extensions / Cython / Numba
- API redesign
- Packaging cleanup

## Definition of done

The optimization effort is complete when:

- encode and decode are measurably faster than baseline
- RGB round-trip tests pass consistently
- core chunk paths remain readable and maintainable
- no regressions are introduced in supported functionality

## Proposed output files for the work

- `OPTIMIZATION_PLAN.md` — this plan
- `bench_qoi.py` — optional benchmark script
- `tests/` or expanded `test_qoi.py` — validation coverage
