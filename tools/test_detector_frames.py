"""从 __init__.py 抽取真实识别类，在参考截图上做回归测试。

覆盖：
- 暗点背景较亮时不能被算成亮起（f_001 / f_004）
- 亮起替身点被背景亮光干扰时不能漏算（f_027）
- 左右计数独立
运行：
    python tools/test_detector_frames.py
"""
import ast
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "as_project", "__init__.py")
FIXTURES = os.path.join(ROOT, "tools", "fixtures")

source = open(SRC, encoding="utf-8").read()
tree = ast.parse(source)

nodes = []
for node in tree.body:
    if isinstance(node, ast.Assign):
        nodes.append(node)
    elif isinstance(node, ast.FunctionDef) and node.name == "classify_slot":
        nodes.append(node)
    elif isinstance(node, ast.ClassDef) and node.name == "PipDetector":
        nodes.append(node)

module = ast.Module(body=nodes, type_ignores=[])
ast.fix_missing_locations(module)
ns = {"np": np, "os": os}
exec(compile(module, SRC, "exec"), ns)
Detector = ns["PipDetector"]

CASES = {
    # 文件: (左侧亮起点数, 右侧亮起点数)
    "f_001.jpg": (4, 2),  # 右侧 2 个暗点 + 2 个亮点，背景较亮
    "f_004.jpg": (4, 2),
    "f_010.jpg": (4, 1),
    "f_017.jpg": (4, 4),
    "f_027.jpg": (4, 4),  # 右侧第一个亮点背景很亮，不能漏算
}


def run_case(name, expected):
    path = os.path.join(FIXTURES, name)
    img = np.array(Image.open(path).convert("RGB"))[:, :, ::-1]
    h, w = img.shape[:2]
    detector = Detector(w, h)
    # 识别器只需要顶部条带，整图直接传入也可
    result = detector.detect(img)
    got = (result["left"]["count"], result["right"]["count"])
    valid = (result["left"]["valid"], result["right"]["valid"])
    ok = got == expected and all(valid)
    print(("PASS" if ok else "FAIL"), name, "counts=", got,
          "valid=", valid, "states=",
          (result["left"]["states"], result["right"]["states"]))
    return ok


def run_team_case():
    path = os.path.join(FIXTURES, "team_clean.png")
    img = np.array(Image.open(path).convert("RGB"))[:, :, ::-1]
    h, w = img.shape[:2]
    detector = Detector(
        w, h, slots=ns["TEAM_SLOTS"], y_ratio=ns["TEAM_PIP_Y"],
        half_w_ratio=ns["TEAM_HALF_W"], half_h_ratio=ns["TEAM_HALF_H"])
    result = detector.detect(img)
    got = (result["left"]["count"], result["right"]["count"])
    valid = (result["left"]["valid"], result["right"]["valid"])
    ok = got == (4, 0) and all(valid)
    print(("PASS" if ok else "FAIL"), "team_clean.png", "counts=", got,
          "valid=", valid, "states=",
          (result["left"]["states"], result["right"]["states"]))
    return ok


all_ok = True
for filename, expected in CASES.items():
    all_ok = run_case(filename, expected) and all_ok
all_ok = run_team_case() and all_ok

if not all_ok:
    raise SystemExit(1)
print("all detector frame tests passed")
