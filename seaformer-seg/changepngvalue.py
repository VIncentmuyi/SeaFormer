import os
import numpy as np
from PIL import Image
import glob


def increment_label_pixels(root_dir="/home/yys/SeaFormer/data/dataset"):
    """
    遍历SeaFormer目录下所有labels文件夹中的PNG图片，
    将每个像素值加1并保存

    Args:
        root_dir (str): 根目录路径，默认为"SeaFormer"
    """

    # 查找所有labels目录
    labels_pattern = os.path.join(root_dir, "**/labels")
    labels_dirs = glob.glob(labels_pattern, recursive=True)

    if not labels_dirs:
        print("未找到任何labels目录")
        return

    total_processed = 0

    for labels_dir in labels_dirs:
        print(f"处理目录: {labels_dir}")

        # 获取该目录下所有PNG文件
        png_files = glob.glob(os.path.join(labels_dir, "*.png"))

        if not png_files:
            print(f"  目录 {labels_dir} 中没有PNG文件")
            continue

        processed_count = 0

        for png_file in png_files:
            try:
                # 读取图像
                img = Image.open(png_file)

                # 转换为numpy数组
                img_array = np.array(img)

                # 检查是否为单通道图像
                if len(img_array.shape) > 2:
                    print(f"  警告: {os.path.basename(png_file)} 不是单通道图像，跳过")
                    continue

                # 像素值加1
                img_array_new = img_array + 1

                # 确保数据类型一致
                if img_array.dtype == np.uint8:
                    # 防止溢出，将值限制在0-255范围内
                    img_array_new = np.clip(img_array_new, 0, 255).astype(np.uint8)

                # 转换回PIL图像并保存
                img_new = Image.fromarray(img_array_new)
                img_new.save(png_file)

                processed_count += 1
                print(f"  ✓ 已处理: {os.path.basename(png_file)}")

            except Exception as e:
                print(f"  ✗ 处理 {os.path.basename(png_file)} 时出错: {e}")

        print(f"  目录 {labels_dir} 共处理了 {processed_count} 个文件")
        total_processed += processed_count

    print(f"\n总共处理了 {total_processed} 个文件")


def increment_single_labels_dir(labels_dir):
    """
    处理单个labels目录中的PNG图片

    Args:
        labels_dir (str): labels目录路径
    """

    if not os.path.exists(labels_dir):
        print(f"目录 {labels_dir} 不存在")
        return

    # 获取该目录下所有PNG文件
    png_files = glob.glob(os.path.join(labels_dir, "*.png"))

    if not png_files:
        print(f"目录 {labels_dir} 中没有PNG文件")
        return

    processed_count = 0

    for png_file in png_files:
        try:
            # 读取图像
            img = Image.open(png_file)

            # 转换为numpy数组
            img_array = np.array(img)

            # 检查是否为单通道图像
            if len(img_array.shape) > 2:
                print(f"警告: {os.path.basename(png_file)} 不是单通道图像，跳过")
                continue

            # 显示原始像素值范围
            print(f"处理 {os.path.basename(png_file)}: 原始值范围 [{img_array.min()}, {img_array.max()}]", end=" -> ")

            # 像素值加1
            img_array_new = img_array + 1

            # 确保数据类型一致
            if img_array.dtype == np.uint8:
                # 防止溢出，将值限制在0-255范围内
                img_array_new = np.clip(img_array_new, 0, 255).astype(np.uint8)

            print(f"新值范围 [{img_array_new.min()}, {img_array_new.max()}]")

            # 转换回PIL图像并保存
            img_new = Image.fromarray(img_array_new)
            img_new.save(png_file)

            processed_count += 1

        except Exception as e:
            print(f"处理 {os.path.basename(png_file)} 时出错: {e}")

    print(f"\n共处理了 {processed_count} 个文件")


if __name__ == "__main__":
    # 方法1: 处理SeaFormer目录下所有labels文件夹
    print("=== 方法1: 处理所有labels目录 ===")
    increment_label_pixels()

    # 方法2: 处理特定的labels目录（取消注释以使用）
    # print("\n=== 方法2: 处理特定labels目录 ===")
    # increment_single_labels_dir("SeaFormer/data/dataset/train/labels")
    # increment_single_labels_dir("SeaFormer/data/dataset/test/labels")
    # increment_single_labels_dir("SeaFormer/data/dataset/val/labels")