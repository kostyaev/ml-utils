from PIL import Image
import numpy as np
import lmdb
import caffe
import sys
import math
import argparse
import random
from os.path import join
import os

def resize(img, maxPx, minPx):
    try:
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
        return img
    except IOError as e:
        print "I/O error({0}): {1}".format(e.errno, e.strerror)

def centeredCrop(img, new_height, new_width):
    width = np.size(img,1)
    height = np.size(img,0)
    left = int(np.ceil((width - new_width)/2.))
    top = int(np.ceil((height - new_height)/2.))
    right = int(np.ceil((width + new_width)/2.))
    bottom = int(np.ceil((height + new_height)/2.))
    cImg = img[top:bottom, left:right]
    return cImg


def open_image(f, max_side, min_side):
    im = Image.open(f)
    im = resize(im, maxPx=max_side, minPx=min_side)
    im = np.array(im).astype(np.float32, copy=False)
    if im.ndim == 2:
        im = im[:, :, np.newaxis]
        im = np.tile(im, (1, 1, 3))
    elif im.shape[2] == 4:
        im = im[:, :, :3]
    im = centeredCrop(im, max_side, max_side)
    im = im[:,:,::-1]
    im = im.transpose(2,0,1)
    return im

def create_lmdb(data, max_side, min_side, out_dir):
    mean_bgr = np.array([0,0,0])
    mean_bgr = mean_bgr[:, np.newaxis, np.newaxis]
    cnt = 0
    lmdb_dir = join(out_dir, 'lmdb')

    if not os.path.exists(lmdb_dir):
        os.makedirs(lmdb_dir)

    db = lmdb.open(out_dir, map_size=int(1e12), map_async=True, writemap=True)
    with db.begin(write=True) as txn:
        for img_path, label in data:
            try:
                img = open_image(img_path, max_side=max_side, min_side=min_side)
                mean_bgr += img
                datum = caffe.io.array_to_datum(img)
                datum.label = label
                str_id = '{:0>10d}'.format(cnt)
                txn.put(str_id.encode('ascii'), datum.SerializeToString())
                cnt += 1
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                print e
                print "Skipped image and label with id {0}".format(cnt)
            if cnt % 500 == 0:
                string_ = str(cnt+1) + ' / ' + str(len(data))
                sys.stdout.write("\r%s" % string_)
                sys.stdout.flush()

    txn.commit()
    db.close()
    print "\nFilling lmdb completed"
    mean_bgr /= cnt
    np.save(mean_bgr, join(out_dir, 'mean.npy'))
    print "Image mean values for BGR: {0}".format(mean_bgr.mean(axis=1).mean(axis=1) / cnt)


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