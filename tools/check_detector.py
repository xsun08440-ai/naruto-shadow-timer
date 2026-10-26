"""用一张游戏截图离线检查替身点识别结果。

用法：
    python tools/check_detector.py [截图路径]

直接抽取 as_project/__init__.py 中的真实识别器，输出每侧 4 个槽位的
状态（lit 亮起 / dark 暗点）、点数、亮度证据，方便换分辨率后校准。
"""
import ast
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "as_project", "__init__.py")

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


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "火影替身计时2.jpg")
    img = np.array(Image.open(path).convert("RGB"))[:, :, ::-1]  # RGB -> BGR
    h, w = img.shape[:2]
    print("image:", path, (w, h))
    result = Detector(w, h).detect(img)
    for side in ("left", "right"):
        data = result[side]
        print("%-5s count=%d valid=%s states=%s" % (
            side, data["count"], data["valid"], data["states"]))
        print("      detail(state, 彩色占比, V75, 相对背景亮度差)=", data["detail"])


if __name__ == "__main__":
    main()
