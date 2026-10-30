"""Bind real motion events to measured audible features. No implicit metronome or loops."""
import argparse,copy,json
from pathlib import Path
from fractions import Fraction
import numpy as np
from audio_common import *
from analyze_audio import analyze

def plan(registry_path,motion_path,brief_path,outdir):
    registry=read_json(registry_path);motion=read_json(motion_path);brief=read_json(brief_path)
    asset_ids=[a['id'] for a in registry['assets']]
    if len(asset_ids)!=len(set(asset_ids)):raise ValueError('Registry asset IDs must be unique')
    assets={a['id']:a for a in registry['assets']};fps=float(Fraction(str(motion['fps'])));total=int(motion['total_frames']);duration=total/fps
    if fps<=0 or total<=0:raise ValueError('Positive sample/video clocks required')
    ids=[e['id'] for e in motion['events']]
    if len(ids)!=len(set(ids)):raise ValueError('Motion event IDs must be unique')
    context=brief.get('publish_context','online_video');wanted=set(brief.get('tags',[]));choices=[]
    for a in assets.values():
        if a.get('kind')!='music':continue
        try:path=require_usable(registry_path,a)
        except (ValueError,FileNotFoundError):continue
        if context not in a['license'].get('allowed_contexts',[]):continue
        dur=float(probe(path)['format']['duration'])
        if dur<duration:continue
        choices.append((len(wanted&set(a.get('tags',[]))),a['id']))
    requested=brief.get('music_asset_id')
    if requested:music=assets[requested];require_usable(registry_path,music)
    elif choices:music=assets[sorted(choices,key=lambda x:(-x[0],x[1]))[0][1]]
    else:raise ValueError('No usable music covers this brief. Acquire a verified asset; no synthesized-loop fallback.')
    if context not in music['license'].get('allowed_contexts',[]):raise ValueError('Music not verified for this publishing context')
    ma=analyze(asset_path(registry_path,music),role='usable')
    if not ma.get('effective_audio'):raise ValueError('Selected music has no effective audio')
    regions=copy.deepcopy(brief.get('music_regions',[]));warnings=[]
    if len(regions)>1 and brief.get('phrase_review')!='reviewed' and not brief.get('diagnostic',False):
        raise ValueError('Noncontiguous music edits require phrase_review=reviewed after listening, or explicit diagnostic mode')
    if not regions:
        # Keep a continuous passage when musical phrase boundaries are unverified.
        # Novelty peaks alone never authorize destructive rearrangement.
        regions=[{'asset_id':music['id'],'source_in':float(brief.get('music_source_in',0)),'source_out':float(brief.get('music_source_in',0))+duration,'output_start':0,'gain_db':brief.get('music_gain_db',-5),'fade_in':min(.15,duration*.03),'fade_out':min(.5,duration*.08),'section_role':'continuous_passage'}]
        warnings.append('Continuous passage retained. Musical phrase/downbeat semantics need review before noncontiguous music edits.')
    music_cues=[];anchors=[]
    for i,r in enumerate(regions):
        a=assets[r.get('asset_id',music['id'])];path=require_usable(registry_path,a)
        if context not in a['license'].get('allowed_contexts',[]):raise ValueError('Region publishing context not allowed')
        cue={'id':f'music-{i:02d}','asset_id':a['id'],'bus':'bgm',**r}
        if float(cue['output_start'])<0:raise ValueError('Music cannot start before output')
        clip=prepare_clip(registry_path,a,cue)
        if float(cue['output_start'])+len(clip)/SR>duration+1/SR:raise ValueError('Music region exceeds requested video duration')
        music_cues.append(cue)
        aa=ma if a['id']==music['id'] else analyze(path,role='usable')
        for onset in aa.get('onset_candidates',[]):
            if cue['source_in']<=onset['time']<cue['source_out']:
                anchors.append((cue['output_start']+onset['time']-cue['source_in'],onset['strength']))
    resolved=copy.deepcopy(motion);retimes=[];cues=[]
    strength_floor=float(np.percentile([x[1] for x in anchors],65)) if anchors else float('inf')
    reviewed=brief.get('reviewed_music_anchors',[])
    if reviewed:
        anchors=[(float(x['output_time']),float(x.get('weight',1))) for x in reviewed if x.get('reviewed') is True]
        strength_floor=0
    elif not brief.get('allow_candidate_retime_for_test',False):
        anchors=[]
        warnings.append('No reviewed music anchors: automatic motion retiming disabled; transient candidates are not downbeats.')
    for e in resolved['events']:
        old=int(e['anchor_frame'])
        if not 0<=old<total:raise ValueError('Motion anchor outside video')
        window=e.get('window_frames',[old,old]);lo,hi=max(0,int(window[0])),min(total-1,int(window[1]))
        if not lo<=old<=hi:raise ValueError('Original event outside its permitted retime window')
        if motion.get('supports_retime') and not e.get('locked',False) and float(e.get('priority',.5))>=.7:
            candidates=[(abs(t-old/fps),-strength,round(t*fps),t) for t,strength in anchors if lo<=round(t*fps)<=hi and strength>=strength_floor]
            if candidates:
                _,_,new,target=min(candidates);e['anchor_frame']=int(new)
                retimes.append({'event_id':e['id'],'from_frame':old,'to_frame':int(new),'music_anchor':target,'basis':'reviewed musical anchor' if reviewed else 'unreviewed candidate, diagnostic only'})
        if not e.get('sfx_id'):continue
        asset=assets[e['sfx_id']];require_usable(registry_path,asset)
        if context not in asset['license'].get('allowed_contexts',[]):raise ValueError('Effect publishing context not allowed')
        cue={'id':'fx-'+e['id'],'event_id':e['id'],'asset_id':asset['id'],'bus':e.get('bus','sfx'),'source_in':e.get('source_in',0),'source_out':e.get('source_out',float(probe(asset_path(registry_path,asset))['format']['duration'])),'gain_db':e.get('gain_db',-10),'pan':e.get('pan',0),'feature':e.get('feature','peak' if e['kind'] in ['motion_peak','pass'] else 'attack'),'intent_offset_seconds':e.get('intent_offset_seconds',0),'fade_in':e.get('fade_in',.002),'fade_out':e.get('fade_out',.025),'allow_tail_trim':bool(e.get('allow_tail_trim',False))}
        clip=prepare_clip(registry_path,asset,cue);offset=feature_offset(clip,cue['feature'])
        target=e['anchor_frame']/fps+float(cue['intent_offset_seconds']);start=target-offset
        if e.get('velocity_envelope'):
            cue['gain_envelope']=[{'time':float(x['relative_frame']+e['anchor_frame'])/fps,'db':float(x['gain_db'])} for x in e['velocity_envelope']]
            cue['gain_envelope_basis']='same evaluated motion speed used by renderer; absolute output seconds'
        # Re-measure after fades/gain automation; automation can move an audible peak.
        from mix_audio import envelope
        for _ in range(12):
            cue['output_start']=start
            measured=feature_offset(envelope(clip,cue),cue['feature'])
            new_start=target-measured
            offset=measured
            if abs(new_start-start)<=1/SR:start=new_start;break
            start=new_start
        cue['output_start']=start
        residual=start+feature_offset(envelope(clip,cue),cue['feature'])-target
        if abs(residual)>1/SR:raise ValueError('Feature/automation alignment did not converge; simplify or prepare a derived sound')
        # Trimming pre-roll is only valid while the audible anchor stays in range.
        if not 0<=target<duration:raise ValueError('Audible feature target outside video')
        if start+len(clip)/SR>duration and not cue['allow_tail_trim']:raise ValueError(f"FX tail overrun: {e['id']}; move it or explicitly permit tail trim")
        cue.update(output_start=start,feature_offset_seconds=offset,target_feature_time=target,visual_anchor_frame=e['anchor_frame']);cues.append(cue)
    resolved['event_timebase']='integer frame / fps; authoritative input for the visual renderer'
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);motion_out=out/'motion-events.json';write_json(motion_out,resolved)
    sheet={'schema_version':1,'sample_rate':SR,'fps':motion['fps'],'total_frames':total,'duration_seconds':duration,'registry':str(Path(registry_path).resolve()),'motion_events_sha256':canonical_digest(resolved),'publish_context':context,'music_selection':{'asset_id':music['id'],'matched_tags':sorted(wanted&set(music.get('tags',[]))),'selection_mode':'explicit' if requested else 'catalog tags + verified duration/rights; not an asserted listening audition'},'music_regions':music_cues,'effects':cues,'retiming_proposals_applied_to_motion_file':retimes,'mix':{'target_i':brief.get('target_i',-16),'target_tp':brief.get('target_tp',-1.3),'duck_music_db':brief.get('duck_music_db',2.5)},'warnings':warnings,'listening_review':'not_performed'}
    ma['output_structure']={'regions':music_cues,'reviewed_music_anchors':reviewed,'phrase_review':brief.get('phrase_review','not_performed'),'section_roles':'editorial intentions, not inferred music semantics'}
    sheet['diagnostic']=bool(brief.get('diagnostic',False))
    write_json(out/'music-analysis.json',ma);write_json(out/'cue-sheet.json',sheet)
    return sheet

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--registry',required=True);p.add_argument('--motion',required=True);p.add_argument('--brief',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    result=plan(a.registry,a.motion,a.brief,a.out);print(json.dumps({'music':result['music_selection'],'effects':len(result['effects']),'retimes':len(result['retiming_proposals_applied_to_motion_file'])},ensure_ascii=False))
