# 关联时间数据与命令

画面用整数帧/有理数fps，音频用48kHz时钟。换算`frame / fps`、`round(seconds * 48000)`，不累加步长。参考另存audio/video start_time/PTS，别默认各流都从0开始。

## 输入

动作数据必须被渲染器实际消费，不能独立手填一份过检。最小例：

```json
{"schema_version":1,"fps":"60","total_frames":1800,"supports_retime":true,"events":[
 {"id":"touch","kind":"contact","anchor_frame":168,"window_frames":[168,168],"locked":true,"priority":0.9,"sfx_id":"interface-click","feature":"attack","gain_db":-10},
 {"id":"pass","kind":"motion_peak","anchor_frame":306,"window_frames":[302,310],"priority":0.9,"sfx_id":"short-air","feature":"peak","gain_db":-15,"velocity_envelope":[{"relative_frame":-30,"gain_db":-24},{"relative_frame":0,"gain_db":0},{"relative_frame":30,"gain_db":-24}]}
]}
```

窗口须扣除阅读、衔接与因果依赖限制。supports_retime=false或locked=true禁止改变时刻。无音效事件省略sfx_id。intent_offset_seconds记录有意偏移，不许挪误差进去过检。可选source_in/out、pan、bus、fade、allow_tail_trim；尾音越界默认报错。

brief含产品tags、publish_context、目标响度；可指定music_asset_id和连续片段music_source_in。听审后可设置：

```json
{"tags":["clean-ui","warm","sparse"],"publish_context":"online_video","music_asset_id":"chosen-track","target_i":-16,"target_tp":-1.3,"phrase_review":"reviewed","reviewed_music_anchors":[{"output_time":5.08,"role":"phrase_accent","reviewed":true,"weight":1}]}
```

非连续音乐以music_regions数组指定asset_id、source_in/out、output_start、gain_db、fade_in/out、section_role（编辑意图，不是算法确认的乐句）。diagnostic:true供未听审的工具短样，交付保留诊断状态；allow_candidate_retime_for_test只供测试。

音源登记：id、kind(music/sfx/texture/voice)、role(usable/reference_only/diagnostic)、path、sha256、tags、license。license含verified、sync_allowed、edit_allowed、source_url、license_url、checked_at、allowed_contexts、attribution、raw_redistribution_allowed。重复ID/哈希变化报错，reference_only不能混入成品。变速须显式制作保音高的派生音源并登记，不隐式变调。

## 三份输出

- music-analysis.json：原始测量、候选速度/瞬态/段落、输出regions、复核音乐锚点、phrase_review，保留测量与听审区别。
- motion-events.json：最终动作表、窗口和重定时结果，渲染器读这一份，总帧数不变。
- cue-sheet.json：素材/事件ID、总线、source区间、output_start、feature_offset_seconds、target_feature_time、visual_anchor_frame、intent_offset、增益/声像/速度包络、动作表canonical SHA256。

文件起点=`动作时刻 + 有意偏移 − 处理后声音特征偏移`。允许静音前导裁掉，不允许可听目标落片外。改动作须重新plan/mix/render/check，不忽略哈希不匹配。

## CLI

项目先准备具体产品动作、brief、已核验音源库。下列路径是示意变量：

```powershell
python <skill>/scripts/analyze_audio.py <reference.mp4> --role reference_only --out reference-analysis.json
python <skill>/scripts/plan_audio.py --registry audio-library/registry.json --motion input-motion.json --brief brief.json --out timeline
# 视觉引擎读timeline/motion-events.json，导出picture.mp4和实际visual-events.json
python <skill>/scripts/mix_audio.py --cues timeline/cue-sheet.json --out audio
ffmpeg -i picture.mp4 -i audio/mix.wav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 256k -ar 48000 -movflags +faststart final.mp4
python <skill>/scripts/check_audio.py --video final.mp4 --cues timeline/cue-sheet.json --visual-events visual-events.json --out qa-report.json
```

visual-events.json含motion_events原对象与renderer实际执行证据，ID与实际帧一一对应；只复制JSON不证明画面触发，另检查前后帧。最终MP4还须probe验证帧数/时长、完整解码。混音输出内部bgm/sfx/texture/voice分轨（有声总线）、premaster和mix.wav；库存许可不允许裸素材分享时保留内部。
