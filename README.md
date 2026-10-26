<div align="center">

# 火影忍者手游 · 左右替身计时器

<p><b>基于计算机视觉与状态机的 HUD 识别和独立冷却计时方案</b></p>

<p><a href="README.md">简体中文</a> · <a href="README_EN.md">English</a></p>
<p><a href="https://github.com/xsun08440-ai/naruto-shadow-timer/releases/latest">下载 Android APK</a> · <a href="https://github.com/xsun08440-ai/naruto-shadow-timer">查看源代码</a></p>
<p><code>Python</code> <code>OpenCV</code> <code>NumPy</code> <code>AScript Android API</code> <code>Java</code> <code>WebView</code></p>

<img src="preview.png" alt="对局 HUD 与左右独立计时悬浮层" width="820">

</div>

---

## 项目概览

这是一个面向火影忍者手游 HUD 的实时视觉识别项目。运行时通过 Android 屏幕采集接口读取游戏画面顶部区域，分析左右两侧替身点状态；当某侧点数减少时，只启动该侧的 15 秒计时器，并通过触摸穿透的悬浮层显示状态。

项目将识别、时序判断、计时状态与界面渲染拆分为独立模块。实现不绑定单一手机型号：检测点使用相对屏幕宽高的归一化坐标，并提供标准对局和组队/训练 HUD 两套布局参数。更换屏幕比例或 HUD 样式时，可通过诊断工具校准坐标和阈值。

| 视觉识别 | 状态处理 | Android 展示 |
| --- | --- | --- |
| ROI 截取、颜色掩码、局部亮度特征 | 连续帧确认、左右独立状态机 | WebView 悬浮层、15 秒倒计时 |
| OpenCV + NumPy | Python / AScript | Java 启动器 + HTML/CSS/JS |

## 架构与实现

~~~mermaid
flowchart LR
    A[Android 屏幕采集] --> B[顶部 HUD ROI]
    B --> C[OpenCV / NumPy 特征提取]
    C --> D[槽位分类: lit / dark / uncertain]
    D --> E[连续帧确认与状态机]
    E --> F[WebWindow.call 桥接]
    F --> G[WebView 悬浮计时器<br/>HTML / CSS / JavaScript]
    H[Java 启动器] --> I[AScript 工程深链]
    I --> A
~~~

### 视觉识别管线

1. **区域裁剪（ROI）**：每帧仅截取屏幕顶部约 18%，减少无关像素处理。
2. **布局定位**：以归一化坐标描述左右各 4 个槽位；运行时根据 HUD 槽位分布选择标准或组队布局。
3. **颜色特征**：通过 BGR 通道关系提取金色和蓝色候选像素，并计算菱形槽位内部的彩色像素占比。
4. **相对亮度分类**：取槽位内部亮度的第 75 百分位，并与局部背景亮度中位数比较，区分 <code>lit</code>、<code>dark</code>、<code>uncertain</code>。仅当一侧 4 个槽位都明确时，才提交该侧的新读数。
5. **时序去抖**：同一点数连续两帧确认后才更新状态，降低闪光、遮挡和动画造成的瞬时误判。

### 状态机与计时

左右两侧分别维护观测基线、稳定帧计数和有效性状态。一侧被遮挡或分类不确定时只暂停该侧的状态更新，不影响另一侧。

- 点数减少 1–2 个：触发对应侧 15 秒倒计时；后续减少会重置该侧计时。
- 点数增加：只同步识别基线，不启动、不重置正在运行的计时。
- 单帧差值超过 2 个：作为界面跳变处理，只同步基线，不触发计时。
- 倒计时在 HUD 暂时不可见期间仍由 UI 独立运行，结束后回到可用状态。

### Android UI 与启动器

识别工程通过 AScript 的 <code>WebWindow.call()</code> 将状态事件传给 HTML 悬浮层；倒计时动画由 WebView 中的 JavaScript <code>requestAnimationFrame</code> 驱动，避免高频 Python/JavaScript 往返调用。悬浮窗采用触摸穿透模式，不拦截游戏触控。

Android 启动器由 Java 编写，通过 Intent 深链启动或停止 AScript 工程，并提供“启动计时器并进入游戏”“只启动计时器”“停止计时器”操作。**APK 是启动器，不包含识别引擎**；检测逻辑和悬浮层资源位于 AScript 工程包中。

## 下载与安装

打开 [GitHub Releases](https://github.com/xsun08440-ai/naruto-shadow-timer/releases/latest)，下载：

- **<code>替身计时器.apk</code>**：Android 桌面启动器。
- **<code>替身计时器.as</code>**：AScript 识别工程包。

### 首次配置

1. 安装 **AScript 4.0.12 或更新版本**，并在 AScript 中导入 <code>替身计时器.as</code>。导入后工程名应为 <code>shadow_timer</code>。
2. 在 Android 系统设置中为 AScript 开启**无障碍服务、悬浮窗和屏幕录制/图色权限**。屏幕采集权限按系统提示授权；若支持按应用采集，可选择游戏应用。
3. 安装并打开 <code>替身计时器.apk</code>。
4. 进入游戏对局或训练场，点击**“启动计时器并进入游戏”**；若希望留在当前应用，选择**“只启动计时器”**。
5. 左上与右上悬浮层分别显示两侧识别状态和剩余时间。点击**“停止计时器”**可停止脚本并关闭悬浮层。

也可以只导入工程包并从 AScript 工程列表中手动运行。重启设备后，Android 可能要求重新授权屏幕录制。

## 适配与诊断

坐标按屏幕宽高归一化，减少对具体分辨率的依赖；当前检测器针对火影忍者手游 HUD 的标准及组队/训练场布局。若显示比例或 HUD 位置变化导致识别不稳定：

1. 保存一张对局截图，用 <code>tools/check_detector.py</code> 查看各槽位的分类和亮度证据。
2. 调整 <code>as_project/__init__.py</code> 中的 <code>PIP_SLOTS</code>、<code>TEAM_SLOTS</code>、<code>PIP_Y</code> 等坐标参数。
3. 根据诊断结果校准 <code>PIP_PRESENT_MIN</code>、<code>LIT_DIFF</code>、<code>DARK_DIFF_MAX</code> 等分类阈值。

<code>tools/</code> 还包含状态机与截图帧回归脚本，便于在修改检测逻辑后复核已有边界场景。

## 项目结构

~~~text
as_project/                 AScript Python 识别逻辑与悬浮 UI
  __init__.py                ROI 采集、槽位分类、状态机、UI 桥接
  res/ui/timer.html          WebView 悬浮层
app_src/                     Android Java 启动器源码
tools/                       识别诊断、回归脚本与截图样本
替身计时器.as                 可导入 AScript 的工程包
替身计时器.apk               Android 启动器安装包
preview.png                  项目运行效果图
app_preview.png              启动器界面图
~~~

## 技术边界

- 输入来自 Android 屏幕采集，不读取或修改游戏内存，不向游戏进程注入代码，也不自动执行游戏操作。
- 运行需要 Android、AScript 运行时及相应系统权限；当前识别参数面向该游戏 HUD，其他游戏或重大 UI 改版需要重新标定。
- 项目用于学习计算机视觉和 Android 自动化接口，请遵守游戏服务条款并保持公平游戏。

---

<div align="center">
<b>简体中文</b> · <a href="README_EN.md">Read in English</a>
</div>

