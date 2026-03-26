from PIL import Image
import numpy as np

def smart_crop(image_path, output_path):
    img = Image.open(image_path).convert("RGB")
    np_img = np.array(img)

    # 转灰度
    gray = np.mean(np_img, axis=2)

    # 👉 找“白色区域”（内容区）
    mask = gray > 240  # 白色区域

    coords = np.argwhere(mask)

    if coords.size == 0:
        print("⚠️ 没检测到白色内容，跳过")
        img.save(output_path)
        return

    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)

    # padding
    padding = 10
    y0 = max(0, y0 - padding)
    x0 = max(0, x0 - padding)
    y1 = min(img.shape[0], y1 + padding)
    x1 = min(img.shape[1], x1 + padding)

    cropped = img.crop((x0, y0, x1, y1))
    cropped.save(output_path)

    print(f"✅ 裁剪完成: {output_path}")


def batch_crop(folder="images/flat"):
    import os

    for file in os.listdir(folder):
        if file.endswith(".png"):
            path = os.path.join(folder, file)
            smart_crop(path, path)


if __name__ == "__main__":
    batch_crop()