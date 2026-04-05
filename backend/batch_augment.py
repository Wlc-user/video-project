# -*- coding: utf-8 -*-
"""
批量增强指纹数据库脚本
将现有指纹升级到增强版
"""
import os
import sys
import json
from pathlib import Path

# 设置stdout编码为utf-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(__file__))

from fingerprint_augmenter import FingerprintAugmenter

def batch_augment_fingerprints(videos_dir: str = "data/uploads",
                                fingerprints_dir: str = "data/fingerprints",
                                dry_run: bool = False):
    """批量增强指纹"""
    videos_dir = Path(videos_dir)
    fingerprints_dir = Path(fingerprints_dir)

    # 获取所有视频文件
    videos = {v.stem: v for v in videos_dir.glob("*.mp4")}
    videos.update({v.stem: v for v in videos_dir.glob("*.avi")})

    print(f"Found {len(videos)} videos")

    # 获取所有指纹文件
    fingerprints = {fp.stem.replace("_fingerprint", ""): fp
                   for fp in fingerprints_dir.glob("*.json")}
    print(f"Found {len(fingerprints)} fingerprints")

    # 初始化增强器
    augmenter = FingerprintAugmenter(fingerprints_dir=str(fingerprints_dir))

    results = {"success": 0, "skipped": 0, "failed": 0, "errors": []}

    for name, fp_file in fingerprints.items():
        try:
            # 查找对应视频
            video = None
            for key in [name, name.replace("_fingerprint", "")]:
                if key in videos:
                    video = videos[key]
                    break

            if not video:
                print(f"  [SKIP] No video for fingerprint: {name}")
                results["skipped"] += 1
                continue

            # 加载现有指纹
            with open(fp_file, 'r', encoding='utf-8') as f:
                fingerprint = json.load(f)

            # 检查是否已有增强特征
            if fingerprint.get("has_enhanced_features"):
                print(f"  [SKIP] Already enhanced: {name}")
                results["skipped"] += 1
                continue

            # 提取增强特征
            print(f"  [PROCESS] Augmenting: {name}")
            enhanced_features = augmenter.extract_enhanced_features(str(video))

            # 添加增强特征到指纹
            fingerprint["enhanced_features"] = enhanced_features
            fingerprint["has_enhanced_features"] = True
            fingerprint["augmentation_version"] = "1.0"

            # 保存
            if not dry_run:
                with open(fp_file, 'w', encoding='utf-8') as f:
                    json.dump(fingerprint, f, indent=2, ensure_ascii=False)

            results["success"] += 1

        except Exception as e:
            print(f"  [ERROR] {name}: {str(e)}")
            results["failed"] += 1
            results["errors"].append(f"{name}: {str(e)}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="批量增强指纹数据库")
    parser.add_argument("--dry-run", action="store_true", help="仅模拟，不实际修改文件")
    parser.add_argument("--videos-dir", default="data/uploads", help="视频目录")
    parser.add_argument("--fingerprints-dir", default="data/fingerprints", help="指纹目录")

    args = parser.parse_args()

    print("=" * 60)
    print("批量增强指纹数据库")
    print("=" * 60)
    print(f"视频目录: {args.videos_dir}")
    print(f"指纹目录: {args.fingerprints_dir}")
    print(f"模式: {'模拟运行' if args.dry_run else '实际修改'}")
    print("=" * 60)

    results = batch_augment_fingerprints(
        videos_dir=args.videos_dir,
        fingerprints_dir=args.fingerprints_dir,
        dry_run=args.dry_run
    )

    print("=" * 60)
    print("结果:")
    print(f"  成功: {results['success']}")
    print(f"  跳过: {results['skipped']}")
    print(f"  失败: {results['failed']}")
    if results['errors']:
        print("错误列表:")
        for err in results['errors'][:5]:
            print(f"  - {err}")
    print("=" * 60)
