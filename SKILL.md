---
name: product-motion-rhythm
description: 从参考宣传片提取镜头、排版、运动和声音结构，为不同产品制作音乐与真实动作事件共同驱动的动效影片及可编辑工程。用于产品广告、App和开发者工具宣传片、参考复刻及音画节奏优化。
metadata:
  short-description: 参考驱动的产品动效与音画联合制作
---

# 产品动效与声音联合制作

交付可播放 MP4、可编辑工程及可追溯的音画时间表。参考决定运动与声音的语法，不只决定配色。先区分同内容重建与换品牌重制；跨产品不声称全画面像素级一致。

## 默认路径

**产品叙事 → 选曲与音乐结构 → 镜头及动作编排 → 分层声音设计 → 混音 → 声画验收。**

1. 获取产品真实界面、品牌资产、用途与核心信息，继承已约定的片长；无约定时以约20秒、16:9、1080p为起点。只向用户询问会影响结果且无法从现有上下文取得的信息。
2. 读 [取证流程](references/forensic-workflow.md) 和 [视觉图谱](references/reference-atlas.md)，选一个主参考及必要的辅助段。涉及声音时读 [声音配方与证据](references/sound-recipes.md)：当前16段参考中12段有有效声音，4段仅画面有效。不要把混合音轨冒充可复用的独立分轨。
3. 按 [音画制作流程](references/audio-workflow.md) 先选曲、检查乐句与结尾，再确定镜头。优先用户已确认的可用库；不足时自动检索并核对具体素材用途与条款，不自动购买。参考片全部为 `reference_only`，不直接抽取到新成片。音源不足或工具异常时明确报告，不回退到单调循环。
4. 建立真实 `shot-map.json` 与 [关联时间数据](references/audio-contract.md)：`music-analysis.json`、`motion-events.json`、`cue-sheet.json`。画面渲染器消费最终动作表，声音定位到可听起音／峰值。先复核音乐锚点，允许在动作窗口内微调，保持总帧数、产品信息、文字阅读时间和衔接对象。
5. 按 [运动制作](references/production.md) 实现2–3个最具辨识度的连续过渡，检查连续帧，再扩展全片。音效按动作与材质选择，点击贴接触、掠过峰值贴速度峰值、撞击贴落定、持续声随速度变化；留白也是编排，不给每次切镜机械加whoosh。
6. 分开制作 BGM、SFX、texture、可选voice，再混音。默认48kHz立体声，约−16 LUFS、真峰值≤−1dBTP为起点；按内容调整并记录理由。使用 `scripts/mix_audio.py` 的两遍测量流程，导出后重新检测编码成片。
7. 按 [视觉验收](references/quality.md) 和 [声音验收](references/audio-qa.md) 复核。同步测量目标为明确事件≤一帧；有意提前／延后另记。完整播放听查段落、重复疲劳、掩蔽、接缝与结尾，不能以信号检测替代听感。无法听审时标记 `not_performed`，交付审阅版并明确未完成项。
8. 交付成片、源工程、三份时间数据、素材来源与验收结果。分轨留在项目工作区；按许可决定可分享范围。不要把禁止独立再分发的库存音频、参考原片打进skill或通用模板。

## 保留参考的运动语法

- 画面是舞台：短词、满屏大字、局部控件、设备、抽象体积与品牌留白形成大小和密度对比。默认不叠四角常驻文字、编号、页脚、进度条或全片固定字幕。
- 同一对象承担衔接：按钮→节点→曲线→界面；文字→胶囊→越框。使用共享世界坐标、遮挡与摄影机关系，避免重绘两份相似图形后用淡化掩盖接缝。
- 阅读停留与运动爆发交替。动作有蓄力、加速、过冲和收束，不把所有镜头做成等长卡片或同款ease-out。
- 原参考24/30fps也能流畅；60fps需计算真实新帧。先修曲线、材质、摄影机，再加亚帧采样。不能用平面圆角卡片冒充参考里的金属、玻璃和空间穿行。

## 工具与资源

依赖 Python 3.10+、NumPy、SciPy、FFmpeg/FFprobe；视觉示例另需Pillow／Blender。音频分析使用SciPy，不强制依赖librosa。

- `scripts/analyze_audio.py`：有效声音判断、能量／音色密度曲线、瞬态／速度／段落候选。候选不是已确认的音乐重拍。
- `scripts/plan_audio.py`：授权音源选择、复核锚点内重定时、起音／峰值补偿、三份关联数据。
- `scripts/mix_audio.py`、`scripts/check_audio.py`：分层混音、实际编码音频模板匹配、响度及同步检测。
- `scripts/fetch_audio_asset.py`：下载已核验的具体音源并登记哈希；搜索与条款判断见流程。资源入口见 [音源索引](references/audio-sources.json)。
- `scripts/motion_math.py`、`reference_sheets.py`、`check_timeline.py` 与 `references/evidence/`：沿用逐帧运动重建工具和证据。
- `assets/motion-starter/`：可改造的视觉技术例子，先读 `asset-contract.json`。`score.py` 仅在显式 `--diagnostic` 时用于技术测试，不能作为成品默认配乐。示例不代表所有产品的固定分镜。
