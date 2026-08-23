"""
Data preparation script — turns a folder of labelled images into the format
YOLO/ultralytics expects (or adapt for whatever framework you choose).

Expects a starting layout like:

    ml_pipeline/data/raw/
        images/
            img001.jpg
            img002.jpg
            ...
        labels/
            img001.txt      # YOLO-format: class x_center y_center width height (normalised 0-1)
            img002.txt

TODO (team):
  - Source/label your dataset. Options: label graffiti images yourselves with a
    tool like LabelImg or Roboflow, or start from a public dataset and
    supplement with your own labelled examples.
  - IMPORTANT: if any images/data involve identifiable people or private
    property collected directly from members of the public, check your ethics
    clearance requirements (see your project brief) before proceeding.
  - Define your class list below to match your harm classification framework.
"""

import os
import shutil
import random

RAW_DIR = "ml_pipeline/data/raw"
OUTPUT_DIR = "ml_pipeline/data/processed"

# TODO: replace with your team's actual tag/surface categories
CLASSES = ["tag", "stencil", "mural", "offensive_content"]

TRAIN_SPLIT = 0.8


def split_dataset():
    images_dir = os.path.join(RAW_DIR, "images")
    if not os.path.isdir(images_dir):
        print(f"No data found at {images_dir} yet — add labelled images/labels first.")
        return

    all_images = [f for f in os.listdir(images_dir) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
    random.shuffle(all_images)
    split_idx = int(len(all_images) * TRAIN_SPLIT)
    train_files, val_files = all_images[:split_idx], all_images[split_idx:]

    for split_name, files in [("train", train_files), ("val", val_files)]:
        img_out = os.path.join(OUTPUT_DIR, split_name, "images")
        lbl_out = os.path.join(OUTPUT_DIR, split_name, "labels")
        os.makedirs(img_out, exist_ok=True)
        os.makedirs(lbl_out, exist_ok=True)
        for fname in files:
            shutil.copy(os.path.join(images_dir, fname), os.path.join(img_out, fname))
            label_fname = os.path.splitext(fname)[0] + ".txt"
            label_src = os.path.join(RAW_DIR, "labels", label_fname)
            if os.path.exists(label_src):
                shutil.copy(label_src, os.path.join(lbl_out, label_fname))

    print(f"Split {len(all_images)} images: {len(train_files)} train / {len(val_files)} val")


def write_data_yaml():
    """YOLO/ultralytics needs a data.yaml describing paths and class names."""
    yaml_content = f"""train: {OUTPUT_DIR}/train/images
val: {OUTPUT_DIR}/val/images

nc: {len(CLASSES)}
names: {CLASSES}
"""
    with open(os.path.join(OUTPUT_DIR, "data.yaml"), "w") as f:
        f.write(yaml_content)
    print(f"Wrote {OUTPUT_DIR}/data.yaml")


if __name__ == "__main__":
    split_dataset()
    write_data_yaml()
