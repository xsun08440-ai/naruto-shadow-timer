# Naruto Mobile · Left/Right Substitution Timer

[简体中文](README.md) | [English](README_EN.md)

An **AScript + OpenCV/NumPy** utility that reads substitution pips from the top of the phone screen and tracks each side independently. When either side loses a pip, its corner overlay starts a 15-second countdown. A later pip loss on that same side restarts its timer.

- **Screen pixels only:** no game-memory reads, process injection, modification, or simulated taps.
- **Runs with accessibility and screen-capture permissions:** the overlay is touch-through so it does not block gameplay.
- **Adapts to pip colors:** detects both gold and blue pips on either side.
- **Independent sides:** left and right counts, detection state, and countdowns do not affect each other.
- **Increases do not trigger:** pip increases only update the observed count. A decrease must be confirmed for two consecutive frames before it starts a timer.
- **Handles effects and occlusion:** compares each pip's brightness with its local background. If all four pips on one side cannot be classified clearly, that side's reading is skipped.

## Device and project status

The app has been installed on a PLF110 phone with AScript 4.0.12:

- AScript project: `shadow_timer`
- Android app package: `com.shadowtimer`
- Screen: `2392 × 1080`, landscape
- Floating timers: top-left and top-right
- Log: `/sdcard/airscript/model/shadow_timer/shadow_timer.log`

![Timer running in a match](preview.png)

## Android launcher app

The launcher APK is included at [`替身计时器.apk`](替身计时器.apk). It can start the timer and optionally open Naruto Mobile. The launcher offers:

- **Start timer and open game:** starts the `shadow_timer` AScript project, then opens the game.
- **Start timer only:** starts the floating timers and stays in the current app.
- **Stop timer:** stops the AScript script and closes the floating overlay.

![Android launcher app](app_preview.png)

The APK is a lightweight launcher. The recognition engine still runs in AScript, so AScript and its accessibility, overlay, and screen-capture permissions must remain available. Building a standalone APK would require the AScript developer publishing flow or a native rewrite of the recognition logic.

## Behavior and detection notes

- The app waits one second after entering a match to avoid false decreases during loading or character-switch animations.
- A timer continues through temporary HUD occlusion, flashes, and pip-count increases. It ends after 15 seconds or when the script stops.
- The detector handles both standard 1v1 HUD positions and the inward-shifted positions used in 3v3/training layouts.
- Each side is accepted only when all four pips are confidently classified as lit or dark. An unclear side is skipped without changing its count or starting a timer.
- Every confirmed decrease restarts only that side's 15-second timer.
- The Python script updates the HTML overlay through `WebWindow.call()`. The countdown animation runs in the WebView with `requestAnimationFrame`.

Regression fixtures and scripts are in `tools/`. They cover pip increases, consecutive decreases, independent sides, occlusion, and difficult brightness cases. Tests are included in the repository but have not been run as part of this upload.

## Setup

1. Install and open **AScript** on the phone.
2. Grant AScript accessibility, floating-window, and screen-capture/color-detection permissions. For screen capture, select Naruto Mobile if Android offers the per-app option.
3. Open Naruto Mobile and enter a match or training mode.
4. Open **替身计时器** and tap **Start timer and open game**. Use **Start timer only** to remain in the current app. For debugging, the project can also be run from the AScript Web IDE/project list.
5. The two overlays show the left and right timers independently:
   - `待命 / 监控中`: watching for a pip decrease;
   - `15.0 秒 / 冷却中`: that side is counting down;
   - `可用 / READY`: the 15-second timer has completed.
6. Stop the script in AScript to close the overlays. Android may request screen-capture permission again after a phone restart.

## Repository layout

```text
as_project/                 AScript project and floating timer UI
app_src/                    Android launcher source (Java)
tools/                      Detector utilities, regression scripts, and fixtures
替身计时器.as                 Importable AScript project package
替身计时器.apk               Android launcher APK
preview.png                 In-game timer screenshot
app_preview.png             Launcher screenshot
```

The local `app_build/` directory contains generated build intermediates and a signing key. It is intentionally excluded from the repository.

## How detection works

1. Capture only the top 18% of the screen: `screen.capture_cv(0, 0, width, height * 0.18)`.
2. Check four normalized pip positions on each side. Both gold and blue pip colors are accepted.
3. For each slot, compare the colored-pixel ratio and the brightness inside the pip with the brightness of the local background. Ambiguous readings are marked `uncertain` and skipped.
4. Confirm a decrease when two consecutive frames agree. Only decreases start or restart a timer; increases only synchronize the observed count.
5. Keep left and right state separate: a decrease on one side calls `HUD.trigger()` for that side only.

## Changing phones or screen resolution

Normalized coordinates should work on landscape phones with a similar aspect ratio (about 2.215:1). If detection needs adjustment:

1. Capture a match screenshot with AScript.
2. Run `tools/check_detector.py` to inspect the four pip slots on each side.
3. Adjust `PIP_Y`, `PIP_HALF_H`, or the normalized x positions in `PIP_SLOTS` in `as_project/__init__.py`.

`PIP_PRESENT_MIN` controls how many colored pixels are needed to recognize a pip. `LIT_ABS_V`, `LIT_ABS_DIFF`, `LIT_DIFF`, and `LIT_RATIO` control lit-pip detection; `DARK_V_MAX` and `DARK_DIFF_MAX` control dark-pip detection.

## Notes

- This project is for learning and personal assistance. Follow the game's terms of service; do not use it for commercial boosting, cheating, or disrupting fair play.
- The project does not read or modify game memory, inject into the game process, or automate gameplay actions.
