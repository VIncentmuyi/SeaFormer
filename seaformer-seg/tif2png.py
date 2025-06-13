#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import csv
from pathlib import Path
from PIL import Image
import subprocess
import sys


def check_dependencies():
    """检查所需的依赖库"""
    try:
        from osgeo import gdal, osr
        print("✓ GDAL已安装")
        return True
    except ImportError:
        print("❌ 未安装GDAL，请先安装：")
        print("pip install GDAL")
        print("或者使用conda：conda install -c conda-forge gdal")
        return False


def get_tif_coordinate_info(tif_path):
    """提取TIF文件的坐标信息"""
    try:
        from osgeo import gdal, osr

        # 打开TIF文件
        dataset = gdal.Open(str(tif_path))
        if dataset is None:
            return None

        # 获取地理变换参数
        geotransform = dataset.GetGeoTransform()

        # 获取投影信息
        projection = dataset.GetProjection()

        # 获取栅格尺寸
        width = dataset.RasterXSize
        height = dataset.RasterYSize

        # 计算边界坐标
        # 左上角
        x_min = geotransform[0]
        y_max = geotransform[3]

        # 右下角
        x_max = x_min + width * geotransform[1]
        y_min = y_max + height * geotransform[5]

        # 中心点
        x_center = (x_min + x_max) / 2
        y_center = (y_min + y_max) / 2

        # 像素分辨率
        pixel_width = geotransform[1]
        pixel_height = abs(geotransform[5])

        # 创建坐标系对象
        spatial_ref = osr.SpatialReference()
        spatial_ref.ImportFromWkt(projection)

        # 获取坐标系名称
        coord_system = spatial_ref.GetAttrValue('AUTHORITY', 1) if spatial_ref.GetAttrValue('AUTHORITY',
                                                                                            1) else "Unknown"

        coordinate_info = {
            "filename": tif_path.name,
            "width": width,
            "height": height,
            "bounds": {
                "x_min": x_min,
                "y_min": y_min,
                "x_max": x_max,
                "y_max": y_max
            },
            "center": {
                "x": x_center,
                "y": y_center
            },
            "pixel_resolution": {
                "width": pixel_width,
                "height": pixel_height
            },
            "coordinate_system": coord_system,
            "projection": projection,
            "geotransform": geotransform
        }

        dataset = None  # 关闭数据集
        return coordinate_info

    except Exception as e:
        print(f"处理文件 {tif_path} 时出错: {str(e)}")
        return None


