from PIL import Image
import argparse
from os import walk, path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Resize all images in direcory'
    )
    parser.add_argument(
        '--input',
        type=str,
        help='Path to dir with images to resize',
        required=True
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Path to dir where result images will be placed',
        required=True
    )
    parser.add_argument(
        '--size',
        type=int,
        help='Max size of larger dimension after resize',
        required=True
    )

    args = parser.parse_args()

    in_dir = args.input
    out_dir = args.output

    files = []
    for (dirpath, dirnames, filenames) in walk(in_dir):
        files.extend(filenames)
        break

    for f in files:
        try:
            filename, file_extension = path.splitext(f)

            img = Image.open(in_dir + f)
            width = img.size[0]
            height = img.size[1]

            top = 0
            left = 0
            bottom = min(args.size, height)
            right = min(args.size, width)

            i = 1
            while True:
                while True:
                    cropped = img.crop((left, top, right, bottom))
                    cropped.save(out_dir + filename + str(i) + file_extension)
                    i += 1

                    if right >= width:
                        break

                    right = min(right + args.size, width)
                    left = right - args.size

                if bottom >= height:
                    break

                bottom = min(bottom + args.size, height)
                top = bottom - args.size
                left = 0
                right = args.size
        except IOError:
            print "Error cropping image"