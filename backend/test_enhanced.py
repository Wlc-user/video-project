# -*- coding: utf-8 -*-
"""快速测试增强版相似度检测"""

import sys
import json

# 测试模块加载
print("1. 测试模块加载...")
try:
    from enhanced_fingerprint import EnhancedVideoFingerprint
    from enhanced_similarity import EnhancedSimilarityDetector
    print("   [OK] 模块加载成功")
except Exception as e:
    print(f"   [FAIL] {e}")
    sys.exit(1)

# 测试指纹生成
print("\n2. 测试指纹生成...")
try:
    fp_gen = EnhancedVideoFingerprint()
    print("   [OK] 指纹生成器初始化成功")
except Exception as e:
    print(f"   [FAIL] {e}")

# 检查数据库中的指纹
print("\n3. 检查指纹数据库...")
from pathlib import Path
fp_dir = Path("data/fingerprints")
if fp_dir.exists():
    fp_files = list(fp_dir.glob("*.json"))
    print(f"   找到 {len(fp_files)} 个指纹文件:")
    for fp in fp_files:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
            has_audio = "有" if data.get("audio_fingerprint") else "无"
            has_sift = "有" if data.get("sift_hashes") else "无"
            print(f"   - {fp.stem}: 帧={data.get('frame_count', 0)}, 音频={has_audio}, SIFT={has_sift}")
else:
    print("   [WARN] 指纹目录不存在")

# 快速比较测试
print("\n4. 快速比较测试...")
try:
    detector = EnhancedSimilarityDetector()
    print(f"   [OK] 检测器初始化成功")
    print(f"   数据库指纹数: {len(detector.fingerprints_db)}")
    
    # 显示权重配置
    print("\n   检测权重配置:")
    for name, weight in detector.weights.items():
        print(f"   - {name}: {weight*100:.0f}%")
except Exception as e:
    print(f"   [FAIL] {e}")

print("\n" + "="*50)
print("测试完成！")
