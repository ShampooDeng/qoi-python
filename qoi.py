import os
import struct

import numpy as np

QOI_HEADER = struct.Struct(">4sIIBB")
QOI_ENDER = struct.Struct(">BBBBBBBB")
QOI_OP_RGB = struct.Struct(">BBBB")
QOI_OP_RGBA = struct.Struct(">BBBBB")
QOI_OP_INDEX = struct.Struct(">B")
QOI_OP_DIFF = struct.Struct(">B")
QOI_OP_LUMA = struct.Struct(">BB")
QOI_OP_RUN = struct.Struct(">B")

QOI_TAG_RGB = 0xFE
QOI_TAG_RGBA = 0xFF
QOI_TAG_INDEX = 0x00
QOI_TAG_DIFF = 0x40
QOI_TAG_LUMA = 0x80
QOI_TAG_RUN = 0xC0
QOI_RGB_HASH_SEED = (255 * 11) % 64


class Qoi_header:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.channels = 0
        self.colorspace = 0

    def read_buffer(self, buffer):
        data = QOI_HEADER.unpack(buffer)
        assert data[0] == b"qoif", "Input image is not qoi format"
        self.width = data[1]
        self.height = data[2]
        self.channels = data[3]
        self.colorspace = data[4]

    def show_attribute(self):
        print(
            f"width:{self.width},"
            f"                height:{self.height},"
            f"                channels:{self.channels},"
            f"                colorspace:{self.colorspace}"
        )


def pack_qoi_header(width, height, channel_num=3, colorspace=1):
    """
    struct qoi_header_t {
        char     magic[4];   // magic bytes "qoif"
        uint32_t width;      // image width in pixels (BE)
        uint32_t height;     // image height in pixels (BE)
        uint8_t  channels;   // 3 = RGB, 4 = RGBA
        uint8_t  colorspace; // 0 = sRGB with linear alpha, 1 = all channels linear
    };
    """

    magic_bytes = b"qoif"
    value = (magic_bytes, width, height, channel_num, colorspace)
    return QOI_HEADER.pack(*value)


"""
The byte stream's end is marked with 7 0x00 bytes followed by a
single 0x01 byte
char qoi_end;
"""
END_MARKER = QOI_ENDER.pack(0, 0, 0, 0, 0, 0, 0, 1)


def pack_qoi_op_rgb(red_val, green_val, blue_val):
    """
    .- QOI_OP_RGB ------------------------------------------.
    |         Byte[0]         | Byte[1] | Byte[2] | Byte[3] |
    |  7  6  5  4  3  2  1  0 | 7 .. 0  | 7 .. 0  | 7 .. 0  |
    |-------------------------+---------+---------+---------|
    |  1  1  1  1  1  1  1  0 |   red   |  green  |  blue   |
    `-------------------------------------------------------`
    8-bit tag b11111110
    8-bit   red channel value
    8-bit green channel value
    8-bit  blue channel value
    """

    tag = 0xFE
    value = (tag, red_val, green_val, blue_val)
    return QOI_OP_RGB.pack(*value)


def pack_qoi_op_rgba(red_val, green_val, blue_val, alpha_val):
    """
    .- QOI_OP_RGBA ---------------------------------------------------.
    |         Byte[0]         | Byte[1] | Byte[2] | Byte[3] | Byte[4] |
    |  7  6  5  4  3  2  1  0 | 7 .. 0  | 7 .. 0  | 7 .. 0  | 7 .. 0  |
    |-------------------------+---------+---------+---------+---------|
    |  1  1  1  1  1  1  1  1 |   red   |  green  |  blue   |  alpha  |
    `-----------------------------------------------------------------`
    8-bit tag b11111111
    8-bit   red channel value
    8-bit green channel value
    8-bit  blue channel value
    8-bit alpha channel value
    """

    tag = 255
    value = (tag, red_val, green_val, blue_val, alpha_val)
    return QOI_OP_RGBA.pack(*value)


