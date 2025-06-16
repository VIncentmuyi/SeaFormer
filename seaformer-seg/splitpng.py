#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的图像切分推理拼接系统 - 避免黑边问题
使用重叠切分策略，确保每个瓦片都是完整的512x512
"""

import os
import json
import math
from pathlib import Path
from PIL import Image
import numpy as np
from typing import List, Tuple, Dict


class ImprovedImageTiler:
    def __init__(self, tile_size=512, min_overlap=64):
        """
        改进的图像切分器 - 避免黑边问题

        Args:
            tile_size: 切分块大小 (默认512x512)
            min_overlap: 最小重叠像素数 (默认64)
        """
        self.tile_size = tile_size
        self.min_overlap = min_overlap

    def calculate_optimal_tiling(self, width: int, height: int) -> Tuple[int, int, int, int]:
        """
        计算最优的切分策略，确保每个瓦片都是完整的tile_size x tile_size

        Args:
            width: 图像宽度
            height: 图像高度

        Returns:
            (tiles_x, tiles_y, stride_x, stride_y)
        """
        # 如果图像小于等于tile_size，直接返回1个瓦片
        if width <= self.tile_size and height <= self.tile_size:
            return 1, 1, self.tile_size, self.tile_size

        # 计算X方向的切分
        if width <= self.tile_size:
            tiles_x = 1
            stride_x = self.tile_size
        else:
            # 计算需要的瓦片数量
            tiles_x = math.ceil((width - self.tile_size) / (self.tile_size - self.min_overlap)) + 1
            # 计算实际步长
            if tiles_x == 1:
                stride_x = self.tile_size
            else:
                stride_x = (width - self.tile_size) / (tiles_x - 1)

        # 计算Y方向的切分
        if height <= self.tile_size:
            tiles_y = 1
            stride_y = self.tile_size
        else:
            tiles_y = math.ceil((height - self.tile_size) / (self.tile_size - self.min_overlap)) + 1
            if tiles_y == 1:
                stride_y = self.tile_size
            else:
                stride_y = (height - self.tile_size) / (tiles_y - 1)

        return tiles_x, tiles_y, stride_x, stride_y

    def split_image(self, image_path: Path, output_dir: Path, image_id: str) -> Dict:
        """
        将单个图像切分为小块 - 改进版本，避免黑边

        Args:
            image_path: 输入图像路径
            output_dir: 输出目录
            image_id: 图像标识符

        Returns:
            包含切分信息的字典
        """
        try:
            # 读取原图
            with Image.open(image_path) as img:
                original_width, original_height = img.size

                print(f"处理图像: {image_path.name}")
                print(f"原始尺寸: {original_width} x {original_height}")

                # 计算最优切分策略
                tiles_x, tiles_y, stride_x, stride_y = self.calculate_optimal_tiling(
                    original_width, original_height)

                print(f"切分策略: {tiles_x} x {tiles_y} = {tiles_x * tiles_y} 个瓦片")
                print(f"步长: X={stride_x:.1f}, Y={stride_y:.1f}")

                # 存储瓦片信息
                tiles_info = []

                for row in range(tiles_y):
                    for col in range(tiles_x):
                        # 计算瓦片在原图中的位置
                        x_start = int(col * stride_x)
                        y_start = int(row * stride_y)

                        # 确保不超出图像边界，并且瓦片大小为tile_size
                        x_end = min(x_start + self.tile_size, original_width)
                        y_end = min(y_start + self.tile_size, original_height)

                        # 如果是边缘瓦片，调整起始位置以确保瓦片大小
                        if x_end - x_start < self.tile_size:
                            x_start = max(0, x_end - self.tile_size)
                        if y_end - y_start < self.tile_size:
                            y_start = max(0, y_end - self.tile_size)

                        # 提取瓦片
                        tile = img.crop((x_start, y_start, x_end, y_end))

                        # 记录实际提取的尺寸
                        actual_width = x_end - x_start
                        actual_height = y_end - y_start

                        # 如果瓦片仍然小于目标尺寸（只有在图像本身小于tile_size时才会发生）
                        needs_padding = actual_width < self.tile_size or actual_height < self.tile_size

                        if needs_padding:
                            # 创建目标尺寸的图像，使用边缘像素填充而不是黑色
                            padded_tile = Image.new('RGB', (self.tile_size, self.tile_size))

                            # 如果图像太小，使用反射填充
                            if actual_width > 0 and actual_height > 0:
                                # 使用镜像填充
                                tile_array = np.array(tile)
                                padded_array = np.pad(tile_array,
                                                      ((0, self.tile_size - actual_height),
                                                       (0, self.tile_size - actual_width),
                                                       (0, 0)),
                                                      mode='edge')
                                padded_tile = Image.fromarray(padded_array)
                            else:
                                padded_tile.paste(tile, (0, 0))

                            tile = padded_tile

                        # 保存瓦片
                        tile_filename = f"{image_id}_tile_{row:03d}_{col:03d}.png"
                        tile_path = output_dir / tile_filename
                        tile.save(tile_path)

                        # 记录瓦片信息
                        tile_info = {
                            "filename": tile_filename,
                            "row": row,
                            "col": col,
                            "x_start": x_start,
                            "y_start": y_start,
                            "x_end": x_end,
                            "y_end": y_end,
                            "actual_width": actual_width,
                            "actual_height": actual_height,
                            "needs_padding": needs_padding
                        }
                        tiles_info.append(tile_info)

                # 创建图像信息字典
                image_info = {
                    "image_id": image_id,
                    "original_filename": image_path.name,
                    "original_width": original_width,
                    "original_height": original_height,
                    "tile_size": self.tile_size,
                    "min_overlap": self.min_overlap,
                    "tiles_x": tiles_x,
                    "tiles_y": tiles_y,
                    "stride_x": stride_x,
                    "stride_y": stride_y,
                    "total_tiles": len(tiles_info),
                    "tiles": tiles_info
                }

                return image_info

        except Exception as e:
            print(f"处理图像 {image_path} 时出错: {str(e)}")
            return None

    def split_all_images(self, input_dir: str, output_dir: str, tiles_dir: str = "tiles",
                         info_file: str = "tiling_info.json"):
        """
        批量切分所有图像
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        tiles_path = output_path / tiles_dir

        # 创建输出目录
        tiles_path.mkdir(parents=True, exist_ok=True)

        # 查找所有图像文件
        image_extensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff']
        image_files = []
        for ext in image_extensions:
            image_files.extend(input_path.glob(f"*{ext}"))
            image_files.extend(input_path.glob(f"*{ext.upper()}"))

        if not image_files:
            print(f"❌ 在目录 {input_dir} 中未找到图像文件")
            return

        print(f"🔍 找到 {len(image_files)} 个图像文件")

        all_images_info = []
        total_tiles = 0

        for i, image_file in enumerate(image_files):
            image_id = f"img_{i:04d}"
            print(f"\n📸 [{i + 1}/{len(image_files)}] 处理: {image_file.name}")

            image_info = self.split_image(image_file, tiles_path, image_id)
            if image_info:
                all_images_info.append(image_info)
                total_tiles += image_info["total_tiles"]
                print(f"✓ 完成，生成 {image_info['total_tiles']} 个瓦片")
            else:
                print(f"❌ 处理失败")

        # 保存切分信息
        info_path = output_path / info_file
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(all_images_info, f, ensure_ascii=False, indent=2)

        print(f"\n📊 切分完成统计:")
        print(f"   处理图像: {len(all_images_info)}")
        print(f"   生成瓦片: {total_tiles}")
        print(f"   瓦片目录: {tiles_path}")
        print(f"   信息文件: {info_path}")

        return all_images_info


