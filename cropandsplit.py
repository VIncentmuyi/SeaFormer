import os
import random
import shutil
import numpy as np
from PIL import Image
from tqdm import tqdm


def create_directories(base_path):
    """创建必要的目录结构"""
    dirs = [
        os.path.join(base_path, "train", "images"),
        os.path.join(base_path, "train", "labels"),
        os.path.join(base_path, "val", "images"),
        os.path.join(base_path, "val", "labels"),
        os.path.join(base_path, "test", "images"),
        os.path.join(base_path, "test", "labels")
    ]

    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)

    return dirs


def crop_image(image_path, label_path, crop_size=512, output_base="output"):
    """裁切图像和标签为crop_size×crop_size大小的块"""

    # 创建输出目录
    dirs = create_directories(output_base)

    # 获取所有图像文件
    image_files = [f for f in os.listdir(image_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))]

    # 准备数据集划分
    random.shuffle(image_files)
    total = len(image_files)
    train_end = int(total * 0.7)
    val_end = train_end + int(total * 0.2)

    train_files = image_files[:train_end]
    val_files = image_files[train_end:val_end]
    test_files = image_files[val_end:]

    # 处理训练集
    process_dataset(train_files, image_path, label_path, dirs[0], dirs[1], crop_size, "train")

    # 处理验证集
    process_dataset(val_files, image_path, label_path, dirs[2], dirs[3], crop_size, "val")

    # 处理测试集
    process_dataset(test_files, image_path, label_path, dirs[4], dirs[5], crop_size, "test")


def process_dataset(files, image_dir, label_dir, out_img_dir, out_lbl_dir, crop_size, dataset_type):
    """处理数据集中的文件，裁切并保存"""
    print(f"Processing {dataset_type} set...")

    for img_file in tqdm(files):
        # 获取对应的标签文件名（假设图像和标签文件名相同，可能扩展名不同）
        label_file = os.path.splitext(img_file)[0] + ".png"  # 根据实际情况调整扩展名

        # 完整路径
        img_path = os.path.join(image_dir, img_file)
        lbl_path = os.path.join(label_dir, label_file)

        # 检查标签文件是否存在
        if not os.path.exists(lbl_path):
            print(f"Warning: Label file not found for {img_file}, skipping...")
            continue

        # 打开图像和标签
        try:
            image = Image.open(img_path)
            label = Image.open(lbl_path)

            # 确保图像和标签大小相同
            if image.size != label.size:
                print(f"Warning: Image and label dimensions don't match for {img_file}, skipping...")
                continue

            width, height = image.size

            # 计算需要裁剪的块数
            n_cols = (width + crop_size - 1) // crop_size
            n_rows = (height + crop_size - 1) // crop_size

            # 裁剪图像和标签
            for i in range(n_rows):
                for j in range(n_cols):
                    # 计算裁剪区域
                    left = j * crop_size
                    top = i * crop_size
                    right = min(left + crop_size, width)
                    bottom = min(top + crop_size, height)

                    # 如果裁剪区域小于完整的crop_size，则跳过
                    if right - left < crop_size or bottom - top < crop_size:
                        continue

                    # 裁剪
                    img_crop = image.crop((left, top, right, bottom))
                    lbl_crop = label.crop((left, top, right, bottom))

                    # 生成输出文件名
                    base_name = os.path.splitext(img_file)[0]
                    crop_name = f"{base_name}_r{i}_c{j}"

                    # 保存裁剪后的图像和标签
                    img_crop.save(os.path.join(out_img_dir, f"{crop_name}.png"))
                    lbl_crop.save(os.path.join(out_lbl_dir, f"{crop_name}.png"))

        except Exception as e:
            print(f"Error processing {img_file}: {e}")


if __name__ == "__main__":
    # 设置路径
    image_folder = "./data/image"  # 原始图像文件夹
    label_folder = "./data/label"  # 原始标签文件夹
    output_folder = "./data/dataset" # 输出文件夹
    crop_size = 512  # 裁剪大小

    # 执行裁剪和划分
    crop_image(image_folder, label_folder, crop_size, output_folder)

    print("Processing complete!")