def tif_to_png_with_gdal(tif_path, png_path):
    """使用GDAL将TIF转换为PNG"""
    try:
        cmd = [
            'gdal_translate',
            '-of', 'PNG',
            '-scale',  # 自动缩放到0-255
            str(tif_path),
            str(png_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            print(f"GDAL转换失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"GDAL转换出错: {str(e)}")
        return False


def tif_to_png_with_pil(tif_path, png_path):
    """使用PIL将TIF转换为PNG（备选方案）"""
    try:
        with Image.open(tif_path) as img:
            # 转换为RGB模式（如果需要）
            if img.mode not in ('RGB', 'RGBA', 'L'):
                if img.mode == 'CMYK':
                    img = img.convert('RGB')
                elif 'transparency' in img.info:
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')

            img.save(png_path, 'PNG')
        return True
    except Exception as e:
        print(f"PIL转换失败: {str(e)}")
        return False


def process_tif_files(chenzhou_dir, output_base_dir):
    """批量处理TIF文件"""
    chenzhou_path = Path(chenzhou_dir)

    if not chenzhou_path.exists():
        print(f"❌ 目录不存在: {chenzhou_dir}")
        return

    # 创建输出目录
    output_base = Path(output_base_dir)
    png_output_dir = output_base / "data"
    coord_output_dir = output_base / "coordinates"

    png_output_dir.mkdir(parents=True, exist_ok=True)
    coord_output_dir.mkdir(parents=True, exist_ok=True)

    # 存储所有坐标信息
    all_coordinates = []

    # 统计信息
    total_files = 0
    processed_files = 0
    failed_files = []

    print(f"🔍 扫描目录: {chenzhou_path}")

    # 遍历chenzhou目录下的所有子文件夹
    for subfolder in chenzhou_path.iterdir():
        if subfolder.is_dir():
            print(f"\n📁 处理文件夹: {subfolder.name}")

            # 查找该文件夹下的所有TIF文件
            tif_files = list(subfolder.glob("*.tif")) + list(subfolder.glob("*.TIF"))

            if not tif_files:
                print(f"   ⚠️ 未找到TIF文件")
                continue

            print(f"   📊 找到 {len(tif_files)} 个TIF文件")

            for tif_file in tif_files:
                total_files += 1
                print(f"   🔄 处理: {tif_file.name}")

                # 生成输出文件名（保持原文件名，只改扩展名）
                base_name = tif_file.stem
                png_file = png_output_dir / f"{base_name}.png"

                # 转换TIF为PNG
                success = False

                # 首先尝试使用GDAL
                if tif_to_png_with_gdal(tif_file, png_file):
                    success = True
                    print(f"      ✓ PNG转换成功 (GDAL)")
                # 如果GDAL失败，尝试PIL
                elif tif_to_png_with_pil(tif_file, png_file):
                    success = True
                    print(f"      ✓ PNG转换成功 (PIL)")
                else:
                    print(f"      ❌ PNG转换失败")
                    failed_files.append(str(tif_file))

                # 提取坐标信息
                coord_info = get_tif_coordinate_info(tif_file)
                if coord_info:
                    coord_info["source_folder"] = subfolder.name
                    coord_info["source_path"] = str(tif_file)
                    coord_info["png_path"] = str(png_file) if success else None
                    all_coordinates.append(coord_info)
                    print(f"      ✓ 坐标信息提取成功")
                else:
                    print(f"      ❌ 坐标信息提取失败")

                if success and coord_info:
                    processed_files += 1

    # 保存坐标信息为JSON文件
    json_file = coord_output_dir / "coordinates.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_coordinates, f, ensure_ascii=False, indent=2, default=str)

    # 保存坐标信息为CSV文件
    csv_file = coord_output_dir / "coordinates.csv"
    if all_coordinates:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # 写入表头
            headers = [
                'filename', 'source_folder', 'width', 'height',
                'x_min', 'y_min', 'x_max', 'y_max',
                'center_x', 'center_y', 'pixel_width', 'pixel_height',
                'coordinate_system', 'source_path', 'png_path'
            ]
            writer.writerow(headers)

            # 写入数据
            for coord in all_coordinates:
                row = [
                    coord['filename'],
                    coord['source_folder'],
                    coord['width'],
                    coord['height'],
                    coord['bounds']['x_min'],
                    coord['bounds']['y_min'],
                    coord['bounds']['x_max'],
                    coord['bounds']['y_max'],
                    coord['center']['x'],
                    coord['center']['y'],
                    coord['pixel_resolution']['width'],
                    coord['pixel_resolution']['height'],
                    coord['coordinate_system'],
                    coord['source_path'],
                    coord['png_path']
                ]
                writer.writerow(row)

    # 输出处理结果
    print(f"\n{'=' * 50}")
    print(f"📊 处理完成统计:")
    print(f"   总文件数: {total_files}")
    print(f"   成功处理: {processed_files}")
    print(f"   失败文件: {len(failed_files)}")
    print(f"\n📁 输出目录:")
    print(f"   PNG文件: {png_output_dir}")
    print(f"   坐标文件: {coord_output_dir}")
    print(f"      - coordinates.json: 详细坐标信息")
    print(f"      - coordinates.csv: 表格格式坐标信息")

    if failed_files:
        print(f"\n❌ 失败的文件:")
        for file in failed_files:
            print(f"   - {file}")


def main():
    print("🚀 TIF文件批量处理工具")
    print("=" * 50)

    # 检查依赖
    if not check_dependencies():
        print("\n⚠️ 建议安装GDAL以获得更好的处理效果")
        print("如果只安装了PIL，某些地理坐标信息可能无法提取")

        response = input("\n是否继续？(y/n): ")
        if response.lower() != 'y':
            return

    # 设置输入和输出路径
    chenzhou_dir = input("\n请输入chenzhou目录的完整路径: ").strip()
    if not chenzhou_dir:
        chenzhou_dir = "/home/yys/Seaformer/data/renju/chenzhou"  # 默认路径

    output_dir = input("请输入输出目录路径 (回车使用当前目录): ").strip()
    if not output_dir:
        output_dir = "."

    print(f"\n📂 输入目录: {chenzhou_dir}")
    print(f"📁 输出目录: {output_dir}")

    # 开始处理
    process_tif_files(chenzhou_dir, output_dir)


if __name__ == "__main__":
    main()