def pack_qoi_op_index(index):
    """
    .- QOI_OP_INDEX ----------.
    |         Byte[0]         |
    |  7  6  5  4  3  2  1  0 |
    |-------+-----------------|
    |  0  0 |     index       |
    `-------------------------`
    2-bit tag b00
    6-bit index into the color index array: 0..63

    A valid encoder must not issue 2 or more consecutive QOI_OP_INDEX
    chunks to the same index. QOI_OP_RUN should be used instead.
    """

    assert 0 <= index <= 63, "index out of range"
    return QOI_OP_INDEX.pack(index)


def pack_qoi_op_diff(dr, dg, db):
    """
    .- QOI_OP_DIFF -----------.
    |         Byte[0]         |
    |  7  6  5  4  3  2  1  0 |
    |-------+-----+-----+-----|
    |  0  1 |  dr |  dg |  db |
    `-------------------------`
    2-bit tag b01
    2-bit   red channel difference from the previous pixel between -2..1
    2-bit green channel difference from the previous pixel between -2..1
    2-bit  blue channel difference from the previous pixel between -2..1

    The difference to the current channel values are using a wraparound operation,
    so "1 - 2" will result in 255, while "255 + 1" will result in 0.

    Values are stored as unsigned integers with a bias of 2. E.g. -2 is stored as
    0 (b00). 1 is stored as 3 (b11).

    The alpha value remains unchanged from the previous pixel.
    """
    assert (
        (dr <= 1 and dr >= -2) and (dg <= 1 and dg >= -2) and (db <= 1 and db >= -2)
    ), "dr, dg, db may out of range."

    value = QOI_TAG_DIFF | ((dr + 2) << 4) | ((dg + 2) << 2) | (db + 2)
    return QOI_OP_DIFF.pack(value)


def pack_qoi_op_luma(drg, dg, dbg):
    """
    .- QOI_OP_LUMA -------------------------------------.
    |         Byte[0]         |         Byte[1]         |
    |  7  6  5  4  3  2  1  0 |  7  6  5  4  3  2  1  0 |
    |-------+-----------------+-------------+-----------|
    |  1  0 |  green diff     |   dr - dg   |  db - dg  |
    `---------------------------------------------------`
    2-bit tag b10
    6-bit green channel difference from the previous pixel -32..31
    4-bit   red channel difference minus green channel difference -8..7
    4-bit  blue channel difference minus green channel difference -8..7

    The green channel is used to indicate the general direction of change and is
    encoded in 6 bits. The red and blue channels (dr and db) base their diffs off
    of the green channel difference and are encoded in 4 bits. I.e.:
        dr_dg = (cur_px.r - prev_px.r) - (cur_px.g - prev_px.g)
        db_dg = (cur_px.b - prev_px.b) - (cur_px.g - prev_px.g)

    The difference to the current channel values are using a wraparound operation,
    so "10 - 13" will result in 253, while "250 + 7" will result in 1.

    Values are stored as unsigned integers with a bias of 32 for the green channel
    and a bias of 8 for the red and blue channel.

    The alpha value remains unchanged from the previous pixel.
    """
    assert -8 <= drg <= 7, "drg out of range"
    assert -32 <= dg <= 31, "dg out of range"
    assert -8 <= dbg <= 7, "dbg out of range"

    byte1 = QOI_TAG_LUMA | (dg + 32)
    byte2 = ((drg + 8) << 4) | (dbg + 8)
    return QOI_OP_LUMA.pack(byte1, byte2)


def pack_qoi_op_run(run_length):
    """
    .- QOI_OP_RUN ------------.
    |         Byte[0]         |
    |  7  6  5  4  3  2  1  0 |
    |-------+-----------------|
    |  1  1 |       run       |
    `-------------------------`
    2-bit tag b11
    6-bit run-length repeating the previous pixel: 1..62

    The run-length is stored with a bias of -1. Note that the run-lengths 63 and 64
    (b111110 and b111111) are illegal as they are occupied by the QOI_OP_RGB and
    QOI_OP_RGBA tags.
    """
    tag = 0xC0
    assert (run_length > 0) and (run_length < 63), "run_length out of range"
    value = tag | (run_length - 1)
    return QOI_OP_RUN.pack(value)


