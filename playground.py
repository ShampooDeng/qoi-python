import qoi
import numpy as np
import matplotlib.pyplot as plt
import os


def qoi_encode(mat: np.ndarray, path, debug=False):
    height, width = mat.shape[0], mat.shape[1]
    # Flatten image matrix
    mat = mat.reshape((width * height, 3))
    with open(path, 'wb') as f:
        # Write qoi image header
        header = qoi.pack_qoi_header(width, height)
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
                    f.write(qoi.pack_qoi_op_run(run))
            else:
                # Write run chunk
                if run != 0:
                    f.write(qoi.pack_qoi_op_run(run))
                    # Clean run after write run chunk
                    run = 0
                # Process current pixel
                r = int(px[0])  # int(pixel value) to avoid overflow.
                g = int(px[1])
                b = int(px[2])
                index_pos = qoi.qoi_color_hash(r, g, b)
                if np.array_equal(index_table[index_pos], px):
                    f.write(qoi.pack_qoi_op_index(index_pos))
                else:
                    dr = r - int(px_pre[0])
                    dg = g - int(px_pre[1])
                    db = b - int(px_pre[2])
                    drg = dr - dg
                    dbg = db - dg
                    if (dr > -3 and dr < 2)\
                            and (dg > -3 and dg < 2)\
                            and (db > -3 and db < 2):
                        f.write(qoi.pack_qoi_op_diff(dr, dg, db))
                    elif (dg > -33 and dg < 32)\
                            and (drg > -9 and drg < 8)\
                            and (dbg > -9 and dbg < 8):
                        f.write(qoi.pack_qoi_op_luma(drg, dg, dbg))
                    else:
                        f.write(qoi.pack_qoi_op_rgb(r, g, b))
                        index_table[index_pos] = px
            px_pre = px
        f.write(qoi.END_MARKER)
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
    index_pos = qoi.qoi_color_hash(r, g, b)
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
        buffer = f.read(qoi.QOI_HEADER.size)
        header = qoi.Qoi_header()
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
            if buffer == qoi.QOI_TAG_RGB:
                px = decode_rgb(f, index_table)
            elif buffer == qoi.QOI_TAG_RGBA:
                pass
            else:
                tag = (buffer & 0xc0)
                if tag == qoi.QOI_TAG_RUN:
                    run = (buffer & 0x3f) + 1
                    run -= 1
                elif tag == qoi.QOI_TAG_DIFF:
                    px = decode_diff(buffer, px)
                elif tag == qoi.QOI_TAG_LUMA:
                    px = decode_luma(f, buffer, px)
                elif tag == qoi.QOI_TAG_INDEX:
                    px = decode_index(buffer, index_table)
            mat[mat_pos] = px
            mat_pos += 1
    return mat.reshape((header.height, header.width, 3))


def main():
    # img = plt.imread('./data/background.jpg')
    img = plt.imread('./data/background_small.jpg')
    # img = img[:200, :200, :]
    # np.save('./output/test', img)  # Save image matrix.
    # plt.imsave('./output/test.png', img)  # Save image in png.

    path = './output/test.qoi'
    # Encode image into qoi format
    qoi_encode(img, path)
    # Decode qoi image
    mat = qoi_decode(path)
    plt.subplot(211)
    plt.imshow(img)
    plt.subplot(212)
    plt.imshow(mat)
    plt.show()


def decode_test(write_case=False, show_case=True):
    # Doing a decode test
    path = './output/case.qoi'
    if write_case:
        path = './output/case0.qoi'
        write_test_case(path)
    mat = qoi_decode(path, True)
    if show_case:
        plt.imshow(mat)
        plt.show()
    np.save('./output/case', mat)


def write_test_case(path):
    """Write a qoi image for code test."""
    width, height = 10, 3
    # Flatten image matrix
    with open(path, 'wb') as f:
        # Writh qoi image header
        header = qoi.pack_qoi_header(width, height)
        f.write(header)
        # Write qoi chunks
        data = qoi.pack_qoi_op_rgb(78, 88, 98)
        f.write(data)
        # Run chunk
        data = qoi.pack_qoi_op_run(9)
        f.write(data)
        # rgb, diff, luma chunks
        data = qoi.pack_qoi_op_rgb(60, 60, 60)
        f.write(data)
        data = qoi.pack_qoi_op_diff(-2, -2, -2)
        f.write(data)
        data = qoi.pack_qoi_op_luma(-3, -30, -5)
        f.write(data)
        # rgb, index
        data = qoi.pack_qoi_op_rgb(133, 154, 96)
        index_pos = qoi.qoi_color_hash(133, 154, 96)
        f.write(data)
        data = qoi.pack_qoi_op_diff(1, 0, 1)
        f.write(data)
        data = qoi.pack_qoi_op_index(index_pos)
        f.write(data)
        data = qoi.pack_qoi_op_luma(2, 28, 5)
        f.write(data)
        data = qoi.pack_qoi_op_rgb(255, 255, 255)
        f.write(data)
        data = qoi.pack_qoi_op_run(12)
        f.write(data)
        f.write(qoi.END_MARKER)


def encode_test():
    mat = np.load('./output/case.npy')
    path = './output/case.qoi'
    qoi_encode(mat, path, True)
    with open(path, 'rb') as f:
        bytes = f.read(48)
        print(bytes)


if __name__ == "__main__":
    main()
    # encode_test()
    # decode_test(write_case=False, show_case=True)
