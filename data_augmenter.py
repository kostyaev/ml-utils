from PIL import Image
from os import listdir
from os.path import join
import argparse
import multiprocessing
import functools


def resize(path, maxPx, minPx):
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
        size = width * k, height * k
        img.thumbnail(size, Image.ANTIALIAS)
        return img
    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)

def quality(image, name, out_path):
    image.save(join(out_path, name + "-{0}.JPEG".format("q90")), quality=90)
    image.save(join(out_path + name + "-{0}.JPEG".format("q20")), quality=20)

def rotate(img, name, out_path):
    quality(img, name, out_path)
    quality(img.rotate(90), name+"-r90", out_path)
    quality(img.rotate(180), name+"-r180", out_path)
    quality(img.rotate(270), name+"-r270", out_path)

def resizeAll(name, in_path, out_path):
    new_name = name.replace(".JPEG", "")
    rotate(resize(join(in_path, name), 256, 224), new_name+"-s256", out_path)
    rotate(resize(join(in_path, name), 300, 224), new_name+"-s300", out_path)
    rotate(resize(join(in_path, name), 384, 224), new_name+"-s384", out_path)
    print name



if __name__ == '__main__':
    pool = multiprocessing.Pool()
    parser = argparse.ArgumentParser(
        description='Generate samples from original images'
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

    args = parser.parse_args()
    in_dir = args.input
    out_dir = args.output

    try:
        files = [f for f in listdir(in_dir) if f.endswith(".JPEG")]
        result = pool.map(functools.partial(resizeAll, in_path=in_dir, out_path=out_dir), files)
        result.get(timeout=60*10)

    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)