import struct

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
        value = value | ((mask & diffs[i]) << 2*(2-i))

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
    return (r*3 + g*5 + b*7 + a*11) % 64


# def qoi_encode(path):
#     pass


# def qoi_decode():
#     pass
