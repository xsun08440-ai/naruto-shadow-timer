# -*- coding: utf-8 -*-
"""
火影忍者手游 · 左右替身计时器
================================
只截取游戏画面顶部血条/替身点区域做颜色识别，不读取、不注入、不修改游戏进程。
任意一侧的替身点减少 1 个（连续减少两个也每次都重新计时）后，
在屏幕左上 / 右上角显示该侧 15 秒倒计时。

说明：
- 左右两侧的替身点颜色会随阵营/角色变化（金色或蓝色），所以每侧都同时识别两种颜色；
- 用 4 个固定槽位计数，亮点减少才算消耗，避免技能特效造成误判；
- 只有左右两侧的 4 个槽位都出现在画面里时才会计时，登录/结算界面不会误触发。
"""

import json
import os
import time
import traceback

import cv2
import numpy as np

from ascript.android import screen
from ascript.android.system import R, Device
from ascript.android.ui import WebWindow

# ----------------------------- 可调参数 -----------------------------
DURATION = 15.0          # 冷却秒数
CAPTURE_INTERVAL = 0.045 # 两次截图间隔，约 20 fps（实际约 12-16 fps）
STABLE_FRAMES = 2        # 连续 2 帧一致就确认，降低触发延迟
ACTIVE_SETTLE = 1.0      # 刚进入对局先稳定 1 秒，避免加载动画造成假减少
SIDE_INVALID_HOLD = 3.0  # 单侧看不清多久后重置该侧基准
MATCH_LOST_HOLD = 2.5    # 两侧都消失多久后判定离开对局
STATUS_LOG_EVERY = 10.0  # 状态日志间隔

BASE = "/sdcard/airscript/model/shadow_timer"
LOG_PATH = os.path.join(BASE, "shadow_timer.log")
DEBUG_DUMP = False  # 调试时改为 True，会保存点数变化时的顶部画面
DEBUG_DIR = os.path.join(BASE, "debug")
DEBUG_LIMIT = 240

# 以屏幕宽度/高度归一化，适配 2392x1080 / 其他同比例横屏分辨率
PIP_SLOTS = {
    "left": [0.1150, 0.1275, 0.1400, 0.1525],
    "right": [0.8487, 0.8612, 0.8737, 0.8863],
}
# 3v3 / 训练场（顶部有队友头像）使用另一套更宽的点位
TEAM_SLOTS = {
    "left": [0.1325, 0.1450, 0.1575, 0.1700],
    "right": [0.8303, 0.8428, 0.8553, 0.8678],
}
PIP_Y = 0.111           # 四个替身点中心相对屏幕高度
PIP_HALF_W = 0.0067     # 单槽半宽
PIP_HALF_H = 0.024      # 单槽半高（放宽一点，兼容刘海/分辨率差异）
TEAM_PIP_Y = 0.113      # 3v3/训练场的点中心略低
TEAM_HALF_W = 0.0084
TEAM_HALF_H = 0.025

# 单槽判定：不再用固定 RGB 阈值，而是比较“槽位内部颜色面积 + 相对背景亮度”
PIP_PRESENT_MIN = 0.30  # 菱形区域内彩色像素占比达到多少才算存在替身点
PIP_V_MIN = 45          # 太暗的像素不参与
LIT_ABS_V = 190         # 正常亮度下，亮起点的亮度门槛
LIT_ABS_DIFF = 25       # 亮起点相对局部背景的最小亮度差
LIT_DIFF = 60           # 亮度被整体压暗时，用更高的相对亮度差判断
LIT_RATIO = 1.55        # 或相对背景亮度达到此倍数
DARK_V_MAX = 160        # 暗点的最高亮度
DARK_DIFF_MAX = 45      # 暗点相对背景的亮度差上限


# ----------------------------- 日志 -----------------------------
def log(*args):
    line = " ".join(str(a) for a in args)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fp:
            fp.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass
    print(line)


_debug_count = 0


