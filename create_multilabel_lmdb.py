from PIL import Image
import numpy as np
import lmdb
import caffe
import sys
import math

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

def createImageLmdb(filename, images):
    means = np.zeros(3)
    in_db = lmdb.open(filename, map_size=int(1e12), map_async=True, writemap=True)
    with in_db.begin(write=True) as in_txn:
        for in_idx, in_ in enumerate(images):
            # load image:
            # - as np.uint8 {0, ..., 255}
            # - in BGR (switch from RGB)
            # - in Channel x Height x Width order (switch from H x W x C)
            im = Image.open(in_)
            im = resize(im, maxPx=256, minPx=227)
            im = np.array(im) # or load whatever ndarray you need
            mean = im.mean(axis=0).mean(axis=0)
            means += mean

            im = im[:,:,::-1]
            im = im.transpose((2,0,1))
            im_dat = caffe.io.array_to_datum(im)
            in_txn.put('{:0>10d}'.format(in_idx), im_dat.SerializeToString())
            if in_idx%1000 == 0:
                string_ = str(in_idx+1) + ' / ' + str(len(images))
                sys.stdout.write("\r%s" % string_)
                sys.stdout.flush()
    in_db.close()
    print "Total number of images: {0}, Mean values in RGB order: {1}".format(len(images), means / len(images))



def createLabelLmdb(filename, labels):
    in_db = lmdb.open(filename, map_size=int(1e12))
    with in_db.begin(write=True) as in_txn:
        for in_idx, in_ in enumerate(labels):
            # load label:
            # - as np.uint8
            # - in float and reshape
            label = np.array(in_).astype(float).reshape(len(in_),1,1)
            # - Turn to caffe object
            label_dat = caffe.io.array_to_datum(label)
            # - Write it
            in_txn.put('{:0>10d}'.format(in_idx), label_dat.SerializeToString())
            if in_idx%1000 == 0:
                string_ = str(in_idx+1) + ' / ' + str(len(labels))
                sys.stdout.write("\r%s" % string_)
                sys.stdout.flush()
    in_db.close()
    print "Total number of labels: {0}".format(len(labels))