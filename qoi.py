import struct
import numpy as np
import os

QOI_HEADER = struct.Struct(">4sIIBB")
QOI_ENDER = struct.Struct(">BBBBBBBB")
QOI_OP_RGB = struct.Struct(">BBBB")
QOI_OP_RGBA = struct.Struct(">BBBBB")
QOI_OP_INDEX = struct.Struct(">B")
QOI_OP_DIFF = struct.Struct(">B")
QOI_OP_LUMA = struct.Struct(">BB")
QOI_OP_RUN = struct.Struct(">B")

QOI_TAG_RGB = 0xfe
QOI_TAG_RGBA = 0xff
QOI_TAG_INDEX = 0x00
QOI_TAG_DIFF = 0x40
QOI_TAG_LUMA = 0x80
QOI_TAG_RUN = 0xc0


class Qoi_header():
    def __init__(self):
        self.width = 0
        self.height = 0
        self.channels = 0
        self.colorspace = 0

    def read_buffer(self, buffer):
        data = QOI_HEADER.unpack(buffer)
        assert data[0] == b'qoif', "Input image is not qoi format"
        self.width = data[1]
        self.height = data[2]
        self.channels = data[3]
        self.colorspace = data[4]

    def show_attribute(self):
        print(f"width:{self.width},\
                height:{self.height},\
                channels:{self.channels},\
                colorspace:{self.colorspace}")


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

    magic_bytes = b'qoif'
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

    tag = 0xfe
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

    assert index >= 0 and index <= 63, "index out of range"
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
    value = 0  # Initial value
    tag = 0b01000000
    value = value | tag

    assert (dr <= 1 and dr >= -2)\
        and (dg <= 1 and dg >= -2)\
        and (db <= 1 and db >= -2), "dr, dg, db may out of range."

    diffs = [dr, dg, db]
    mask = 0b00000011
    for i in range(3):
        value = value | ((mask & diffs[i]) << 2 * (2 - i))

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
    tag = 0x80
    byte1, byte2 = 0, 0
    byte1 = tag | byte1

    assert (drg <= 7 and drg >= -8), "drg out of range"
    assert (dg <= 31 and dg >= -32), "dg out of range"
    assert (dbg <= 7 and dbg >= -8), "dbg out of range"

    mask_6 = 0x3f
    mask_4 = 0x0f
    byte1 = byte1 | ((mask_6 & dg))
    byte2 = byte2 | ((mask_4 & drg) << 4)
    byte2 = byte2 | ((mask_4 & dbg))

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
    tag = 0xc0  # b11000000
    assert (run_length > 0) and (run_length < 63), "run_length out of range"
    value = tag | (run_length - 1)
    return QOI_OP_RUN.pack(value)


def qoi_color_hash(r, g, b, a=255):
    return (r * 3 + g * 5 + b * 7 + a * 11) % 64


def qoi_encode(mat: np.ndarray, path, debug=False):
    height, width = mat.shape[0], mat.shape[1]
    # Flatten image matrix
    mat = mat.reshape((width * height, 3))
    with open(path, 'wb') as f:
        # Write qoi image header
        header = pack_qoi_header(width, height)
        f.write(header)
        # Encode image
        px_len = width * height
        px = np.zeros((3,), dtype=np.uint8)  # current pixel
        px_pre = px  # previous pixel
        run = 0  # run length
        mat_pos = 0  # image matrix index position
        index_table = np.zeros((64, 3), dtype=np.uint8)
        # Start encoding
        for mat_pos in range(px_len):
            px = mat[mat_pos]
            if np.array_equal(px, px_pre) and mat_pos != 0 and run < 62:
                run += 1
                # Write qoi end marker
                if mat_pos == px_len - 1:
                    f.write(pack_qoi_op_run(run))
            else:
                # Write run chunk
                if run != 0:
                    f.write(pack_qoi_op_run(run))
                    # Clean run after write run chunk
                    run = 0
                # Process current pixel
                r = int(px[0])  # int(pixel value) to avoid overflow.
                g = int(px[1])
                b = int(px[2])
                index_pos = qoi_color_hash(r, g, b)
                if np.array_equal(index_table[index_pos], px):
                    f.write(pack_qoi_op_index(index_pos))
                else:
                    dr = r - int(px_pre[0])
                    dg = g - int(px_pre[1])
                    db = b - int(px_pre[2])
                    drg = dr - dg
                    dbg = db - dg
                    if (dr > -3 and dr < 2)\
                            and (dg > -3 and dg < 2)\
                            and (db > -3 and db < 2):
                        f.write(pack_qoi_op_diff(dr, dg, db))
                    elif (dg > -33 and dg < 32)\
                            and (drg > -9 and drg < 8)\
                            and (dbg > -9 and dbg < 8):
                        f.write(pack_qoi_op_luma(drg, dg, dbg))
                    else:
                        f.write(pack_qoi_op_rgb(r, g, b))
                        index_table[index_pos] = px
            px_pre = px
        f.write(END_MARKER)
    return 1


