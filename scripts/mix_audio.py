"""Sample-accurate production mixing, internal stems and measured two-pass master."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from scipy import ndimage,signal
from audio_common import *

def envelope(a,cue):
    a=a.copy();n=len(a);env=np.ones(n)
    fi=min(n,round(float(cue.get('fade_in',0))*SR));fo=min(n,round(float(cue.get('fade_out',0))*SR))
    if fi:env[:fi]*=np.sin(np.linspace(0,np.pi/2,fi))
    if fo:env[-fo:]*=np.cos(np.linspace(0,np.pi/2,fo))
    a*=env[:,None]*10**(float(cue.get('gain_db',0))/20)
    if cue.get('gain_envelope'):
        controls=cue['gain_envelope'];times=[x['time'] for x in controls]
        if any(b<=a for a,b in zip(times,times[1:])):raise ValueError('Gain envelope must increase in time')
        clock=np.arange(n)/SR+float(cue['output_start']);gain=np.interp(clock,times,[x['db'] for x in controls]);a*=10**(gain[:,None]/20)
    pan=float(cue.get('pan',0))
    if not -1<=pan<=1:raise ValueError('Pan outside [-1,1]')
    a[:,0]*=np.sqrt(1-pan);a[:,1]*=np.sqrt(1+pan)
    return a

def mix(cue_path,outdir):
    sheet=read_json(cue_path);regpath=sheet['registry'];assets={x['id']:x for x in read_json(regpath)['assets']}
    duration=float(sheet['duration_seconds']);n=round(duration*SR);buses={k:np.zeros((n,2)) for k in ['bgm','sfx','texture','voice']};placements=[]
    for cue in sheet['music_regions']+sheet['effects']:
        if cue['bus'] not in buses:raise ValueError('Unknown mix bus')
        a=envelope(prepare_clip(regpath,assets[cue['asset_id']],cue),cue);at=round(float(cue['output_start'])*SR);src=0
        if at<0:src=-at;at=0
        count=min(len(a)-src,n-at)
        if count<=0:raise ValueError('Clip entirely outside output')
        if src+count<len(a) and not cue.get('allow_tail_trim',False):raise ValueError('Implicit clip truncation is forbidden')
        buses[cue['bus']][at:at+count]+=a[src:src+count];placements.append({'cue_id':cue['id'],'sample_start':at,'trimmed_preroll_samples':src,'sample_count':count})
    # Transparent short ducking around foreground effects, with no permanent pumping.
    fx=np.max(np.abs(buses['sfx']),axis=1);detector=ndimage.maximum_filter1d(fx,size=2401,mode='constant')
    if detector.max()>0:
        d=np.clip(detector/max(np.percentile(detector[detector>0],80),1e-9),0,1);d=ndimage.gaussian_filter1d(d,SR*.025);buses['bgm']*=10**(-float(sheet['mix'].get('duck_music_db',2.5))*d[:,None]/20)
    voice=np.sqrt(np.mean(buses['voice']**2,axis=1))
    if voice.max()>1e-7:
        d=ndimage.maximum_filter1d(voice,size=12001);d=ndimage.gaussian_filter1d(d,SR*.05);d=np.clip(d/max(np.percentile(d[d>0],75),1e-9),0,1);buses['bgm']*=10**(-7*d[:,None]/20)
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    for k,a in buses.items():
        if np.any(a):write_wav(out/(k+'-internal.wav'),a)
    mixarr=sum(buses.values());pre=out/'premaster-internal.wav';write_wav(pre,mixarr)
    meas=stereo_loudness(pre);target_i=float(sheet['mix']['target_i']);target_tp=float(sheet['mix']['target_tp'])
    if meas['input_i']=='-inf':raise ValueError('Silent master is not a completed soundtrack')
    filt=f"loudnorm=I={target_i}:TP={target_tp}:LRA=9:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:linear=true:print_format=json"
    master=out/'mix.wav';r=subprocess.run(['ffmpeg','-y','-hide_banner','-nostats','-i',str(pre),'-af',filt,'-ar',str(SR),'-ac','2','-c:a','pcm_s24le',str(master)],capture_output=True,text=True,encoding='utf8',errors='replace')
    if r.returncode:raise RuntimeError(r.stderr[-1500:])
    report={'sample_rate':SR,'sample_count':n,'duration_seconds':n/SR,'master':str(master.resolve()),'premaster_measurement':meas,'master_measurement':stereo_loudness(master),'placements':placements,'stem_policy':'internal project working files; consult asset license before redistribution. Source skill packages do not contain stock audio.','listening_review':'not_performed'}
    write_json(out/'mix-report.json',report);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cues',required=True);p.add_argument('--out',required=True);a=p.parse_args();r=mix(a.cues,a.out);print(json.dumps({'master':r['master'],'measurement':r['master_measurement']},ensure_ascii=False))
