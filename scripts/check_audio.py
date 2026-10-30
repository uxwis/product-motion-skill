"""Inspect encoded output, not just declared cue timestamps. No aesthetic pass claim."""
import argparse,json
from pathlib import Path
from fractions import Fraction
import numpy as np
from scipy import signal
from audio_common import *
from mix_audio import envelope

def check(video,cue_path,visual_path,out):
    sheet=read_json(cue_path);visual=read_json(visual_path);motion=visual['motion_events'];fps=float(Fraction(str(motion['fps'])))
    if canonical_digest(motion)!=sheet['motion_events_sha256']:raise ValueError('Rendered visual events differ from the audio plan; re-plan/remix')
    ev={x['id']:x for x in motion['events']};registry=sheet['registry'];assets={x['id']:x for x in read_json(registry)['assets']};arr=pcm(video);mono=arr.mean(1)
    meta=probe(video);ast=next(x for x in meta['streams'] if x['codec_type']=='audio');vst=next((x for x in meta['streams'] if x['codec_type']=='video'),None)
    clock_ok=int(ast['sample_rate'])==SR and int(ast['channels'])==2
    if vst:
        clock_ok=clock_ok and abs(float(Fraction(vst['avg_frame_rate']))-fps)<1e-5 and int(vst.get('nb_frames',motion['total_frames']))==motion['total_frames']
    report={'encoded_file':str(Path(video).resolve()),'duration_seconds':len(arr)/SR,'expected_duration':sheet['duration_seconds'],'stream_clock_pass':clock_ok,'audio_stream':{'sample_rate':ast['sample_rate'],'channels':ast['channels']},'video_stream':{'fps':vst.get('avg_frame_rate'),'frames':vst.get('nb_frames')} if vst else None,'loudness':stereo_loudness(video),'events':[],'listening_review':'not_performed','subjective_quality':'not inferred from synchronization or loudness measurements'}
    for cue in sheet['effects']:
        a=envelope(prepare_clip(registry,assets[cue['asset_id']],cue),cue).mean(1)
        if len(a)<64:raise ValueError('Effect too short for validation')
        # Match the effect waveform in an actual decoded mix around its target.
        # Limit the template to the feature neighborhood, where it is detectable
        # against music. Use the same fades/pan/velocity envelope as the mixer.
        feature_offset_seconds=float(cue['feature_offset_seconds'])
        crop_lo=max(0,round((feature_offset_seconds-.16)*SR),-round(float(cue['output_start'])*SR))
        crop_hi=min(len(a),round((feature_offset_seconds+.22)*SR),len(mono)-round(float(cue['output_start'])*SR))
        a=a[crop_lo:crop_hi];feature_in_template=feature_offset_seconds-crop_lo/SR
        expected_start=float(cue['output_start'])+crop_lo/SR;pre=max(0,round((expected_start-.12)*SR));stop=min(len(mono),round((expected_start+len(a)/SR+.12)*SR));seg=mono[pre:stop]
        if len(a)>len(seg) or len(a)<64:
            report['events'].append({'event_id':cue['event_id'],'status':'unverified','reason':'clipped matching window'});continue
        # DC removal and normalized correlation are insensitive to master gain.
        a=a-a.mean();x=seg-seg.mean();cc=signal.correlate(x,a,mode='valid',method='fft');energy=signal.convolve(x*x,np.ones(len(a)),mode='valid',method='fft');norm=cc/np.sqrt(np.maximum(energy*np.sum(a*a),1e-20));j=int(np.argmax(norm));confidence=float(norm[j]);detected_start=(pre+j)/SR
        feature=detected_start+feature_in_template;visual_t=ev[cue['event_id']]['anchor_frame']/fps;expected_feature=visual_t+float(cue.get('intent_offset_seconds',0));error=feature-expected_feature
        status='pass' if confidence>=.22 and abs(error)<=1/fps+1/SR else ('fail' if confidence>=.22 else 'unverified')
        report['events'].append({'event_id':cue['event_id'],'status':status,'normalized_correlation':confidence,'detected_feature_time':feature,'visual_anchor_time':visual_t,'intent_offset_seconds':cue.get('intent_offset_seconds',0),'residual_error_ms':error*1000,'frame_tolerance_ms':1000/fps})
    loud=report['loudness'];i=float(loud['input_i']);tp=float(loud['input_tp']);report['signal_pass']=clock_ok and abs(len(arr)/SR-sheet['duration_seconds'])<=.05 and abs(i-float(sheet['mix']['target_i']))<=1.2 and tp<=-1
    report['synchronization_pass']=all(x['status']=='pass' for x in report['events']) if report['events'] else None;report['perceptual_pass']=None
    write_json(out,report);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--video',required=True);p.add_argument('--cues',required=True);p.add_argument('--visual-events',required=True);p.add_argument('--out',required=True);a=p.parse_args();r=check(a.video,a.cues,a.visual_events,a.out);print(json.dumps({'signal_pass':r['signal_pass'],'synchronization_pass':r['synchronization_pass'],'events':r['events'],'listening_review':r['listening_review']},ensure_ascii=False));raise SystemExit(0 if r['signal_pass'] and r['synchronization_pass'] is not False else 2)