def read_sign_byte(byte, bit):
    if bit == 2:
        mask = 0x02
        if (byte & mask) >> 1 == 1:
            byte = -1 - (~byte & 0x03)
    elif bit == 4:
        mask = 0x08
        if (byte & mask) >> 3 == 1:
            byte = -1 - (~byte & 0x0f)
    elif bit == 6:
        mask = 0x20
        if (byte & mask) >> 5 == 1:
            byte = -1 - (~byte & 0x3f)
    else:
        return None
    return byte


def decode_rgb(f, index_table):
    r = int.from_bytes(f.read(1), 'big')
    g = int.from_bytes(f.read(1), 'big')
    b = int.from_bytes(f.read(1), 'big')
    px = np.asarray([r, g, b], dtype=np.uint8)
    # Assign index table
    index_pos = qoi_color_hash(r, g, b)
    index_table[index_pos] = px
    return px


def decode_diff(buffer, px, debug=False):
    dr = (buffer & 0x30) >> 4
    dr = read_sign_byte(dr, 2)
    dg = (buffer & 0x0c) >> 2
    dg = read_sign_byte(dg, 2)
    db = (buffer & 0x03)
    db = read_sign_byte(db, 2)
    px = (px + np.asarray([dr, dg, db])).astype(np.uint8)
    if debug:
        print('diff')
        print(bin(buffer))
        print(dr, dg, db)
    return px


def decode_luma(f, buffer, px, debug=False):
    dg = (buffer & 0x3f)
    dg = read_sign_byte(dg, 6)
    another_buffer = int.from_bytes(f.read(1), 'big')
    drg = (another_buffer & 0xf0) >> 4
    drg = read_sign_byte(drg, 4)
    dbg = another_buffer & 0x0f
    dbg = read_sign_byte(dbg, 4)
    dr = drg + dg
    db = dbg + dg
    px = (px + np.asarray([dr, dg, db])).astype(np.uint8)
    if debug:
        print('luma')
        print(bin(another_buffer))
        print(drg, dg, dbg)
        print(dr, dg, db)
        print(px.dtype)
    return px


def decode_index(buffer, index_table):
    index_pos = buffer & 0x3f
    px = index_table[index_pos]
    return px


def qoi_decode(path, debug=False):
    # Check if path is valid
    if not os.path.isfile(path):
        return None
    with open(path, 'rb') as f:
        # Read qoi image header
        buffer = f.read(QOI_HEADER.size)
        header = Qoi_header()
        header.read_buffer(buffer)
        if debug:
            header.show_attribute()
        # Decode qoi chunks
        px_len = header.width * header.height
        px = np.zeros((3,), dtype=np.uint8)
        mat = np.zeros((px_len, 3), dtype=np.uint8)  # flattened image matrix
        mat_pos = 0
        run = 0
        index_table = np.zeros((64, 3), dtype=np.uint8)
        # Start decoding
        while mat_pos < px_len:
            # Decode run chunk
            if run != 0:
                run -= 1
                mat[mat_pos] = px
                mat_pos += 1
                continue
            buffer = int.from_bytes(f.read(1), 'big')
            if buffer == QOI_TAG_RGB:
                px = decode_rgb(f, index_table)
            elif buffer == QOI_TAG_RGBA:
                pass
            else:
                tag = (buffer & 0xc0)
                if tag == QOI_TAG_RUN:
                    run = (buffer & 0x3f) + 1
                    run -= 1
                elif tag == QOI_TAG_DIFF:
                    px = decode_diff(buffer, px)
                elif tag == QOI_TAG_LUMA:
                    px = decode_luma(f, buffer, px)
                elif tag == QOI_TAG_INDEX:
                    px = decode_index(buffer, index_table)
            mat[mat_pos] = px
            mat_pos += 1
    return mat.reshape((header.height, header.width, 3))
