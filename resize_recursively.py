from PIL import Image
import argparse
import multiprocessing
import functools
import math
from os.path import join
import os


def resize(path, out_path, maxPx, minPx):
    try:
        img = Image.open(path)
        width = img.size[0]
        height = img.size[1]
        smallest = min(width, height)
        largest = max(width, height)
        k = 1
        if largest > maxPx:
            k = maxPx / float(largest)
            smallest *= k
            largest *= k
        if smallest < minPx:
            k *= minPx / float(smallest)
        size = int(math.ceil(width * k)), int(math.ceil(height * k))
        img = img.resize(size, Image.ANTIALIAS)
        img.save(out_path + '/' + path.split('/')[-1], 'JPEG')
    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)


def resizeRecursively(original_dir, new_dir, path, max):
    for subdir, dirs, files in os.walk(path):
        paths = [join(subdir, f) for f in files]
        out_path = new_dir + subdir.replace(original_dir,'')
        if not os.path.exists(out_path):
            os.makedirs(out_path)
        pool.map(functools.partial(resize, out_path=out_path, minPx=224, maxPx=256), paths[:max])
        print "Completed dir: {}".format(out_path)
        for folder in dirs:
            resizeRecursively(original_dir, new_dir, join(subdir, folder), max = max)


if __name__ == '__main__':
    pool = multiprocessing.Pool()
    parser = argparse.ArgumentParser(
        description='Resize images'
    )
    parser.add_argument(
        '--input',
        type=str,
        help='Path to dir with images',
        required=True
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Path to dir where result images will be placed',
        required=True
    )
    parser.add_argument(
        '--max',
        type=int,
        help='Max images per category',
        required=True
    )

    args = parser.parse_args()
    in_dir = args.input
    out_dir = args.output

    try:
        resizeRecursively(original_dir=in_dir, path=in_dir, new_dir=out_dir, max=args.max)

    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)