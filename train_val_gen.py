#!/usr/bin/env python

from os import listdir
from os.path import join
import argparse
import random

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Create train/val dictionary for binary classification')
    parser.add_argument(
        '-p', '--positive', type=str,
        help="Positive examples dir",
        required=True)
    parser.add_argument(
        '-n', '--negative', type=str,
        help="Negative examples dir",
        required=True)
    parser.add_argument(
        '-s', '--split', type=str,
        help="Split, percent of validation set",
        required=True)
    parser.add_argument(
        '-o', '--output', type=str,
        help="Output path",
        required=True)
    parser.add_argument(
        '-r', '--ralative', type=bool,
        help="Output path",
        default=False)

    args = parser.parse_args()

    pos_dir = args.positive
    neg_dir = args.negative
    split = float(args.split)
    output = args.output

    positive_examples = [{'image': join(pos_dir, f), 'label': 1} for f in listdir(pos_dir) if f.endswith(".jpg")]
    negative_examples = [{'image': join(neg_dir, f), 'label': 0} for f in listdir(neg_dir) if f.endswith(".jpg")]

    all_examples = positive_examples + negative_examples
    random.shuffle(all_examples)

    split_id = int((1 - split) * len(all_examples))
    train_split = all_examples[0:split_id]
    val_split = all_examples[split_id:len(all_examples)]

    print 'Number of all examples {0}'.format(len(all_examples))
    print 'Number of train examples {0}'.format(len(train_split))
    print 'Number of validation examples {0}'.format(len(val_split))

    with open(join(output, 'train.txt'), 'w') as txt:
        for image in train_split:
            txt.write('{0} {1}\n'.format(image['image'], image['label']))

    with open(join(output, 'val.txt'), 'w') as txt:
        for image in val_split:
            txt.write('{0} {1}\n'.format(image['image'], image['label']))
