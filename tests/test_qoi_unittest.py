import tempfile
import unittest
from pathlib import Path

import numpy as np

import qoi


class TestQoiHeaderAndPacking(unittest.TestCase):
    def test_pack_qoi_header_round_trip(self):
        buffer = qoi.pack_qoi_header(320, 240, channel_num=3, colorspace=1)

        self.assertEqual(len(buffer), qoi.QOI_HEADER.size)

        header = qoi.Qoi_header()
        header.read_buffer(buffer)

        self.assertEqual(header.width, 320)
        self.assertEqual(header.height, 240)
        self.assertEqual(header.channels, 3)
        self.assertEqual(header.colorspace, 1)

    def test_qoi_header_rejects_invalid_magic(self):
        header = qoi.Qoi_header()
        bad_buffer = b"bad!" + qoi.pack_qoi_header(1, 1)[4:]

        with self.assertRaises(AssertionError):
            header.read_buffer(bad_buffer)

    def test_end_marker_matches_expected_bytes(self):
        self.assertEqual(qoi.END_MARKER, b"\x00\x00\x00\x00\x00\x00\x00\x01")

    def test_pack_qoi_op_rgb_bytes(self):
        self.assertEqual(qoi.pack_qoi_op_rgb(1, 2, 3), b"\xfe\x01\x02\x03")

    def test_pack_qoi_op_rgba_bytes(self):
        self.assertEqual(qoi.pack_qoi_op_rgba(1, 2, 3, 4), b"\xff\x01\x02\x03\x04")

    def test_pack_qoi_op_index_accepts_full_valid_range(self):
        self.assertEqual(qoi.pack_qoi_op_index(0), b"\x00")
        self.assertEqual(qoi.pack_qoi_op_index(63), b"\x3f")

    def test_pack_qoi_op_index_rejects_out_of_range_values(self):
        with self.assertRaises(AssertionError):
            qoi.pack_qoi_op_index(-1)

        with self.assertRaises(AssertionError):
            qoi.pack_qoi_op_index(64)

    def test_pack_qoi_op_run_accepts_valid_bounds(self):
        self.assertEqual(qoi.pack_qoi_op_run(1), b"\xc0")
        self.assertEqual(qoi.pack_qoi_op_run(62), b"\xfd")

    def test_pack_qoi_op_run_rejects_out_of_range_values(self):
        with self.assertRaises(AssertionError):
            qoi.pack_qoi_op_run(0)

        with self.assertRaises(AssertionError):
            qoi.pack_qoi_op_run(63)

    def test_pack_qoi_op_diff_rejects_out_of_range_values(self):
        with self.assertRaises(AssertionError):
            qoi.pack_qoi_op_diff(-3, 0, 0)

        with self.assertRaises(AssertionError):
            qoi.pack_qoi_op_diff(0, 2, 0)

        with self.assertRaises(AssertionError):
            qoi.pack_qoi_op_diff(0, 0, -3)

    def test_pack_qoi_op_luma_rejects_out_of_range_values(self):
        with self.assertRaises(AssertionError):
            qoi.pack_qoi_op_luma(-9, 0, 0)

        with self.assertRaises(AssertionError):
            qoi.pack_qoi_op_luma(0, 32, 0)

        with self.assertRaises(AssertionError):
            qoi.pack_qoi_op_luma(0, 0, 8)

    def test_qoi_color_hash_matches_formula(self):
        self.assertEqual(
            qoi.qoi_color_hash(1, 2, 3), (1 * 3 + 2 * 5 + 3 * 7 + 255 * 11) % 64
        )

    def test_pack_and_unpack_rgb24_round_trip(self):
        packed = qoi.pack_rgb24(10, 20, 30)

        self.assertEqual(packed, (10 << 16) | (20 << 8) | 30)
        self.assertEqual(qoi.unpack_rgb24(packed), (10, 20, 30))