class ImprovedImageMerger:
    def __init__(self):
        pass

    def merge_single_image(self, image_info: Dict, inference_dir: Path, output_path: Path):
        """
        改进的图像拼接 - 处理重叠区域
        """
        try:
            # 创建输出图像
            output_img = Image.new('RGB',
                                   (image_info["original_width"], image_info["original_height"]),
                                   (0, 0, 0))

            print(f"拼接图像: {image_info['original_filename']}")
            print(f"目标尺寸: {image_info['original_width']} x {image_info['original_height']}")

            # 创建权重矩阵用于处理重叠区域
            weight_matrix = np.zeros((image_info["original_height"], image_info["original_width"]), dtype=np.float32)
            accumulated_img = np.zeros((image_info["original_height"], image_info["original_width"], 3),
                                       dtype=np.float32)

            missing_tiles = []

            for tile_info in image_info["tiles"]:
                # 查找对应的推理结果
                tile_filename = tile_info["filename"]
                possible_names = [
                    tile_filename,
                    tile_filename.replace('.png', '_pred.png'),
                    Path(tile_filename).stem + '.png'
                ]

                inference_tile_path = None
                for name in possible_names:
                    potential_path = inference_dir / name
                    if potential_path.exists():
                        inference_tile_path = potential_path
                        break

                if inference_tile_path is None:
                    missing_tiles.append(tile_filename)
                    continue

                # 读取推理结果
                with Image.open(inference_tile_path) as result_tile:
                    result_array = np.array(result_tile)

                    # 获取在原图中的位置
                    x_start = tile_info["x_start"]
                    y_start = tile_info["y_start"]
                    x_end = tile_info["x_end"]
                    y_end = tile_info["y_end"]

                    # 计算实际需要使用的区域
                    actual_width = x_end - x_start
                    actual_height = y_end - y_start

                    # 裁剪推理结果到实际尺寸
                    cropped_result = result_array[:actual_height, :actual_width]

                    # 创建权重（中心权重高，边缘权重低，用于平滑拼接）
                    tile_weight = np.ones((actual_height, actual_width), dtype=np.float32)

                    # 如果有重叠，在边缘区域使用渐变权重
                    fade_width = min(32, actual_width // 4)  # 边缘渐变宽度
                    fade_height = min(32, actual_height // 4)

                    if fade_width > 0 and fade_height > 0:
                        # 创建渐变权重
                        for i in range(fade_height):
                            tile_weight[i, :] *= (i + 1) / fade_height
                            tile_weight[-(i + 1), :] *= (i + 1) / fade_height
                        for j in range(fade_width):
                            tile_weight[:, j] *= (j + 1) / fade_width
                            tile_weight[:, -(j + 1)] *= (j + 1) / fade_width

                    # 累积到结果图像
                    accumulated_img[y_start:y_end, x_start:x_end] += cropped_result * tile_weight[:, :, np.newaxis]
                    weight_matrix[y_start:y_end, x_start:x_end] += tile_weight

            # 避免除零
            weight_matrix[weight_matrix == 0] = 1

            # 计算最终结果
            final_result = accumulated_img / weight_matrix[:, :, np.newaxis]
            final_result = np.clip(final_result, 0, 255).astype(np.uint8)

            # 转换为PIL图像并保存
            output_img = Image.fromarray(final_result)
            output_img.save(output_path)

            if missing_tiles:
                print(f"⚠️ 缺少 {len(missing_tiles)} 个瓦片的推理结果")
                for tile in missing_tiles[:5]:
                    print(f"   - {tile}")
                if len(missing_tiles) > 5:
                    print(f"   ... 还有 {len(missing_tiles) - 5} 个")
            else:
                print(f"✓ 拼接完成: {output_path}")

            return True

        except Exception as e:
            print(f"拼接图像时出错: {str(e)}")
            return False

    def merge_all_images(self, tiling_info_file: str, inference_dir: str, output_dir: str):
        """批量拼接所有图像的推理结果"""
        try:
            with open(tiling_info_file, 'r', encoding='utf-8') as f:
                all_images_info = json.load(f)
        except Exception as e:
            print(f"❌ 无法读取切分信息文件: {str(e)}")
            return

        inference_path = Path(inference_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"📁 推理结果目录: {inference_dir}")
        print(f"📁 输出目录: {output_dir}")
        print(f"🔄 开始拼接 {len(all_images_info)} 个图像...")

        success_count = 0

        for i, image_info in enumerate(all_images_info):
            print(f"\n[{i + 1}/{len(all_images_info)}] ", end="")

            original_name = Path(image_info["original_filename"]).stem
            output_filename = f"{original_name}_merged.png"
            output_file_path = output_path / output_filename

            if self.merge_single_image(image_info, inference_path, output_file_path):
                success_count += 1

        print(f"\n📊 拼接完成统计:")
        print(f"   总图像数: {len(all_images_info)}")
        print(f"   成功拼接: {success_count}")
        print(f"   输出目录: {output_dir}")


# 使用示例
def demo_usage():
    """演示如何使用改进的切分器"""

    # 创建改进的切分器
    tiler = ImprovedImageTiler(tile_size=512, min_overlap=64)

    # 切分图像
    input_dir = "path/to/input/images"
    output_dir = "path/to/output"
    tiler.split_all_images(input_dir, output_dir)

    # 推理完成后，使用改进的拼接器
    merger = ImprovedImageMerger()
    info_file = f"{output_dir}/tiling_info.json"
    inference_dir = "path/to/inference/results"
    merged_dir = "path/to/merged/results"
    merger.merge_all_images(info_file, inference_dir, merged_dir)


if __name__ == "__main__":
    demo_usage()