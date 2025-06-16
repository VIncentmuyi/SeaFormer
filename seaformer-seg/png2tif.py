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


def load_coordinate_info(coord_file):
    """加载坐标信息文件"""
    coord_path = Path(coord_file)

    if not coord_path.exists():
        print(f"❌ 坐标文件不存在: {coord_file}")
        return None

    coordinate_data = {}

    if coord_path.suffix.lower() == '.json':
        # 加载JSON文件
        try:
            with open(coord_path, 'r', encoding='utf-8') as f:
                coords_list = json.load(f)

            # 将列表转换为以文件名为键的字典
            for coord in coords_list:
                filename = coord['filename']
                # 去掉扩展名，因为PNG文件名可能与原TIF文件名相同（除了扩展名）
                base_name = Path(filename).stem
                coordinate_data[base_name] = coord

        except Exception as e:
            print(f"❌ 读取JSON文件失败: {str(e)}")
            return None

    elif coord_path.suffix.lower() == '.csv':
        # 加载CSV文件
        try:
            with open(coord_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    filename = row['filename']
                    base_name = Path(filename).stem

                    # 重构坐标信息格式
                    coord_info = {
                        'filename': filename,
                        'source_folder': row['source_folder'],
                        'width': int(row['width']),
                        'height': int(row['height']),
                        'bounds': {
                            'x_min': float(row['x_min']),
                            'y_min': float(row['y_min']),
                            'x_max': float(row['x_max']),
                            'y_max': float(row['y_max'])
                        },
                        'center': {
                            'x': float(row['center_x']),
                            'y': float(row['center_y'])
                        },
                        'pixel_resolution': {
                            'width': float(row['pixel_width']),
                            'height': float(row['pixel_height'])
                        },
                        'coordinate_system': row['coordinate_system'],
                        'source_path': row['source_path'],
                        'png_path': row['png_path']
                    }

                    # 如果有projection和geotransform信息，尝试解析
                    if 'projection' in row:
                        coord_info['projection'] = row['projection']
                    if 'geotransform' in row:
                        coord_info['geotransform'] = eval(row['geotransform']) if row['geotransform'] else None

                    coordinate_data[base_name] = coord_info

        except Exception as e:
            print(f"❌ 读取CSV文件失败: {str(e)}")
            return None
    else:
        print(f"❌ 不支持的坐标文件格式: {coord_path.suffix}")
        return None

    print(f"✓ 成功加载 {len(coordinate_data)} 个文件的坐标信息")
    return coordinate_data


def png_to_tif_with_coordinates(png_path, tif_path, coord_info):
    """将PNG转换为带地理坐标的TIF文件"""
    try:
        from osgeo import gdal, osr

        # 首先检查PNG文件是否存在
        if not png_path.exists():
            print(f"❌ PNG文件不存在: {png_path}")
            return False

        # 使用PIL读取PNG文件
        with Image.open(png_path) as img:
            # 获取图像数据
            img_array = list(img.getdata())
            width, height = img.size

            # 确保尺寸匹配
            if width != coord_info['width'] or height != coord_info['height']:
                print(f"⚠️ 尺寸不匹配: PNG({width}x{height}) vs 原始({coord_info['width']}x{coord_info['height']})")
                # 可以选择调整大小或继续使用PNG的尺寸
                width, height = img.size

        # 创建GDAL驱动
        driver = gdal.GetDriverByName('GTiff')

        # 确定数据类型和波段数
        with Image.open(png_path) as img:
            if img.mode == 'L':  # 灰度图像
                bands = 1
                data_type = gdal.GDT_Byte
            elif img.mode == 'RGB':  # RGB图像
                bands = 3
                data_type = gdal.GDT_Byte
            elif img.mode == 'RGBA':  # RGBA图像
                bands = 4
                data_type = gdal.GDT_Byte
            else:
                # 转换为RGB
                img = img.convert('RGB')
                bands = 3
                data_type = gdal.GDT_Byte

        # 创建输出TIF文件
        dataset = driver.Create(str(tif_path), width, height, bands, data_type)

        if dataset is None:
            print(f"❌ 无法创建TIF文件: {tif_path}")
            return False

        # 设置地理变换参数
        if 'geotransform' in coord_info and coord_info['geotransform']:
            # 使用原始的geotransform
            geotransform = coord_info['geotransform']
        else:
            # 根据边界信息计算geotransform
            x_min = coord_info['bounds']['x_min']
            y_max = coord_info['bounds']['y_max']
            pixel_width = coord_info['pixel_resolution']['width']
            pixel_height = -coord_info['pixel_resolution']['height']  # 注意负号

            geotransform = (x_min, pixel_width, 0, y_max, 0, pixel_height)

        dataset.SetGeoTransform(geotransform)

        # 设置投影信息
        if 'projection' in coord_info and coord_info['projection']:
            dataset.SetProjection(coord_info['projection'])
        else:
            # 如果没有投影信息，尝试使用坐标系信息
            srs = osr.SpatialReference()
            if coord_info['coordinate_system'] != 'Unknown':
                srs.ImportFromEPSG(int(coord_info['coordinate_system']))
                dataset.SetProjection(srs.ExportToWkt())

        # 写入图像数据
        with Image.open(png_path) as img:
            if img.mode == 'L':
                # 灰度图像
                band = dataset.GetRasterBand(1)
                img_array = list(img.getdata())
                # 重新排列数据为2D数组
                import numpy as np
                img_2d = np.array(img_array).reshape((height, width))
                band.WriteArray(img_2d)
            elif img.mode in ['RGB', 'RGBA']:
                # 彩色图像
                img_array = list(img.getdata())
                import numpy as np

                if img.mode == 'RGB':
                    # RGB图像
                    img_array = np.array(img_array).reshape((height, width, 3))
                    for i in range(3):
                        band = dataset.GetRasterBand(i + 1)
                        band.WriteArray(img_array[:, :, i])
                else:
                    # RGBA图像
                    img_array = np.array(img_array).reshape((height, width, 4))
                    for i in range(4):
                        band = dataset.GetRasterBand(i + 1)
                        band.WriteArray(img_array[:, :, i])

        # 刷新缓存并关闭数据集
        dataset.FlushCache()
        dataset = None

        print(f"      ✓ TIF文件创建成功")
        return True

    except Exception as e:
        print(f"      ❌ 转换失败: {str(e)}")
        return False


def process_png_to_tif(png_dir, coord_file, output_dir):
    """批量将PNG转换为带坐标的TIF文件"""
    png_path = Path(png_dir)
    output_path = Path(output_dir)

    if not png_path.exists():
        print(f"❌ PNG目录不存在: {png_dir}")
        return

    # 加载坐标信息
    coordinate_data = load_coordinate_info(coord_file)
    if not coordinate_data:
        return

    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)

    # 统计信息
    total_files = 0
    processed_files = 0
    failed_files = []
    missing_coord_files = []

    print(f"🔍 扫描PNG目录: {png_path}")
    print(f"📋 坐标信息中的文件名示例: {list(coordinate_data.keys())[:3] if coordinate_data else []}")

    # 查找所有PNG文件
    png_files = list(png_path.glob("*.png")) + list(png_path.glob("*.PNG"))

    if not png_files:
        print("❌ 未找到PNG文件")
        return

    print(f"📊 找到 {len(png_files)} 个PNG文件")
    print(f"📋 PNG文件名示例: {[f.name for f in png_files[:3]]}")
    print(f"💡 将尝试通过移除'_merged'后缀来匹配坐标信息")
    print()

    for png_file in png_files:
        total_files += 1
        base_name = png_file.stem

        print(f"🔄 处理: {png_file.name}")

        # 处理文件名映射：移除_merged后缀来匹配原始坐标信息
        original_name = base_name
        if base_name.endswith('_merged'):
            original_name = base_name[:-7]  # 移除'_merged'后缀

        # 查找对应的坐标信息
        if original_name not in coordinate_data:
            print(f"   ⚠️ 未找到坐标信息 (尝试匹配: {original_name})")
            missing_coord_files.append(str(png_file))
            continue

        coord_info = coordinate_data[original_name]

        # 生成输出TIF文件路径（保留merged后缀或使用原始名称）
        output_name = base_name  # 保持PNG的完整文件名（包含_merged）
        # 如果您希望输出文件名不包含_merged，可以使用下面这行
        # output_name = original_name

        tif_file = output_path / f"{output_name}.tif"

        # 转换PNG为TIF
        if png_to_tif_with_coordinates(png_file, tif_file, coord_info):
            processed_files += 1
            print(f"   ✓ 转换成功: {tif_file.name}")
        else:
            failed_files.append(str(png_file))

    # 输出处理结果
    print(f"\n{'=' * 50}")
    print(f"📊 处理完成统计:")
    print(f"   总PNG文件数: {total_files}")
    print(f"   成功转换: {processed_files}")
    print(f"   转换失败: {len(failed_files)}")
    print(f"   缺少坐标信息: {len(missing_coord_files)}")
    print(f"\n📁 输出目录: {output_path}")

    if failed_files:
        print(f"\n❌ 转换失败的文件:")
        for file in failed_files:
            print(f"   - {file}")

    if missing_coord_files:
        print(f"\n⚠️ 缺少坐标信息的文件:")
        for file in missing_coord_files:
            print(f"   - {file}")


def main():
    print("🔄 PNG转TIF并恢复地理坐标工具")
    print("=" * 50)

    # 检查依赖
    if not check_dependencies():
        print("❌ 需要安装GDAL才能使用此工具")
        return

    # 检查numpy依赖
    try:
        import numpy as np
        print("✓ NumPy已安装")
    except ImportError:
        print("❌ 未安装NumPy，请先安装：pip install numpy")
        return

    # 设置输入路径
    png_dir = input("\n请输入PNG文件目录路径: ").strip()
    if not png_dir:
        png_dir = "./data"  # 默认路径

    coord_file = input("请输入坐标信息文件路径 (coordinates.json 或 coordinates.csv): ").strip()
    if not coord_file:
        coord_file = "./coordinates/coordinates.json"  # 默认路径

    output_dir = input("请输入输出TIF文件目录路径 (回车使用当前目录下的output_tif): ").strip()
    if not output_dir:
        output_dir = "./output_tif"

    print(f"\n📂 PNG目录: {png_dir}")
    print(f"📍 坐标文件: {coord_file}")
    print(f"📁 输出目录: {output_dir}")

    # 开始处理
    process_png_to_tif(png_dir, coord_file, output_dir)


if __name__ == "__main__":
    main()