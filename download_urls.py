import argparse
import eventlet
from eventlet.green import urllib2
from os.path import join
import os


def fetch(url, directory):
    try:
        filename = join(directory, url.split('/')[-1].rsplit('?', 1)[0])
        data = urllib2.urlopen(url).read()
        if len(data) > 5000:
            with open(filename, 'w') as f:
                f.write(data)
        return filename
    except Exception as e:
        print e
        return None


def download_urls((idx, url)):
    os.sys.stdout.write('\r{}'.format(idx))
    os.sys.stdout.flush()
    return fetch(url, args.dir)


if __name__ == '__main__':

    pool = eventlet.GreenPool(size=50)

    parser = argparse.ArgumentParser(
            description='Create labels to images map'
    )
    parser.add_argument(
            '--urls',
            type=str,
            help='Urls file',
            required=True
    )
    parser.add_argument(
            '--dir',
            type=str,
            help='Dir',
            required=True
    )

    args = parser.parse_args()

    if not os.path.exists(args.dir):
            os.makedirs(args.dir)

    links = [l.rstrip('\n') for l in open(args.urls)]

    result = [res for res in pool.imap(download_urls, enumerate(links))]