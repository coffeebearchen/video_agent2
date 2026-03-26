import os
import json
import hashlib
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")

INDEX_PATH = os.path.join(BASE_DIR, "image_index.json")


def get_hash(path):

    h = hashlib.md5()

    with open(path, "rb") as f:

        while True:

            chunk = f.read(8192)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def scan_images():

    index = []

    for file in os.listdir(IMAGE_DIR):

        if not file.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        path = os.path.join(IMAGE_DIR, file)

        img = Image.open(path)

        width, height = img.size

        orientation = "landscape"

        if height > width:
            orientation = "portrait"

        info = {
            "file": file,
            "path": path,
            "width": width,
            "height": height,
            "orientation": orientation,
            "size": os.path.getsize(path),
            "hash": get_hash(path),
            "tags": [],
            "category": "",
            "style": ""
        }

        index.append(info)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:

        json.dump(index, f, indent=2, ensure_ascii=False)

    print("图片扫描完成")
    print("生成 image_index.json")


if __name__ == "__main__":

    scan_images()