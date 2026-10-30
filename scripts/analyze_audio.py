"""Conservative signal analysis: onset/tempo/section candidates, never claimed listening."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy import signal,ndimage
from audio_common import probe,pcm,write_json,digest,db

def analyze(path,role='reference_only'):
    path=Path(path).resolve();meta=probe(path);streams=meta['streams'];audio=next((s for s in streams if s['codec_type']=='audio'),None)
    r={'schema_version':1,'path':str(path),'sha256':digest(path),'role':role,'duration':float(meta['format'].get('duration',0)),
       'audio_stream_present':audio is not None,'effective_audio':False,'listening_review':'not_performed',
       'semantics':{'music':'unreviewed','sfx':'unreviewed','voice':'unreviewed'},
       'method':'SciPy STFT; positive log-spectral flux; onset-autocorrelation candidates; no automatic stem separation'}
    v=next((s for s in streams if s['codec_type']=='video'),None)
    if v:r['video']={'width':v['width'],'height':v['height'],'fps':v.get('avg_frame_rate'),'time_base':v.get('time_base'),'start_time':v.get('start_time','0')}
    if audio is None:r['status']='visual_only';return r
    a=pcm(path,sr=22050,channels=2);sr=22050
    if not len(a):r['status']='empty_audio';return r
    # Existence and audibility use original channels, not a cancelling mono sum.
    peak=float(np.abs(a).max());r.update(decoded_audio_duration=len(a)/sr,rms_dBFS=db(np.sqrt(np.mean(a*a))),decoded_channel_peak_dBFS=db(peak),audio_start_time=float(audio.get('start_time',0)))
    if peak<1e-5:r['status']='silent_track';return r
    r['effective_audio']=True;r['status']='signal_analyzed'
    mono=np.mean(a,axis=1)
    if np.sqrt(np.mean(mono*mono))<np.sqrt(np.mean(a*a))*.05:
        mono=a[:,np.argmax(np.mean(a*a,axis=0))];r['mono_analysis_note']='phase cancellation detected; analyzed strongest channel'
    nfft=1024;hop=256
    _,tt,z=signal.stft(mono,fs=sr,nperseg=nfft,noverlap=nfft-hop,boundary=None)
    mag=np.abs(z);freq=np.fft.rfftfreq(nfft,1/sr)
    flux=np.r_[0,np.maximum(0,np.diff(np.log1p(mag*300),axis=1)).mean(axis=0)]
    flux=ndimage.gaussian_filter1d(flux,.65);scale=max(np.percentile(flux,95),1e-12);norm=flux/scale
    peaks,_=signal.find_peaks(norm,distance=max(1,round(.075*sr/hop)),prominence=.12)
    # Offset corresponds to STFT window centre, not FFT frame start.
    onsets=[{'time':round(float(tt[i]),6),'strength':round(float(norm[i]),4)} for i in peaks]
    r['onset_candidates']=onsets
    env=norm-np.mean(norm);ac=signal.correlate(env,env,mode='full',method='fft')[len(env)-1:]
    lo=round(60/190*sr/hop);hi=min(len(ac)-1,round(60/65*sr/hop))
    candidates=[]
    if hi>lo:
        pk,_=signal.find_peaks(ac[lo:hi+1]);lags=pk+lo
        if len(lags)==0:lags=np.array([lo+np.argmax(ac[lo:hi+1])])
        for lag in sorted(lags,key=lambda j:-ac[j])[:4]:
            bpm=60/(lag*hop/sr);period=60/bpm
            phases=np.linspace(0,period,80,endpoint=False);scores=[]
            ot=np.array([x['time'] for x in onsets]);weights=np.array([x['strength'] for x in onsets])
            for phase in phases:
                dist=np.abs((ot-phase+period/2)%period-period/2)
                scores.append(float(np.sum(weights*np.exp(-(dist/.045)**2))))
            phase=float(phases[int(np.argmax(scores))]);conf=float(max(0,ac[lag]/max(ac[0],1e-9)))
            candidates.append({'bpm':round(float(bpm),3),'periodicity':round(conf,4),'phase_seconds':round(phase,6),'beat_candidates':[round(float(x),6) for x in np.arange(phase,len(a)/sr,period)],'verified':False})
    r['tempo_candidates']=candidates
    r['beat_grid_status']='candidate_only; half/double ambiguity and SFX/voice contamination require review'
    # Half-second energy/timbre/density trajectory supports aural section review.
    energy=np.sum(mag*mag,axis=0);centroid=(mag*freq[:,None]).sum(0)/np.maximum(mag.sum(0),1e-12)
    features=[]
    for start in np.arange(0,len(a)/sr,.5):
        mask=(tt>=start)&(tt<start+.5);seg=a[round(start*sr):round((start+.5)*sr)]
        if not len(seg):continue
        features.append({'start':round(float(start),3),'end':round(min(float(start+.5),len(a)/sr),3),'rms_dBFS':round(db(np.sqrt(np.mean(seg*seg))),3),
           'spectral_centroid_hz':round(float(np.mean(centroid[mask])) if mask.any() else 0,1),
           'low_band_fraction':round(float(np.sum(mag[freq<180][:,mask]**2)/max(np.sum(mag[:,mask]**2),1e-12)),4),
           'onsets_per_second':int(sum(start<=x['time']<start+.5 for x in onsets)*2)})
    r['energy_timbre_curve']=features
    feat=np.array([[x['rms_dBFS'],x['spectral_centroid_hz'],x['onsets_per_second']] for x in features]);section=[]
    if len(feat)>10:
        feat=(feat-np.median(feat,axis=0))/np.maximum(np.std(feat,axis=0),1e-6);nov=[]
        for i in range(len(feat)):
            if i<3 or i>len(feat)-4:nov.append(0);continue
            nov.append(float(np.linalg.norm(feat[i:i+3].mean(0)-feat[i-3:i].mean(0))))
        idx,_=signal.find_peaks(nov,distance=4,prominence=.4)
        section=[{'time':features[i]['start'],'novelty':round(float(nov[i]),3),'verified':False} for i in sorted(idx,key=lambda i:-nov[i])[:14]];section.sort(key=lambda x:x['time'])
    r['section_boundary_candidates']=section
    r['limitations']=['Signal descriptors do not identify genre, musical downbeats, speech, isolated stems or subjective quality.','Candidate times use the decoded audio clock; align audio/video stream start times when comparing to video PTS.','Decoded sample peaks above 0dBFS are not themselves a true-peak or clipping verdict.']
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--role',choices=['reference_only','usable','diagnostic'],default='reference_only');args=p.parse_args()
    r=analyze(args.input,args.role);write_json(args.out,r)
    print(json.dumps({'input':args.input,'status':r['status'],'onsets':len(r.get('onset_candidates',[])),'tempo_candidates':[x['bpm'] for x in r.get('tempo_candidates',[])]},ensure_ascii=False))
