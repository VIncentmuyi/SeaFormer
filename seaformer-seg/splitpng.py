#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像切分推理拼接系统
1. 将大图切分为512x512小块
2. 记录切分信息
3. 推理后拼接回原图尺寸
"""

import os
import json
import math
from pathlib import Path
from PIL import Image
import numpy as np
from typing import List, Tuple, Dict


class ImageTiler:
    def __init__(self, tile_size=512, overlap=0):
        """
        初始化图像切分器

        Args:
            tile_size: 切分块大小 (默认512x512)
            overlap: 重叠像素数 (默认0，可设置如64来减少边界效应)
        """
        self.tile_size = tile_size
        self.overlap = overlap
        self.stride = tile_size - overlap

    def split_image(self, image_path: Path, output_dir: Path, image_id: str) -> Dict:
        """
        将单个图像切分为小块

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

                # 计算需要的瓦片数量
                tiles_x = math.ceil((original_width - self.overlap) / self.stride)
                tiles_y = math.ceil((original_height - self.overlap) / self.stride)

                print(f"将切分为: {tiles_x} x {tiles_y} = {tiles_x * tiles_y} 个瓦片")

                # 存储瓦片信息
                tiles_info = []

                for row in range(tiles_y):
                    for col in range(tiles_x):
                        # 计算瓦片在原图中的位置
                        x_start = col * self.stride
                        y_start = row * self.stride
                        x_end = min(x_start + self.tile_size, original_width)
                        y_end = min(y_start + self.tile_size, original_height)

                        # 提取瓦片
                        tile = img.crop((x_start, y_start, x_end, y_end))

                        # 如果瓦片小于目标尺寸，进行填充
                        tile_width, tile_height = tile.size
                        if tile_width < self.tile_size or tile_height < self.tile_size:
                            # 创建目标尺寸的黑色图像
                            padded_tile = Image.new('RGB', (self.tile_size, self.tile_size), (0, 0, 0))
                            # 将原瓦片粘贴到左上角
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
                            "original_width": tile_width,
                            "original_height": tile_height,
                            "padded": tile_width < self.tile_size or tile_height < self.tile_size
                        }
                        tiles_info.append(tile_info)

                # 创建图像信息字典
                image_info = {
                    "image_id": image_id,
                    "original_filename": image_path.name,
                    "original_width": original_width,
                    "original_height": original_height,
                    "tile_size": self.tile_size,
                    "overlap": self.overlap,
                    "stride": self.stride,
                    "tiles_x": tiles_x,
                    "tiles_y": tiles_y,
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

        Args:
            input_dir: 输入图像目录
            output_dir: 输出根目录
            tiles_dir: 瓦片存储子目录名
            info_file: 切分信息文件名
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


class ImageMerger:
    def __init__(self):
        pass

    def merge_single_image(self, image_info: Dict, inference_dir: Path, output_path: Path):
        """
        拼接单个图像的推理结果

        Args:
            image_info: 图像切分信息
            inference_dir: 推理结果目录
            output_path: 输出文件路径
        """
        try:
            # 创建输出图像
            output_img = Image.new('RGB',
                                   (image_info["original_width"], image_info["original_height"]),
                                   (0, 0, 0))

            print(f"拼接图像: {image_info['original_filename']}")
            print(f"目标尺寸: {image_info['original_width']} x {image_info['original_height']}")

            missing_tiles = []

            for tile_info in image_info["tiles"]:
                # 查找对应的推理结果
                tile_filename = tile_info["filename"]
                # 推理结果可能有不同的文件名格式，尝试多种可能
                possible_names = [
                    tile_filename,
                    tile_filename.replace('.png', '_pred.png'),
                    tile_filename.replace('.png', '.png'),
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
                    # 如果瓦片被填充过，需要裁剪到原始尺寸
                    if tile_info["padded"]:
                        result_tile = result_tile.crop((0, 0,
                                                        tile_info["original_width"],
                                                        tile_info["original_height"]))

                    # 粘贴到输出图像
                    output_img.paste(result_tile, (tile_info["x_start"], tile_info["y_start"]))

            # 保存拼接结果
            output_img.save(output_path)

            if missing_tiles:
                print(f"⚠️ 缺少 {len(missing_tiles)} 个瓦片的推理结果")
                for tile in missing_tiles[:5]:  # 只显示前5个
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
        """
        批量拼接所有图像的推理结果

        Args:
            tiling_info_file: 切分信息文件路径
            inference_dir: 推理结果目录
            output_dir: 输出目录
        """
        # 读取切分信息
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

            # 生成输出文件名
            original_name = Path(image_info["original_filename"]).stem
            output_filename = f"{original_name}_merged.png"
            output_file_path = output_path / output_filename

            if self.merge_single_image(image_info, inference_path, output_file_path):
                success_count += 1

        print(f"\n📊 拼接完成统计:")
        print(f"   总图像数: {len(all_images_info)}")
        print(f"   成功拼接: {success_count}")
        print(f"   输出目录: {output_dir}")


def main():
    print("🚀 图像切分推理拼接系统")
    print("=" * 50)

    print("选择操作:")
    print("1. 切分图像 (推理前)")
    print("2. 拼接结果 (推理后)")
    print("3. 完整流程演示")

    choice = input("\n请选择操作 (1/2/3): ").strip()

    if choice == "1":
        # 切分图像
        print("\n📸 图像切分模式")

        input_dir = input("请输入原图目录路径: ").strip()
        if not input_dir:
            input_dir = "/home/yys/SeaFormer/data/renju/chenzhou/test"

        output_dir = input("请输入输出目录路径: ").strip()
        if not output_dir:
            output_dir = "/home/yys/SeaFormer/data/renju/chenzhou/processing"

        tile_size = input("请输入瓦片尺寸 (默认512): ").strip()
        tile_size = int(tile_size) if tile_size else 512

        overlap = input("请输入重叠像素数 (默认0): ").strip()
        overlap = int(overlap) if overlap else 0

        print(f"\n📂 输入目录: {input_dir}")
        print(f"📁 输出目录: {output_dir}")
        print(f"📐 瓦片尺寸: {tile_size}x{tile_size}")
        print(f"🔗 重叠像素: {overlap}")

        confirm = input("\n开始切分？(y/n): ").strip().lower()
        if confirm == 'y':
            tiler = ImageTiler(tile_size=tile_size, overlap=overlap)
            tiler.split_all_images(input_dir, output_dir)

    elif choice == "2":
        # 拼接结果
        print("\n🧩 结果拼接模式")

        info_file = input("请输入切分信息文件路径: ").strip()
        if not info_file:
            info_file = "/home/yys/SeaFormer/data/renju/chenzhou/processing/tiling_info.json"

        inference_dir = input("请输入推理结果目录路径: ").strip()
        if not inference_dir:
            inference_dir = "/home/yys/SeaFormer/data/renju/chenzhou/out"

        output_dir = input("请输入拼接输出目录路径: ").strip()
        if not output_dir:
            output_dir = "/home/yys/SeaFormer/data/renju/chenzhou/merged"

        print(f"\n📄 切分信息: {info_file}")
        print(f"📂 推理结果: {inference_dir}")
        print(f"📁 输出目录: {output_dir}")

        confirm = input("\n开始拼接？(y/n): ").strip().lower()
        if confirm == 'y':
            merger = ImageMerger()
            merger.merge_all_images(info_file, inference_dir, output_dir)

    elif choice == "3":
        # 完整流程演示
        print("\n🔄 完整流程演示")
        print("步骤1: 切分图像")
        print("步骤2: 运行推理命令")
        print("步骤3: 拼接结果")

        # 设置默认路径
        test_dir = "/home/yys/SeaFormer/data/renju/chenzhou/test/data"
        processing_dir = "/home/yys/SeaFormer/data/renju/chenzhou/processing"
        out_dir = "/home/yys/SeaFormer/data/renju/chenzhou/out"
        merged_dir = "/home/yys/SeaFormer/data/renju/chenzhou/merged"

        print(f"\n默认路径配置:")
        print(f"原图目录: {test_dir}")
        print(f"处理目录: {processing_dir}")
        print(f"推理输出: {out_dir}")
        print(f"拼接输出: {merged_dir}")

        print(f"\n推理命令 (步骤2需要手动执行):")
        print(f"CUDA_VISIBLE_DEVICES=1 python ./tools/test.py \\")
        print(f"    local_configs/seaformer/seaformer_large_512x512_160k_4x8_renju.py \\")
        print(f"    /home/yys/SeaFormer/save/best_mIoU_iter_48000.pth \\")
        print(f"    --show-dir {out_dir} \\")
        print(f"    --opacity 1")

        confirm = input(f"\n使用默认配置开始处理？(y/n): ").strip().lower()
        if confirm == 'y':
            # 步骤1: 切分
            print(f"\n🔄 步骤1: 切分图像...")
            tiler = ImageTiler(tile_size=512, overlap=0)
            tiler.split_all_images(test_dir, processing_dir)

            print(f"\n✅ 步骤1完成！")
            print(f"\n🔄 请手动执行步骤2 (推理):")
            print(f"cd /home/yys/SeaFormer")
            print(f"CUDA_VISIBLE_DEVICES=1 python ./tools/test.py \\")
            print(f"    local_configs/seaformer/seaformer_large_512x512_160k_4x8_renju.py \\")
            print(f"    /home/yys/SeaFormer/save/best_mIoU_iter_48000.pth \\")
            print(f"    --show-dir {out_dir} \\")
            print(f"    --opacity 1")

            input(f"\n推理完成后按回车继续拼接...")

            # 步骤3: 拼接
            print(f"\n🔄 步骤3: 拼接结果...")
            merger = ImageMerger()
            info_file = f"{processing_dir}/tiling_info.json"
            merger.merge_all_images(info_file, out_dir, merged_dir)

            print(f"\n🎉 完整流程完成!")

    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    main()