def qoi_color_hash(r, g, b, a=255):
    return (r * 3 + g * 5 + b * 7 + a * 11) % 64


def pack_rgb24(r, g, b):
    return (r << 16) | (g << 8) | b


def unpack_rgb24(value):
    return (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF


def qoi_encode(mat: np.ndarray, path, debug=False):
    del debug

    if mat.ndim != 3:
        raise ValueError("Expected image array with shape (height, width, channels)")
    if mat.shape[2] == 4:
        raise NotImplementedError("RGBA images are not supported")
    if mat.shape[2] != 3:
        raise ValueError("Only 3-channel RGB images are supported")

    height, width = mat.shape[0], mat.shape[1]
    mat = mat.reshape((width * height, 3))

    out = bytearray()
    out.extend(pack_qoi_header(width, height))
    out_append = out.append

    px_len = width * height
    pr = 0
    pg = 0
    pb = 0
    run = 0
    hash_seed = QOI_RGB_HASH_SEED
    index_table = [0] * 64

    for mat_pos in range(px_len):
        px = mat[mat_pos]
        r = int(px[0])
        g = int(px[1])
        b = int(px[2])

        if r == pr and g == pg and b == pb and mat_pos != 0 and run < 62:
            run += 1
            if mat_pos == px_len - 1:
                out_append(QOI_TAG_RUN | (run - 1))
        else:
            if run != 0:
                out_append(QOI_TAG_RUN | (run - 1))
                run = 0

            packed_px = (r << 16) | (g << 8) | b
            index_pos = (r * 3 + g * 5 + b * 7 + hash_seed) & 63
            if index_table[index_pos] == packed_px:
                out_append(index_pos)
            else:
                dr = r - pr
                dg = g - pg
                db = b - pb
                drg = dr - dg
                dbg = db - dg
                if (-3 < dr < 2) and (-3 < dg < 2) and (-3 < db < 2):
                    out_append(
                        QOI_TAG_DIFF | ((dr + 2) << 4) | ((dg + 2) << 2) | (db + 2)
                    )
                elif (-33 < dg < 32) and (-9 < drg < 8) and (-9 < dbg < 8):
                    out_append(QOI_TAG_LUMA | (dg + 32))
                    out_append(((drg + 8) << 4) | (dbg + 8))
                else:
                    out_append(QOI_TAG_RGB)
                    out_append(r)
                    out_append(g)
                    out_append(b)

            index_table[index_pos] = packed_px

        pr = r
        pg = g
        pb = b

    out.extend(END_MARKER)
    with open(path, "wb") as f:
        f.write(out)
    return 1


def read_sign_byte(byte, bit):
    if bit == 2:
        mask = 0x02
        if (byte & mask) >> 1 == 1:
            byte = -1 - (~byte & 0x03)
    elif bit == 4:
        mask = 0x08
        if (byte & mask) >> 3 == 1:
            byte = -1 - (~byte & 0x0F)
    elif bit == 6:
        mask = 0x20
        if (byte & mask) >> 5 == 1:
            byte = -1 - (~byte & 0x3F)
    else:
        return None
    return byte


def decode_rgb(payload, pos, index_table):
    if pos + 3 > len(payload):
        raise AssertionError("Unexpected end of QOI payload while reading QOI_OP_RGB")

    r = payload[pos]
    g = payload[pos + 1]
    b = payload[pos + 2]
    pos += 3

    index_pos = qoi_color_hash(r, g, b)
    index_table[index_pos] = pack_rgb24(r, g, b)
    return r, g, b, pos


def decode_diff(buffer, r, g, b, debug=False):
    dr = ((buffer >> 4) & 0x03) - 2
    dg = ((buffer >> 2) & 0x03) - 2
    db = (buffer & 0x03) - 2
    r = (r + dr) & 0xFF
    g = (g + dg) & 0xFF
    b = (b + db) & 0xFF
    if debug:
        print("diff")
        print(bin(buffer))
        print(dr, dg, db)
    return r, g, b


def decode_luma(payload, pos, buffer, r, g, b, debug=False):
    dg = (buffer & 0x3F) - 32
    if pos >= len(payload):
        raise AssertionError("Unexpected end of QOI payload while reading QOI_OP_LUMA")

    another_buffer = payload[pos]
    pos += 1
    drg = ((another_buffer >> 4) & 0x0F) - 8
    dbg = (another_buffer & 0x0F) - 8
    dr = drg + dg
    db = dbg + dg
    r = (r + dr) & 0xFF
    g = (g + dg) & 0xFF
    b = (b + db) & 0xFF
    if debug:
        print("luma")
        print(bin(another_buffer))
        print(drg, dg, dbg)
        print(dr, dg, db)
    return r, g, b, pos


def decode_index(buffer, index_table):
    index_pos = buffer & 0x3F
    return unpack_rgb24(index_table[index_pos])


def qoi_decode(path, debug=False):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        buffer = f.read(QOI_HEADER.size)
        header = Qoi_header()
        header.read_buffer(buffer)
        if debug:
            header.show_attribute()

        if header.channels == 4:
            raise NotImplementedError("RGBA images are not supported")
        if header.channels != 3:
            raise ValueError(f"Unsupported channel count: {header.channels}")

        payload = memoryview(f.read())

    px_len = header.width * header.height
    r = 0
    g = 0
    b = 0
    mat = np.zeros((px_len, 3), dtype=np.uint8)
    mat_pos = 0
    run = 0
    pos = 0
    payload_len = len(payload)
    hash_seed = QOI_RGB_HASH_SEED
    index_table = [0] * 64

    while mat_pos < px_len:
        if run != 0:
            run -= 1
            mat[mat_pos, 0] = r
            mat[mat_pos, 1] = g
            mat[mat_pos, 2] = b
            mat_pos += 1
            continue

        if pos >= payload_len:
            raise AssertionError("Unexpected end of QOI payload while decoding image")

        buffer = payload[pos]
        pos += 1
        if buffer == QOI_TAG_RGB:
            if pos + 3 > payload_len:
                raise AssertionError(
                    "Unexpected end of QOI payload while reading QOI_OP_RGB"
                )

            r = payload[pos]
            g = payload[pos + 1]
            b = payload[pos + 2]
            pos += 3
        elif buffer == QOI_TAG_RGBA:
            raise NotImplementedError("RGBA images are not supported")
        else:
            tag = buffer & 0xC0
            if tag == QOI_TAG_RUN:
                run = buffer & 0x3F
            elif tag == QOI_TAG_DIFF:
                r = (r + ((buffer >> 4) & 0x03) - 2) & 0xFF
                g = (g + ((buffer >> 2) & 0x03) - 2) & 0xFF
                b = (b + (buffer & 0x03) - 2) & 0xFF
            elif tag == QOI_TAG_LUMA:
                if pos >= payload_len:
                    raise AssertionError(
                        "Unexpected end of QOI payload while reading QOI_OP_LUMA"
                    )

                dg = (buffer & 0x3F) - 32
                another_buffer = payload[pos]
                pos += 1
                r = (r + dg + ((another_buffer >> 4) & 0x0F) - 8) & 0xFF
                g = (g + dg) & 0xFF
                b = (b + dg + (another_buffer & 0x0F) - 8) & 0xFF
            elif tag == QOI_TAG_INDEX:
                packed = index_table[buffer & 0x3F]
                r = (packed >> 16) & 0xFF
                g = (packed >> 8) & 0xFF
                b = packed & 0xFF

        packed = (r << 16) | (g << 8) | b
        index_table[(r * 3 + g * 5 + b * 7 + hash_seed) & 63] = packed
        mat[mat_pos, 0] = r
        mat[mat_pos, 1] = g
        mat[mat_pos, 2] = b
        mat_pos += 1

    if payload[pos:].tobytes() != END_MARKER:
        raise AssertionError("Missing or invalid QOI end marker")

    return mat.reshape((header.height, header.width, 3))
