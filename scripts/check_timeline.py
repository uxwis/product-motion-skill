import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('storyboard');p.add_argument('--video');a=p.parse_args();d=json.loads(pathlib.Path(a.storyboard).read_text(encoding='utf-8-sig'));sc=d['scenes'];end=0
for i,s in enumerate(sc):
 assert s['start_frame']==end,f'gap or overlap at scene {i}'
 assert s['end_frame']>s['start_frame'],f'empty scene {i}'
 assert s['duration_frames']==s['end_frame']-s['start_frame'],f'duration mismatch {i}'
 assert s.get('reference_file') and s.get('reference_fps')>0,f'missing reference binding {i}'
 assert s.get('reference_out_frame')>s.get('reference_in_frame'),f'invalid reference range {i}'
 assert not s.get('persistent_overlays'),f'unreviewed permanent overlay {i}'
 end=s['end_frame']
assert end==d['total_frames'],'incorrect total'
if a.video:
 meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',a.video]));v=next(s for s in meta['streams'] if s['codec_type']=='video');assert int(v['nb_read_frames'])==end,'actual video frame count mismatch';assert (v['width'],v['height'])==(d['width'],d['height']),'dimension mismatch';assert abs(float(meta['format']['duration'])-end/d['fps'])<.05,'duration mismatch'
print(json.dumps({'timeline':'pass','scenes':len(sc),'frames':end,'duration':end/d['fps'],'visual_similarity':'requires actual image and motion review'},ensure_ascii=False))