class TestQoiDecodeHelpers(unittest.TestCase):
    def test_read_sign_byte_for_2_bit_values(self):
        expected = {
            0b00: 0,
            0b01: 1,
            0b10: -2,
            0b11: -1,
        }
        for raw_value, decoded_value in expected.items():
            with self.subTest(raw_value=raw_value):
                self.assertEqual(qoi.read_sign_byte(raw_value, 2), decoded_value)

    def test_read_sign_byte_for_4_bit_values(self):
        self.assertEqual(qoi.read_sign_byte(0b0000, 4), 0)
        self.assertEqual(qoi.read_sign_byte(0b0111, 4), 7)
        self.assertEqual(qoi.read_sign_byte(0b1000, 4), -8)
        self.assertEqual(qoi.read_sign_byte(0b1111, 4), -1)

    def test_read_sign_byte_for_6_bit_values(self):
        self.assertEqual(qoi.read_sign_byte(0b000000, 6), 0)
        self.assertEqual(qoi.read_sign_byte(0b011111, 6), 31)
        self.assertEqual(qoi.read_sign_byte(0b100000, 6), -32)
        self.assertEqual(qoi.read_sign_byte(0b111111, 6), -1)

    def test_read_sign_byte_rejects_unknown_bit_width(self):
        self.assertIsNone(qoi.read_sign_byte(0, 3))

    def test_decode_rgb_reads_pixel_and_updates_index_table(self):
        index_table = [0] * 64
        payload = memoryview(b"\x0a\x14\x1e")

        r, g, b, pos = qoi.decode_rgb(payload, 0, index_table)

        index_pos = qoi.qoi_color_hash(10, 20, 30)

        self.assertEqual(pos, 3)
        self.assertEqual((r, g, b), (10, 20, 30))
        self.assertEqual(index_table[index_pos], qoi.pack_rgb24(10, 20, 30))

    def test_pack_and_decode_diff_round_trip(self):
        chunk = qoi.pack_qoi_op_diff(-2, 1, -1)

        decoded = qoi.decode_diff(chunk[0], 10, 20, 30)

        self.assertEqual(decoded, (8, 21, 29))

    def test_pack_and_decode_luma_round_trip(self):
        chunk = qoi.pack_qoi_op_luma(-3, -30, -5)

        r, g, b, pos = qoi.decode_luma(memoryview(chunk[1:]), 0, chunk[0], 58, 58, 58)

        self.assertEqual(pos, 1)
        self.assertEqual((r, g, b), (25, 28, 23))

    def test_decode_index_returns_cached_pixel(self):
        index_table = [0] * 64
        index_table[7] = qoi.pack_rgb24(99, 88, 77)

        px = qoi.decode_index(7, index_table)

        self.assertEqual(px, (99, 88, 77))


class TestQoiCodecIntegration(unittest.TestCase):
    def test_qoi_decode_returns_none_for_missing_file(self):
        self.assertIsNone(qoi.qoi_decode("./definitely_missing_file.qoi"))

    def test_encode_decode_round_trip_small_rgb_image(self):
        image = np.asarray(
            [
                [
                    [10, 20, 30],
                    [10, 20, 30],
                    [10, 20, 30],
                    [12, 21, 31],
                    [200, 100, 50],
                ],
                [[1, 2, 3], [5, 6, 7], [5, 6, 7], [12, 21, 31], [1, 2, 3]],
                [[255, 0, 0], [254, 1, 1], [222, 200, 100], [222, 200, 100], [0, 0, 0]],
            ],
            dtype=np.uint8,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "round_trip.qoi"
            result = qoi.qoi_encode(image, path)
            decoded = qoi.qoi_decode(path)

        self.assertEqual(result, 1)
        self.assertEqual(decoded.shape, image.shape)
        self.assertTrue(np.array_equal(decoded, image))

    def test_encoded_file_has_expected_header_and_end_marker(self):
        image = np.asarray(
            [
                [[1, 2, 3], [1, 2, 3]],
                [[4, 5, 6], [7, 8, 9]],
            ],
            dtype=np.uint8,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "encoded.qoi"
            qoi.qoi_encode(image, path)
            data = path.read_bytes()

        expected_header = qoi.pack_qoi_header(width=2, height=2)

        self.assertTrue(data.startswith(expected_header))
        self.assertTrue(data.endswith(qoi.END_MARKER))

    def test_manual_case_from_playground_decodes_to_expected_pixels(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "manual_case.qoi"
            self._write_manual_case(path)
            decoded = qoi.qoi_decode(path)

        expected_pixels = np.asarray(
            [[78, 88, 98]] * 10
            + [
                [60, 60, 60],
                [58, 58, 58],
                [25, 28, 23],
                [133, 154, 96],
                [134, 154, 97],
                [133, 154, 96],
                [163, 182, 129],
            ]
            + [[255, 255, 255]] * 13,
            dtype=np.uint8,
        ).reshape((3, 10, 3))

        self.assertEqual(decoded.shape, (3, 10, 3))
        self.assertTrue(np.array_equal(decoded, expected_pixels))

    @staticmethod
    def _write_manual_case(path: Path) -> None:
        with path.open("wb") as f:
            f.write(qoi.pack_qoi_header(10, 3))
            f.write(qoi.pack_qoi_op_rgb(78, 88, 98))
            f.write(qoi.pack_qoi_op_run(9))
            f.write(qoi.pack_qoi_op_rgb(60, 60, 60))
            f.write(qoi.pack_qoi_op_diff(-2, -2, -2))
            f.write(qoi.pack_qoi_op_luma(-3, -30, -5))
            f.write(qoi.pack_qoi_op_rgb(133, 154, 96))
            index_pos = qoi.qoi_color_hash(133, 154, 96)
            f.write(qoi.pack_qoi_op_diff(1, 0, 1))
            f.write(qoi.pack_qoi_op_index(index_pos))
            f.write(qoi.pack_qoi_op_luma(2, 28, 5))
            f.write(qoi.pack_qoi_op_rgb(255, 255, 255))
            f.write(qoi.pack_qoi_op_run(12))
            f.write(qoi.END_MARKER)


if __name__ == "__main__":
    unittest.main()
