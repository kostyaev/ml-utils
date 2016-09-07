from PIL import Image
from os.path import join
import numpy as np
import os
import lmdb
import caffe
import sys
import math
import argparse
import random
import multiprocessing
import functools

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
        img = img.resize(size, Image.BILINEAR)
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


def chunks(l, n):
    return [l[i:i+n] for i in xrange(0, len(l), n)]


def prepare_image(path_label, max_side, min_side):
    try:
        img_path, label = path_label[0], path_label[1]
        img = open_image(img_path, max_side=max_side, min_side=min_side)
        datum = caffe.io.array_to_datum(img.astype(np.uint8))
        datum.label = label
        return img, datum.SerializeToString()
    except Exception as e:
        print e
        print "Skipped image {}".format(path_label[0])
        return None, None


def prepare_batch(batch):
    return pool.map(prepare_image_func, batch)

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


def create_lmdb(data, max_side, min_side, out_dir):
    mean_bgr = np.zeros((3, min_side, min_side)).astype(np.float32, copy=False)
    print mean_bgr.shape
    cnt = 0
    lmdb_dir = join(out_dir, 'lmdb')
    if not os.path.exists(lmdb_dir):
        os.makedirs(lmdb_dir)

    db = lmdb.open(lmdb_dir, map_size=int(1e12), map_async=True, writemap=True)
    txn = db.begin(write=True)
    for batch in chunks(data, 50):
        for img, datum_str in prepare_batch(batch):
            if img is not None:
                mean_bgr += img.astype(np.float32)
                str_id = '{:0>10d}'.format(cnt)
                txn.put(str_id, datum_str)
                cnt += 1

        string_ = str(cnt + 1) + ' / ' + str(len(data))
        sys.stdout.write("\r%s" % string_)
        sys.stdout.flush()

    txn.commit()
    db.close()

    print "\nFilling lmdb completed"

    mean_bgr /= cnt
    mean_bgr = mean_bgr[np.newaxis, :, :, :]
    blob = array_to_blobproto(mean_bgr)
    binaryproto_file = open(join(out_dir, 'mean.binaryproto'), 'wb' )
    binaryproto_file.write(blob.SerializeToString())
    binaryproto_file.close()
    np.save(join(out_dir, 'mean.npy'), mean_bgr)
    print "Image mean values for BGR: {0}".format(mean_bgr[0].mean(axis=1).mean(axis=1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description='Create lmdb for caffe'
    )
    parser.add_argument(
            '--data',
            type=str,
            help='Data file',
            required=True
    )
    parser.add_argument(
            '--out_dir',
            type=str,
            help='Output dir',
            required=True
    )
    parser.add_argument(
            '--max_side',
            type=int,
            help='Max size of larger dimension after resize',
            required=True
    )
    parser.add_argument(
            '--min_side',
            type=int,
            help='Min size of smaller dimension after resize. Has higher priority than --max',
            required=True
    )
    parser.add_argument(
            '--shuffle',
            type=bool,
            help='Enable shuffling of the data',
            default=False
    )

    args = parser.parse_args()
    prepare_image_func = functools.partial(prepare_image, max_side=args.max_side, min_side=args.min_side)

    pool = multiprocessing.Pool(processes=8)
    data = []
    for row in open(args.data):
        splits = row.rstrip('\n').split(' ')
        img_path = splits[0]
        label = int(splits[1])
        data.append((img_path, label))

    if args.shuffle:
        print "Shuffling the data"
        random.shuffle(data)


    print "Creating lmdb"

    create_lmdb(
            data=data,
            max_side=args.max_side,
            min_side=args.min_side,
            out_dir=args.out_dir)

    print "Completed."
