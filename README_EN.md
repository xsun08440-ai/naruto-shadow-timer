<div align="center">

# Naruto Mobile · Left/Right Substitution Timer

<p><b>A computer-vision HUD detector with an independent cooldown state machine</b></p>

<p><a href="README.md">简体中文</a> · <a href="README_EN.md">English</a></p>
<p><a href="https://github.com/xsun08440-ai/naruto-shadow-timer/releases/latest">Download Android APK</a> · <a href="https://github.com/xsun08440-ai/naruto-shadow-timer">Browse source</a></p>
<p><code>Python</code> <code>OpenCV</code> <code>NumPy</code> <code>AScript Android API</code> <code>Java</code> <code>WebView</code></p>

<img src="preview.png" alt="In-match HUD and independent left/right timer overlays" width="820">

</div>

---

## Overview

This project provides real-time visual detection for the Naruto Mobile HUD. It captures the top region of the Android display, classifies substitution pips on both sides, and starts a 15-second countdown only for the side whose count decreases. A touch-through overlay renders each side's status independently.

Recognition, temporal validation, timer state, and UI rendering are separate components. The detector is not tied to a single phone model: pip locations use normalized screen coordinates, with parameter sets for standard and team/training HUD layouts. Coordinate and threshold calibration is available for different display ratios or HUD revisions.

| Vision | State processing | Android presentation |
| --- | --- | --- |
| ROI capture, color masks, local luminance features | Consecutive-frame confirmation, isolated side state machines | WebView overlay, 15-second countdown |
| OpenCV + NumPy | Python / AScript | Java launcher + HTML/CSS/JS |

## Architecture and implementation

~~~mermaid
flowchart LR
    A[Android screen capture] --> B[Top HUD ROI]
    B --> C[OpenCV / NumPy feature extraction]
    C --> D[Slot classifier: lit / dark / uncertain]
    D --> E[Temporal debounce and state machine]
    E --> F[WebWindow.call bridge]
    F --> G[WebView timer overlay<br/>HTML / CSS / JavaScript]
    H[Java launcher] --> I[AScript project deep link]
    I --> A
~~~

### Vision pipeline

1. **Region of interest (ROI):** Capture only the top ~18% of each frame to reduce unnecessary pixel processing.
2. **Layout selection:** Describe four pip slots per side with normalized coordinates; select the standard or team layout from the HUD slot distribution.
3. **Color features:** Use BGR channel relationships to extract gold and blue candidate pixels and calculate their ratio inside each diamond-shaped slot.
4. **Relative luminance classification:** Compare the 75th-percentile brightness inside a slot with the median brightness of its local background to classify it as <code>lit</code>, <code>dark</code>, or <code>uncertain</code>. A side is accepted only when all four slots are unambiguous.
5. **Temporal debounce:** Require the same pip count in two consecutive frames before updating state, reducing transient errors from flashes, occlusion, and animation.

### State machine and timers

Each side maintains its own observation baseline, stable-frame counter, and validity state. If one side is occluded or ambiguous, only that side pauses state updates; the other side continues independently.

- A decrease of 1–2 pips starts that side's 15-second countdown. A later decrease restarts only that timer.
- An increase synchronizes the observation baseline but does not start or reset a running timer.
- A change greater than 2 pips in one observation is treated as a HUD transition: synchronize the baseline without triggering a timer.
- The UI countdown continues while the HUD is briefly unavailable and returns to ready when it expires.

### Android UI and launcher

The AScript project sends state events to the HTML overlay through <code>WebWindow.call()</code>. JavaScript <code>requestAnimationFrame</code> drives the countdown in the WebView, avoiding frequent Python-to-JavaScript calls. The floating window uses touch-through mode so it does not intercept gameplay input.

The Android launcher is written in Java. Intent deep links start or stop the AScript project, and the launcher provides **Start timer and open game**, **Start timer only**, and **Stop timer** actions. **The APK is a launcher, not the recognition engine**; detection logic and overlay resources are packaged in the AScript project.

## Download and installation

Open [GitHub Releases](https://github.com/xsun08440-ai/naruto-shadow-timer/releases/latest) and download:

- **<code>naruto-shadow-timer.apk</code>**: Android launcher.
- **<code>shadow_timer.as</code>**: AScript recognition project package.

### First-time setup

1. Install **AScript 4.0.12 or later**, then import <code>shadow_timer.as</code>. The imported project should be named <code>shadow_timer</code>.
2. In Android settings, grant AScript **Accessibility, floating-window, and screen-capture/color-detection permissions**. Follow the screen-capture prompt; if per-app capture is available, select the game.
3. Install and open <code>naruto-shadow-timer.apk</code>.
4. Enter a match or training mode and tap **Start timer and open game**. Choose **Start timer only** to stay in the current app.
5. The top-left and top-right overlays display each side's recognition status and remaining time. Tap **Stop timer** to stop the script and close the overlays.

You can also import the project package and run it directly from the AScript project list. Android may request screen-capture permission again after a device restart.

## Adaptation and diagnostics

Normalized screen coordinates reduce dependence on a specific resolution. Current detector parameters target the Naruto Mobile HUD in standard and team/training layouts. If recognition becomes unstable after a display-ratio change or HUD update:

1. Capture a match screenshot and inspect slot classifications and brightness evidence with <code>tools/check_detector.py</code>.
2. Adjust <code>PIP_SLOTS</code>, <code>TEAM_SLOTS</code>, <code>PIP_Y</code>, and related coordinate parameters in <code>as_project/__init__.py</code>.
3. Calibrate classifier thresholds such as <code>PIP_PRESENT_MIN</code>, <code>LIT_DIFF</code>, and <code>DARK_DIFF_MAX</code> based on the diagnostic output.

The <code>tools/</code> directory also contains state-machine and frame-regression scripts for checking known edge cases after detector changes.

## Repository layout

~~~text
as_project/                 AScript Python recognition logic and overlay UI
  __init__.py                ROI capture, slot classification, state machine, UI bridge
  res/ui/timer.html          WebView overlay
app_src/                     Android Java launcher source
tools/                       Detector diagnostics, regression scripts, and fixtures
替身计时器.as                 Importable AScript project package
替身计时器.apk               Android launcher package
preview.png                  Project runtime preview
app_preview.png              Launcher UI preview
~~~

## Scope

- Input comes from Android screen capture. The project does not read or modify game memory, inject code into the game process, or automate gameplay actions.
- It requires Android, the AScript runtime, and the relevant system permissions. Current recognition parameters target this game's HUD; other games or major UI revisions require recalibration.
- Intended for learning computer vision and Android automation interfaces. Follow the game's terms and preserve fair play.

---

<div align="center">
<a href="README.md">简体中文</a> · <b>English</b>
</div>


