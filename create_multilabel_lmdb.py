from PIL import Image
import numpy as np
import lmdb
import caffe
import sys
import math
import argparse
import random

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

def fillLmdb(images_file, labels_file, images, labels, maxPx, minPx):
    means = np.zeros(3)
    cnt = 0
    images_db = lmdb.open(images_file, map_size=int(1e12), map_async=True, writemap=True)
    labels_db = lmdb.open(labels_file, map_size=int(1e12))

    images_txn = images_db.begin(write=True)
    labels_txn = labels_db.begin(write=True)

    examples = zip(images, labels)
    for in_idx, (image, label) in enumerate(examples):
        try:
            #save image
            im = Image.open(image)
            im = resize(im, maxPx=maxPx, minPx=minPx)
            im = np.array(im) # or load whatever ndarray you need
            mean = im.mean(axis=0).mean(axis=0)
            means += mean
            im = im[:,:,::-1]
            im = im.transpose((2,0,1))
            im_dat = caffe.io.array_to_datum(im)
            images_txn.put('{:0>10d}'.format(in_idx), im_dat.SerializeToString())

            #save label
            label = np.array(label).astype(float).reshape(1,1,len(label))
            label_dat = caffe.io.array_to_datum(label)
            labels_txn.put('{:0>10d}'.format(in_idx), label_dat.SerializeToString())
            cnt += 1
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            print e
            print "Skipped image and label with id {0}".format(in_idx)
        if in_idx%500 == 0:
            string_ = str(in_idx+1) + ' / ' + str(len(images))
            sys.stdout.write("\r%s" % string_)
            sys.stdout.flush()

    images_txn.commit()
    labels_txn.commit()
    images_db.close()
    labels_db.close()

    print "\nFilling lmdb completed"
    print "Image mean values for RBG: {0}".format(means / cnt)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create lmdb for caffe'
    )
    parser.add_argument(
        '--images',
        type=str,
        help='Images file',
        required=True
    )
    parser.add_argument(
        '--labels',
        type=str,
        help='Labels npy file',
        required=True
    )
    parser.add_argument(
        '--imagesOut',
        type=str,
        help='Images lmdb',
        required=True
    )
    parser.add_argument(
        '--labelsOut',
        type=str,
        help='Labels lmdb',
        required=True
    )
    parser.add_argument(
        '-n',
        type=int,
        help='Number of test examples',
        required=True
    )
    parser.add_argument(
        '--maxPx',
        type=int,
        help='Max size of larger dimension after resize',
        required=True
    )
    parser.add_argument(
        '--minPx',
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

    images = np.loadtxt(args.images, str, delimiter='\t')
    labels = np.load(args.labels)

    if args.shuffle:
        print "Shuffling the data"
        data = zip(images, labels)
        random.shuffle(data)
        images, labels = zip(*data)

    print "Creating test set"
    fillLmdb(
        images_file=args.imagesOut + "_test",
        labels_file=args.labelsOut + "_test",
        images=images[:args.n],
        labels=labels[:args.n],
        minPx=args.minPx,
        maxPx=args.maxPx)

    print "Creating training set"
    fillLmdb(
        images_file=args.imagesOut,
        labels_file=args.labelsOut,
        images=images[args.n:],
        labels=labels[args.n:],
        minPx=args.minPx,
        maxPx=args.maxPx)

    print "Completed."