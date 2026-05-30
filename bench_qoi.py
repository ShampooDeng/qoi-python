from __future__ import annotations

import argparse
import gc
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from matplotlib import image as mpimg

import qoi

ROOT = Path(__file__).resolve().parent
PHOTO_PATH = ROOT / "data" / "background.jpg"


def ensure_rgb_uint8(image: np.ndarray) -> np.ndarray:
    if image.ndim != 3 or image.shape[2] < 3:
        raise ValueError(f"Expected an RGB-like image, got shape={image.shape!r}")

    image = image[..., :3]
    if image.dtype == np.uint8:
        return np.ascontiguousarray(image)

    if np.issubdtype(image.dtype, np.floating):
        if float(np.max(image)) <= 1.0:
            image = image * 255.0
        image = np.rint(np.clip(image, 0.0, 255.0)).astype(np.uint8)
        return np.ascontiguousarray(image)

    return np.ascontiguousarray(np.clip(image, 0, 255).astype(np.uint8))


def load_photographic_image() -> np.ndarray:
    if not PHOTO_PATH.is_file():
        raise FileNotFoundError(f"Missing benchmark image: {PHOTO_PATH}")
    return ensure_rgb_uint8(mpimg.imread(PHOTO_PATH))


def make_flat_regions_image() -> np.ndarray:
    image = np.zeros((256, 256, 3), dtype=np.uint8)
    palette = np.asarray(
        [
            [12, 12, 12],
            [30, 90, 180],
            [240, 240, 240],
            [200, 50, 50],
            [50, 160, 70],
            [80, 40, 200],
            [0, 0, 0],
            [255, 255, 255],
        ],
        dtype=np.uint8,
    )

    for row_block in range(8):
        for col_block in range(8):
            y0 = row_block * 32
            y1 = y0 + 32
            x0 = col_block * 32
            x1 = x0 + 32
            image[y0:y1, x0:x1] = palette[(row_block + col_block) % len(palette)]

    return image


def make_small_sanity_image() -> np.ndarray:
    return np.asarray(
        [
            [[10, 20, 30], [10, 20, 30], [10, 20, 30], [12, 21, 31], [200, 100, 50]],
            [[1, 2, 3], [5, 6, 7], [5, 6, 7], [12, 21, 31], [1, 2, 3]],
            [[255, 0, 0], [254, 1, 1], [222, 200, 100], [222, 200, 100], [0, 0, 0]],
        ],
        dtype=np.uint8,
    )


def measure_encode(
    image: np.ndarray, path: Path, repeats: int, warmups: int
) -> list[float]:
    timings: list[float] = []
    total_runs = warmups + repeats
    for run_idx in range(total_runs):
        gc.collect()
        start = time.perf_counter()
        qoi.qoi_encode(image, path)
        elapsed = time.perf_counter() - start
        if run_idx >= warmups:
            timings.append(elapsed)
    return timings


def measure_decode(path: Path, repeats: int, warmups: int) -> list[float]:
    timings: list[float] = []
    total_runs = warmups + repeats
    for run_idx in range(total_runs):
        gc.collect()
        start = time.perf_counter()
        decoded = qoi.qoi_decode(path)
        elapsed = time.perf_counter() - start
        if decoded is None:
            raise RuntimeError(f"Decode failed for {path}")
        if run_idx >= warmups:
            timings.append(elapsed)
    return timings


def format_ms(seconds: float) -> str:
    return f"{seconds * 1000:.3f} ms"


def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.2f} KiB"
    return f"{size / (1024 * 1024):.2f} MiB"


def benchmark_case(
    name: str, image: np.ndarray, repeats: int, warmups: int
) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / f"{name}.qoi"

        qoi.qoi_encode(image, output_path)
        decoded = qoi.qoi_decode(output_path)
        if decoded is None:
            raise RuntimeError(f"Decode failed for benchmark case {name}")

        if decoded.shape != image.shape:
            raise AssertionError(
                f"Round-trip shape mismatch for {name}: decoded={decoded.shape}, original={image.shape}"
            )
        if not np.array_equal(decoded, image):
            raise AssertionError(f"Round-trip pixel mismatch for {name}")

        encoded_size = output_path.stat().st_size
        encode_timings = measure_encode(
            image, output_path, repeats=repeats, warmups=warmups
        )
        decode_timings = measure_decode(output_path, repeats=repeats, warmups=warmups)

        return {
            "name": name,
            "shape": image.shape,
            "encoded_size": encoded_size,
            "encode_mean": statistics.mean(encode_timings),
            "encode_median": statistics.median(encode_timings),
            "decode_mean": statistics.mean(decode_timings),
            "decode_median": statistics.median(decode_timings),
        }


def print_report(results: list[dict[str, object]], repeats: int, warmups: int) -> None:
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")
    print(f"Benchmark repeats={repeats}, warmups={warmups}")
    print()

    header = (
        f"{'case':<18} {'shape':<18} {'size':>12} {'encode mean':>14} "
        f"{'encode median':>15} {'decode mean':>14} {'decode median':>15}"
    )
    print(header)
    print("-" * len(header))

    for result in results:
        print(
            f"{result['name']:<18} "
            f"{str(result['shape']):<18} "
            f"{format_bytes(int(result['encoded_size'])):>12} "
            f"{format_ms(float(result['encode_mean'])):>14} "
            f"{format_ms(float(result['encode_median'])):>15} "
            f"{format_ms(float(result['decode_mean'])):>14} "
            f"{format_ms(float(result['decode_median'])):>15}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 0 QOI benchmark runner")
    parser.add_argument(
        "--repeats", type=int, default=5, help="Measured iterations per case"
    )
    parser.add_argument(
        "--warmups", type=int, default=1, help="Warm-up iterations per case"
    )
    args = parser.parse_args()

    cases = [
        ("photographic_rgb", load_photographic_image()),
        ("flat_regions", make_flat_regions_image()),
        ("small_sanity", make_small_sanity_image()),
    ]

    results = [
        benchmark_case(name, image, repeats=args.repeats, warmups=args.warmups)
        for name, image in cases
    ]
    print_report(results, repeats=args.repeats, warmups=args.warmups)


if __name__ == "__main__":
    main()
