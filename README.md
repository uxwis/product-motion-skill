# Product Motion Rhythm

参考驱动的产品动效与音画联合制作 skill。分析参考片的镜头、排版、运动和声音结构，制作产品宣传片、可编辑工程和可追溯的音画时间表。

## 仓库结构

```text
SKILL.md                  skill 入口与制作流程
agents/openai.yaml        Codex 展示信息
scripts/                  音频分析、编排、混音、验收和运动分析工具
references/               制作规范、参考图谱、声音配方及测量证据
assets/motion-starter/    可改造的视觉技术示例
requirements.txt          Python 依赖
```

## 安装与使用

将本仓库完整放入 `~/.codex/skills/product-motion-rhythm/`，确保该目录下直接包含 `SKILL.md`。Windows 通常对应 `%USERPROFILE%\.codex\skills\product-motion-rhythm`。

依赖 Python 3.10+；执行 `python -m pip install -r requirements.txt`。另外安装 FFmpeg（含 ffprobe）并加入 PATH。3D 示例需通过 Blender 的 Python 环境运行。

请求示例：

> 使用 $product-motion-rhythm，为我的产品制作约 20 秒的宣传片，交付 MP4、可编辑工程和音画时间表。

制作前按 `SKILL.md` 读取相应参考。`assets/motion-starter/asset-contract.json` 说明示例所需的产品、字体和其他素材；示例不是无需配置即可运行的成品。

## 素材与分发范围

仓库包含参考分析、测量数据与参考截图，不附参考原视频、库存音乐、音效、字体或用户项目。`references/audio-evidence/` 中的 `reference-media/` 路径是原始参考的逻辑标识，对应文件不随仓库分发；重新分析时需要自行提供参考片。

音源索引不是授权音频包。使用或下载音源前，应核对具体素材的当前条款。项目音频库使用 `audio-library/registry.json` 或环境变量 `PRODUCT_MOTION_AUDIO_LIBRARY` 配置。

参考截图及第三方素材的权利归原权利人所有；本次整理未核验截图的公开再分发授权。公开仓库前需确认其发布范围。仓库暂未指定开源许可证；整理操作不替作者选择授权条款。
