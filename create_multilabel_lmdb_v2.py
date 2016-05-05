from PIL import Image
import numpy as np
import lmdb
import caffe
import sys
import math
import argparse
import random
import pickle
from os.path import join
import os
import multiprocessing
import functools


def save_obj(obj, name ):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name ):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)

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

def chunks(l, n):
    return [l[i:i+n] for i in xrange(0, len(l), n)]


def prepare_image(pair, max_side, min_side):
    img_path, labels = pair[0], pair[1]
    try:
        img = open_image(img_path, max_side=max_side, min_side=min_side)
        labels = np.array(labels).astype(float).reshape(1, 1, len(labels))
        im_dat = caffe.io.array_to_datum(img.astype(np.uint8))
        label_dat = caffe.io.array_to_datum(labels)
        return img, im_dat.SerializeToString(), label_dat.SerializeToString()
    except Exception as e:
        print e
        print "Skipped image {}".format(img_path)
        return None, None, None


def prepare_batch(batch):
    return pool.map(prepare_image_func, batch)


def fillLmdb(images, labels, max_side, min_side, output_dir):
    mean_bgr = np.zeros((3, min_side, min_side)).astype(np.float32, copy=False)
    img_lmdb_dir = join(output_dir, "img_lmdb")
    label_lmdb_dir = join(output_dir, "label_lmdb")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    images_db = lmdb.open(img_lmdb_dir, map_size=int(1e12), map_async=True, writemap=True)
    labels_db = lmdb.open(label_lmdb_dir, map_size=int(1e12))

    images_txn = images_db.begin(write=True)
    labels_txn = labels_db.begin(write=True)

    examples = zip(images, labels)

    cnt = 0
    for batch in chunks(examples, 50):
        for img, img_dat, lab_dat in prepare_batch(batch):
            if img is not None:
                mean_bgr += img.astype(np.float32)
                images_txn.put('{:0>10d}'.format(cnt), img_dat)
                labels_txn.put('{:0>10d}'.format(cnt), lab_dat)
                cnt += 1
        string_ = str(cnt + 1) + ' / ' + str(len(examples))
        sys.stdout.write("\r%s" % string_)
        sys.stdout.flush()

    images_txn.commit()
    labels_txn.commit()
    images_db.close()
    labels_db.close()

    print "\nFilling lmdb completed"
    mean_bgr /= cnt
    mean_bgr = mean_bgr[np.newaxis, :, :, :]
    blob = array_to_blobproto(mean_bgr)
    binaryproto_file = open(join(output_dir, 'mean.binaryproto'), 'wb')
    binaryproto_file.write(blob.SerializeToString())
    binaryproto_file.close()
    np.save(join(output_dir, 'mean.npy'), mean_bgr)
    print "Image mean values for BGR: {0}".format(mean_bgr[0].mean(axis=1).mean(axis=1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create lmdb for caffe'
    )
    parser.add_argument(
        '--dict',
        type=str,
        help='Images file',
        required=True
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        help='Images lmdb',
        required=True
    )
    parser.add_argument(
        '-n',
        type=int,
        help='Number of test examples',
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

    data = load_obj(args.dict)
    pairs = []
    for l, imgs in data:
        for img in imgs:
            pairs.append((img, l))

    if args.shuffle:
        print "Shuffling the data"
        random.shuffle(pairs)

    images, labels = zip(*pairs)

    print "Creating test set"
    fillLmdb(
        images=images[:args.n],
        labels=labels[:args.n],
        min_side=args.min_side,
        max_side=args.max_side,
        output_dir=join(args.output_dir, 'test')
    )

    print "Creating training set"
    fillLmdb(
        images=images[args.n:],
        labels=labels[args.n:],
        min_side=args.min_side,
        max_side=args.max_side,
        output_dir=join(args.output_dir, 'train')
    )

    print "Completed."