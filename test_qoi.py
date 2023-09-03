import qoi
import matplotlib.pyplot as plt
import numpy as np
import time


if __name__ == "__main__":
    img_path = './data/background.jpg'
    output_dir = './output/'

    # Encode test
    start = time.time()
    img = plt.imread(img_path)
    assert qoi.qoi_encode(img, output_dir + 'test.qoi'), "encode fail."
    end = time.time()
    print(f"Encoding takes {end - start}s")

    # Decode test
    start = time.time()
    img_decode = qoi.qoi_decode('./output/test.qoi')
    end = time.time()
    print(f"Decoding takes {end - start}s")
    # plt.imshow(img_decode)
    # plt.show()
