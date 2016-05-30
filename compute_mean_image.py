import argparse
from PIL import Image
import numpy as np
import sys
import multiprocessing
import functools
import caffe
import math

def resize(img, max_side, min_side):
    try:
        width = img.size[0]
        height = img.size[1]
        smallest = min(width, height)
        largest = max(width, height)
        k = 1
        if largest > max_side:
            k = max_side / float(largest)
            smallest *= k
            largest *= k
        if smallest < min_side:
            k *= min_side / float(smallest)
        size = int(math.ceil(width * k)), int(math.ceil(height * k))
        img = img.resize(size, Image.ANTIALIAS)
        return img
    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)


def centered_crop(img, new_height, new_width):
    width = np.size(img, 1)
    height = np.size(img, 0)
    left = int(np.ceil((width - new_width) / 2.))
    top = int(np.ceil((height - new_height) / 2.))
    right = int(np.ceil((width + new_width) / 2.))
    bottom = int(np.ceil((height + new_height) / 2.))
    cImg = img[top:bottom, left:right]
    return cImg


def open_image(f, max_side, min_side):
    im = Image.open(f)
    im = resize(im, max_side=max_side, min_side=min_side)
    im = np.array(im)
    if im.ndim == 2:
        im = im[:, :, np.newaxis]
        im = np.tile(im, (1, 1, 3))
    elif im.shape[2] == 4:
        im = im[:, :, :3]
    im = centered_crop(im, min_side, min_side)
    im = im[:, :, ::-1]
    im = im.transpose((2,0,1))
    return im


def prepare_image(path_label, min_side):
    try:
        img_path = path_label[0]
        img = open_image(img_path, max_side=min_side, min_side=min_side)
        return img
    except Exception as e:
        print e
        print "Skipped image {}".format(path_label[0])
        return None


def prepare_all(data):
    return pool.map(prepare_image_func, data)

def chunks(l, n):
    return [l[i:i+n] for i in xrange(0, len(l), n)]

def array_to_blobproto(arr, diff=None):
    """Converts a N-dimensional array to blob proto. If diff is given, also
    convert the diff. You need to make sure that arr and diff have the same
    shape, and this function does not do sanity check.
    """
    blob = caffe.proto.caffe_pb2.BlobProto()
    blob.shape.dim.extend(arr.shape)
    blob.data.extend(arr.astype(float).flat)
    if diff is not None:
        blob.diff.extend(diff.astype(float).flat)
    return blob


def compute_mean(data, min_side, output):
    mean_bgr = np.zeros((3, min_side, min_side)).astype(np.float32, copy=False)
    cnt = 0
    print "Computing mean image..."
    batch_cnt = 0
    for batch in chunks(data, 100):
        mean_bgr_batch = np.zeros((3, min_side, min_side)).astype(np.float32, copy=False)
        i = 0
        batch_cnt += 1
        for img in prepare_all(batch):
            if img is not None:
                i += 1
                mean_bgr_batch += img.astype(np.float32)
                cnt += 1
                if cnt % 50 == 0:
                    string_ = str(cnt + 1) + ' / ' + str(len(data))
                    sys.stdout.write("\r%s" % string_)
                    sys.stdout.flush()
        mean_bgr += (mean_bgr_batch / i)

    mean_bgr /= batch_cnt
    mean_bgr = mean_bgr[np.newaxis, :, :, :]
    blob = array_to_blobproto(mean_bgr)
    binaryproto_file = open(output, 'wb')
    binaryproto_file.write(blob.SerializeToString())
    binaryproto_file.close()
    print "Image mean values for BGR: {0}".format(mean_bgr[0].mean(axis=1).mean(axis=1))
    print "Saved to {}".format(output)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description='Compute mean image for training set'
    )

    parser.add_argument(
            '--train',
            type=str,
            help='Train file',
            required=True
    )
    parser.add_argument(
            '--min_side',
            type=int,
            help='Train file',
            required=True
    )
    parser.add_argument(
            '--n',
            type=int,
            help='Sample size',
            required=True
    )
    parser.add_argument(
            '--output',
            type=str,
            help='Name of output file',
            required=True
    )

    args = parser.parse_args()
    prepare_image_func = functools.partial(prepare_image, min_side=args.min_side)
    pool = multiprocessing.Pool(processes=8)

    data = [tuple(line.rstrip('\n').split(' ')) for line in open(args.train)]
    compute_mean(data[:args.n], args.min_side, args.output)



