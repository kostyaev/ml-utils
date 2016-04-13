import argparse
from os.path import join
import os
import eventlet
from eventlet.green import urllib2
from eventlet.timeout import Timeout
import uuid


def fetch(p):
    url, path = p[0], p[1]
    try:
        timeout = Timeout(20)
        data = urllib2.urlopen(url).read()
        if len(data) > 10000:
            with open(path, 'w') as f:
                f.write(data)
        return url
    except Exception as e:
        print e
        return url


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description='Create lmdb for caffe'
    )
    parser.add_argument(
            '--data',
            type=str,
            help='Data file containing kv pairs k - is a output dir name for images, '
                 'v - url to retrieve a list of images urls',
            required=True
    )
    parser.add_argument(
            '--out_dir',
            type=str,
            help='Output dir',
            required=True
    )

    args = parser.parse_args()
    io_pool = eventlet.GreenPool(size=50)

    result_dir = args.out_dir
    for line in open(args.data):
        a = line.rstrip('\n').split(' ')
        subdir = join(result_dir, a[0])
        if not os.path.exists(subdir):
            os.makedirs(subdir)
        try:
            data = urllib2.urlopen(a[1]).read().split('\r\n')
            print "Downloading set {}, size: {}".format(a[0], len(data))
            urls = [(url, join(subdir, '{}.jpg'.format(str(uuid.uuid4())))) for url in data]
            result = [url for url in io_pool.imap(fetch, urls)]
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            print e

    print "Completed."
