"""Recreate the train/val split used in fine-tuning.

Same procedure as AlignedShapeTextLatentModule.setup() (hy3dshape/data/dit_astl.py): every sub-folder of
the preprocessed dataset, sorted by path, shuffled with random.seed(42), first 80 % train, rest val.
The split therefore depends only on the set of folder names present when training started
(dit_v2 run: 7,473 folders -> 5,978 train / 1,495 val).

Usage: python make_splits.py $DATA_ROOT/preprocessed [--out_dir .]
"""
import argparse
import os
import random


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("train_paths", help="preprocessed dataset root (one folder per UUID)")
    ap.add_argument("--out_dir", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()

    all_data = sorted([
        os.path.join(args.train_paths, d)
        for d in os.listdir(args.train_paths)
        if os.path.isdir(os.path.join(args.train_paths, d))
    ])
    random.seed(42)
    random.shuffle(all_data)
    split_idx = int(len(all_data) * 0.8)

    for name, items in (("train_uuids.txt", all_data[:split_idx]), ("val_uuids.txt", all_data[split_idx:])):
        with open(os.path.join(args.out_dir, name), "w", encoding="utf-8") as f:
            f.writelines(os.path.basename(p) + "\n" for p in items)
    print(f"Total={len(all_data)}, Train={split_idx}, Val={len(all_data) - split_idx}")


if __name__ == "__main__":
    main()