def debug_snapshot(frame, tag, side, result, extra=None):
    """临时诊断：把事件发生时的顶部画面和识别数据落盘。"""
    global _debug_count
    if not DEBUG_DUMP or _debug_count >= DEBUG_LIMIT:
        return
    try:
        if not os.path.isdir(DEBUG_DIR):
            os.makedirs(DEBUG_DIR)
        _debug_count += 1
        stamp = time.strftime("%H%M%S") + ("_%03d" % int((time.time() % 1) * 1000))
        name = "%s_%s_%s" % (stamp, tag, side)
        cv2.imwrite(os.path.join(DEBUG_DIR, name + ".jpg"), frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        record = {
            "tag": tag,
            "side": side,
            "time": time.strftime("%H:%M:%S"),
            "left": result.get("left"),
            "right": result.get("right"),
            "extra": extra,
        }
        with open(os.path.join(DEBUG_DIR, "events.jsonl"), "a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


# ----------------------------- 替身点识别 -----------------------------
def classify_slot(patch, diamond, bg):
    """把单个槽位分类为 lit / dark / uncertain / absent。

    关键点：暗掉的替身点如果背景比较亮，也会有不少亮色像素；
    单看颜色阈值会把它误判成“亮起”。这里改为比较槽位内部与局部背景的亮度差，
    并检查彩色像素是否集中在菱形区域；亮暗不明确时返回 uncertain，宁可跳过也不乱计时。
    """
    if patch is None or patch.size == 0 or not diamond.any() or not bg.any():
        return "absent", 0.0, 0, 0

    p = patch.astype(np.int16)
    b = p[:, :, 0]
    g = p[:, :, 1]
    r = p[:, :, 2]

    # 金色或蓝色，亮起和暗点都包含，只用来定位“替身点身体”
    gold = (r - b > 35) & (r > g * 1.04) & (g >= b * 1.1)
    blue = (b - r > 25) & (b > g * 0.98)
    colored = gold | blue

    inside_ratio = float((colored & diamond).sum()) / float(diamond.sum())
    v = p.max(axis=2)
    vi = float(np.percentile(v[diamond], 75))
    vo = float(np.median(v[bg]))
    diff = vi - vo
    ratio = vi / max(vo, 1.0)

    present = inside_ratio >= PIP_PRESENT_MIN and vi >= PIP_V_MIN
    if not present:
        state = "absent"
    elif (vi >= LIT_ABS_V and diff >= LIT_ABS_DIFF) or \
            (diff >= LIT_DIFF and ratio >= LIT_RATIO):
        state = "lit"
    elif vi <= DARK_V_MAX and diff <= DARK_DIFF_MAX:
        state = "dark"
    else:
        # 被技能特效/闪光混合，无法可靠区分亮暗：不更新这一侧
        state = "uncertain"

    return state, inside_ratio, vi, diff


class PipDetector:
    def __init__(self, width, height, slots=None, y_ratio=None,
                 half_w_ratio=None, half_h_ratio=None):
        self.width = width
        self.height = height
        self.slots = slots or PIP_SLOTS
        self.y_ratio = PIP_Y if y_ratio is None else y_ratio
        self.half_w = max(8, int(width * (half_w_ratio or PIP_HALF_W)))
        self.half_h = max(10, int(height * (half_h_ratio or PIP_HALF_H)))

        # 预生成菱形内部区域 + 上下背景带
        ph, pw = self.half_h * 2, self.half_w * 2
        yy, xx = np.mgrid[0:ph, 0:pw]
        cy, cx = (ph - 1) / 2.0, (pw - 1) / 2.0
        self.diamond = (np.abs(xx - cx) / (pw / 2.0)
                        + np.abs(yy - cy) / (ph / 2.0)) <= 0.95
        self.bg = ((np.abs(yy - cy) > ph * 0.36)
                   & (np.abs(xx - cx) < pw * 0.4))

    def detect(self, frame):
        """frame: 从 y=0 开始截取的顶部条带，BGR。"""
        fh, fw = frame.shape[:2]
        if fw != self.width:
            self.width = fw
        y = int(self.y_ratio * self.height)
        result = {}
        for side, xs in self.slots.items():
            states = []
            details = []
            for xf in xs:
                x = int(xf * fw)
                patch = frame[max(0, y - self.half_h):y + self.half_h,
                              max(0, x - self.half_w):x + self.half_w]
                # 边缘裁剪可能让尺寸变化，尺寸不符时视为无效
                if patch.shape[0] != self.half_h * 2 or patch.shape[1] != self.half_w * 2:
                    states.append("absent")
                    details.append(("absent", 0.0, 0, 0))
                    continue
                state, ir, vi, diff = classify_slot(
                    patch, self.diamond, self.bg)
                states.append(state)
                details.append((state, round(ir, 2), int(vi), int(diff)))

            # 4 个槽位都必须是明确的 lit/dark，否则整侧视为不可靠
            valid = all(s in ("lit", "dark") for s in states)
            result[side] = {
                "count": states.count("lit"),
                "valid": valid,
                "states": states,
                "detail": details,
            }
        return result


# ----------------------------- 悬浮计时器 UI -----------------------------
class TimerHud:
    def __init__(self, width, height):
        self.window = WebWindow(R.ui("timer.html"))
        self.window.size(width, height)
        self.window.gravity(3 | 48, 0, 0)   # Gravity.TOP | Gravity.LEFT
        self.window.mode(2)                 # 触摸穿透，不挡游戏操作
        self.window.dim_amount(0)
        self.window.background("#00000000")
        self.window.show()
        self.last_payload = None

    def update_charges(self, left, right):
        state = {
            "left": {"valid": bool(left["valid"]), "charges": int(left["count"])},
            "right": {"valid": bool(right["valid"]), "charges": int(right["count"])},
        }
        if state == self.last_payload:
            return
        self.last_payload = state
        self.call("HUD.validAll(%s)" % json.dumps(
            state, ensure_ascii=False, separators=(",", ":")))

    def trigger(self, side, charges):
        self.call("HUD.trigger(%s,%d,%d)" % (
            json.dumps(side), int(DURATION * 1000), int(charges)))

    def cancel(self, side):
        self.call("HUD.cancel(%s)" % json.dumps(side))

    def reset_all(self):
        self.call("HUD.resetAll()")

    def call(self, js):
        try:
            self.window.call(js)
        except Exception:
            log("UI_CALL_ERROR", js, traceback.format_exc())


# ----------------------------- 点数状态机 -----------------------------
def update_side_count(side, s, raw, now):
    """处理一个稳定读数。

    - 减少：立即返回 trigger，不再等 0.4 秒确认；
    - 增加：只同步点数，绝不启动计时，返回 increase；
    - 一次掉 3 个以上：更像界面切换/遮挡，只同步不计时。
    """
    last = s["last_count"]
    if last is None:
        s["last_count"] = raw
        log("BASE %s=%d" % (side, raw))
        return None

    if raw > last:
        s["last_count"] = raw
        log("INCREASE %s %d->%d ignored" % (side, last, raw))
        return ("increase", last, raw)

    if raw < last:
        if last - raw <= 2:
            s["last_count"] = raw
            log("DECREASE %s %d->%d" % (side, last, raw))
            return ("trigger", last, raw)
        # 一次掉 3 个以上更像是界面切换/遮挡，不计时，仅同步
        s["last_count"] = raw
        log("BULK %s %d->%d ignored" % (side, last, raw))
    return None


# ----------------------------- 主循环 -----------------------------
def wait_for_landscape():
    while True:
        d = Device.display()
        if d.widthPixels >= d.heightPixels:
            return d
        log("等待横屏... 当前 %dx%d" % (d.widthPixels, d.heightPixels))
        time.sleep(1.0)


def main():
    global _debug_count
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as fp:
            fp.write("")
    except Exception:
        pass
    if DEBUG_DUMP:
        _debug_count = 0
        try:
            import shutil
            if os.path.isdir(DEBUG_DIR):
                shutil.rmtree(DEBUG_DIR)
        except Exception:
            pass

    display = wait_for_landscape()
    width, height = display.widthPixels, display.heightPixels
    log("start display=%dx%d rotation=%s" % (width, height, display.rotation))

    detectors = {
        "1v1": PipDetector(width, height),
        "team": PipDetector(
            width, height, slots=TEAM_SLOTS, y_ratio=TEAM_PIP_Y,
            half_w_ratio=TEAM_HALF_W, half_h_ratio=TEAM_HALF_H),
    }
    current_layout = None
    hud = TimerHud(width, height)
    time.sleep(0.35)

    sides = {}
    for side in ("left", "right"):
        sides[side] = {
            "stable_raw": None,
            "stable_n": 0,
            "last_count": None,      # 已确认、用于比较的点数
            "invalid_since": None,
        }

    last_status_log = 0.0
    announced_wait = False
    match_active = False
    active_since = 0.0
    seen = {"left": 0.0, "right": 0.0}
    last_any_valid = 0.0
    log("running")

    def reset_side(side):
        s = sides[side]
        s["last_count"] = None
        s["stable_raw"] = None
        s["stable_n"] = 0
        s["invalid_since"] = None

    def ui_state(side, data):
        s = sides[side]
        count = data["count"] if data["valid"] else (s["last_count"] or 0)
        return {"valid": bool(data["valid"]), "count": int(count)}

    while True:
        loop_start = time.monotonic()
        try:
            crop_h = int(height * 0.18)
            frame = screen.capture_cv(0, 0, width, crop_h)
            if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
                time.sleep(0.15)
                continue
            if frame.ndim != 3 or frame.shape[2] < 3:
                time.sleep(0.15)
                continue
            if frame.shape[2] > 3:
                frame = frame[:, :, :3]
            # 单应用投屏若尺寸异常（例如退到竖屏），跳过这一帧
            if frame.shape[0] < int(height * 0.1) or frame.shape[1] < int(width * 0.9):
                time.sleep(0.2)
                continue

            # 先确定当前 HUD 布局（1v1 与 3v3/训练场的点位间距不同）
            now = time.monotonic()
            if current_layout is None:
                result = detectors["1v1"].detect(frame)
                for name in ("1v1", "team"):
                    candidate = detectors[name].detect(frame)
                    if candidate["left"]["valid"] and candidate["right"]["valid"]:
                        current_layout = name
                        result = candidate
                        log("LAYOUT %s" % name)
                        break
            else:
                result = detectors[current_layout].detect(frame)

            left, right = result["left"], result["right"]

            if left["valid"]:
                seen["left"] = now
            if right["valid"]:
                seen["right"] = now
            if left["valid"] or right["valid"]:
                last_any_valid = now

            # 两侧都曾经看到过，并且最近 2.5 秒内至少有一侧还看得到，才算仍在局内。
            # 这样一侧被特效挡住时，另一侧仍然可以独立计时。
            active_now = (seen["left"] > 0 and seen["right"] > 0
                          and (now - last_any_valid) <= MATCH_LOST_HOLD)

            if not active_now:
                if match_active:
                    log("MATCH LOST / 等待进入对局")
                    debug_snapshot(frame, "match_lost", "both", result)
                    match_active = False
                    active_since = 0.0
                    current_layout = None
                    seen = {"left": 0.0, "right": 0.0}
                    for side in ("left", "right"):
                        reset_side(side)
                    # 注意：不调用 reset_all()。短暂遮挡/全屏大招不能把
                    # 正在走的 15 秒倒计时清成“待命”，让它自然走完。
                    hud.update_charges(
                        {"valid": False, "count": 0},
                        {"valid": False, "count": 0},
                    )
                if not announced_wait:
                    announced_wait = True
                    hud.update_charges(
                        {"valid": False, "count": 0},
                        {"valid": False, "count": 0},
                    )
                    log("HUD 暂未识别，等待进入对局...")
                if now - last_status_log >= STATUS_LOG_EVERY:
                    last_status_log = now
                    log("wait L=%s R=%s" % (left["detail"], right["detail"]))
                time.sleep(CAPTURE_INTERVAL)
                continue

            announced_wait = False
            if not match_active:
                active_since = now
            match_active = True

            # 刚进入对局/刚恢复画面时先稳定 1 秒，只记录基准，不触发计时
            if now - active_since < ACTIVE_SETTLE:
                for side, data in (("left", left), ("right", right)):
                    if data["valid"]:
                        s = sides[side]
                        s["last_count"] = data["count"]
                        s["stable_raw"] = data["count"]
                        s["stable_n"] = 1
                hud.update_charges(ui_state("left", left), ui_state("right", right))
                time.sleep(CAPTURE_INTERVAL)
                continue

            # ---------- 两侧独立处理：一侧看不清，不影响另一侧 ----------
            for side, data in (("left", left), ("right", right)):
                s = sides[side]
                if not data["valid"]:
                    if s["invalid_since"] is None:
                        s["invalid_since"] = now
                        debug_snapshot(frame, "invalid", side, result,
                                       {"states": data["states"]})
                    if now - s["invalid_since"] >= SIDE_INVALID_HOLD:
                        reset_side(side)
                    continue

                if s["invalid_since"] is not None:
                    debug_snapshot(frame, "recover", side, result,
                                   {"states": data["states"]})
                s["invalid_since"] = None
                raw = data["count"]

                if s["stable_raw"] == raw:
                    s["stable_n"] += 1
                else:
                    s["stable_raw"] = raw
                    s["stable_n"] = 1

                if s["stable_n"] >= STABLE_FRAMES:
                    if s["stable_n"] == STABLE_FRAMES:
                        debug_snapshot(frame, "stable", side, result,
                                       {"raw": raw, "states": data["states"],
                                        "last": s["last_count"]})
                    event = update_side_count(side, s, raw, now)
                    if event is not None and event[0] == "trigger":
                        # 立即启动，不再等 0.4 秒
                        debug_snapshot(frame, "trigger", side, result,
                                       {"old": event[1], "new": event[2]})
                        hud.trigger(side, event[2])
                        log("START %s timer  %.1fs" % (side, DURATION))
                    # 增加：只更新点数，不启动也不撤销计时。
                    # 已经开始的 15 秒倒计时不会因为方块回满/识别抖动而变成“待命”。

            # ---------- 两侧分别同步 UI ----------
            hud.update_charges(ui_state("left", left), ui_state("right", right))

            if now - last_status_log >= STATUS_LOG_EVERY:
                last_status_log = now
                log("status L=%d/%s%s R=%d/%s%s" % (
                    left["count"], left["valid"], left["states"],
                    right["count"], right["valid"], right["states"]))

        except Exception:
            log("LOOP_ERROR", traceback.format_exc())
            time.sleep(0.4)

        elapsed = time.monotonic() - loop_start
        sleep_time = CAPTURE_INTERVAL - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)


if __name__ == "__main__" or True:
    try:
        main()
    except Exception:
        log("FATAL", traceback.format_exc())
        raise
