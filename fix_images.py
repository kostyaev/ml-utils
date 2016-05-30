from os.path import join
import os
import argparse
import multiprocessing
from PIL import Image
import sys

def remove_corrupted(path):
    try:
        img = Image.open(path)
        img.load()
        if img.format != 'JPEG':
            if img.mode == 'RGBA':
                print "converting RGBA {} to JPEG".format(path)
                png = img.convert('RGBA')
                background = Image.new('RGBA', png.size, (255,255,255))
                alpha_composite = Image.alpha_composite(background, png)
                alpha_composite.save(path, 'JPEG', quality=100)
            else:
                print "converting {} {} to JPEG".format(img.mode, path)
                img.convert('RGB').save(path)
        return True
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        print "removing broken img {}".format(path)
        os.remove(path)
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description='Create labels to images map'
    )
    parser.add_argument(
            '--dir',
            type=str,
            help='Dir',
            required=True
    )

    args = parser.parse_args()
    pool = multiprocessing.Pool(processes=8)

    cnt = 0
    failed_cnt = 0
    for subdir, dirs, files in os.walk(args.dir):
        cur_dir = subdir.split('/')[-1]
        imgs = [join(subdir, f) for f in files if f.endswith('.jpg')]
        for res in pool.map(remove_corrupted, imgs):
            cnt += 1
            if not res:
                failed_cnt += 1
            if cnt % 50 == 0:
                sys.stdout.write("\r%s" % str(cnt))
                sys.stdout.flush()
    print "Kept {} images, removed: {}".format(cnt-failed_cnt, failed_cnt)
