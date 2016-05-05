from os.path import join
import os
import argparse
import operator
import pickle

def save_obj(obj, name ):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def encode(labels, label_to_id):
    return ','.join([str(label_to_id[l]) for l in labels.split('/')])

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
    parser.add_argument(
        '--labels_out',
        type=str,
        help='Output file',
        required=True
    )
    parser.add_argument(
        '--dict',
        type=str,
        help='Output file',
        required=True
    )

    args = parser.parse_args()

    labels_files = []
    all_labels = {}

    for subdir, dirs, files in os.walk(args.dir):
        cur_dir = subdir.split('/')[-1]
        if cur_dir != '':
            all_labels[cur_dir] = len(all_labels)
        labels = subdir.replace(args.dir, '')
        imgs = [join(subdir, f) for f in files if f.endswith('.jpg')]
        if len(imgs) > 0:
            labels_files.append((labels, imgs))

    sorted_labels = sorted(all_labels.items(), key=operator.itemgetter(1))
    with open(args.labels_out, 'w') as f:
        for label, id in sorted_labels:
            f.write(label + '\n')

    encoded_labels_files = []
    for k,v in labels_files:
        encoded_labels_files.append((encode(k, all_labels), v))

    save_obj(encoded_labels_files, args.dict)

