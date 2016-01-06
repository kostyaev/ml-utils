import argparse
from os import listdir
from os.path import join
import os
import shutil

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Copy first n files to some dir'
    )
    parser.add_argument(
        '--input',
        type=str,
        help='Input dir',
        required=True
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output dir',
        required=True
    )
    parser.add_argument(
        '-n',
        type=int,
        help='Number of files to copy',
        required=True
    )

    args = parser.parse_args()

    in_dir = args.input
    out_dir = args.output
    n = args.n
    cnt = 0

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    for f in listdir(in_dir):
        if cnt < n:
            print f
            shutil.copy(join(in_dir, f), out_dir)
            cnt += 1
        else:
            break

    print "Completed."
