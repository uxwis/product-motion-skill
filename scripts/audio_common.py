"""Shared PCM, provenance and sample-clock operations. Python/numpy/scipy + FFmpeg."""
from pathlib import Path
import hashlib,json,subprocess,wave
import numpy as np
from scipy import signal

SR=48000
def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write_json(path,value):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def canonical_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]))
def pcm(path,sr=SR,channels=2):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-vn','-ac',str(channels),'-ar',str(sr),'-f','f32le','-'])
    return np.frombuffer(raw,'<f4').reshape(-1,channels).astype(np.float64)
def write_wav(path,a,sr=SR):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    a=np.asarray(a)
    if a.ndim==1:a=a[:,None]
    # Float WAV avoids clipping stems before the common master gain is known.
    from scipy.io.wavfile import write
    write(str(p),sr,a.astype(np.float32))
def db(x):return float(20*np.log10(max(float(x),1e-12)))
def stereo_loudness(path):
    cmd=['ffmpeg','-hide_banner','-nostats','-i',str(path),'-af','loudnorm=I=-16:TP=-1.3:LRA=9:print_format=json','-f','null','-']
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8',errors='replace')
    if r.returncode:raise RuntimeError(r.stderr[-1500:])
    start=r.stderr.rfind('{')
    return json.loads(r.stderr[start:])
def asset_path(registry_path,asset):
    p=Path(asset['path'])
    return p if p.is_absolute() else Path(registry_path).resolve().parent/p
def require_usable(registry_path,asset):
    if asset.get('role')!='usable':raise ValueError(f"Asset {asset['id']} is reference_only or diagnostic; cannot enter a production mix")
    lic=asset.get('license',{})
    if not lic.get('verified') or not lic.get('sync_allowed') or not lic.get('edit_allowed'):
        raise ValueError(f"Unverified production rights for {asset['id']}")
    if not lic.get('source_url') or not lic.get('license_url') or not lic.get('checked_at'):
        raise ValueError(f"Incomplete provenance for {asset['id']}")
    p=asset_path(registry_path,asset)
    if not p.is_file():raise FileNotFoundError(p)
    sha=asset.get('sha256','')
    if len(sha)!=64 or any(c not in '0123456789abcdefABCDEF' for c in sha):raise ValueError(f"SHA256 registration required: {asset['id']}")
    if digest(p).lower()!=sha.lower():raise ValueError(f"Asset bytes changed: {asset['id']}")
    return p
def feature_offset(a,kind='attack',sr=SR):
    if len(a)==0:raise ValueError('Empty audio feature')
    y=np.sqrt(np.mean(np.asarray(a)**2,axis=1)) if a.ndim==2 else np.abs(a)
    if y.max()<1e-8:raise ValueError('Silent asset cannot supply a feature')
    n=max(1,round(sr*.003));env=np.sqrt(np.maximum(0,signal.convolve(y*y,np.ones(n)/n,mode='same',method='fft')))
    if kind=='peak':return float(np.argmax(env)/sr)
    if kind!='attack':raise ValueError('feature must be attack or peak')
    threshold=max(env.max()*.08,1e-7)
    return float(np.flatnonzero(env>=threshold)[0]/sr)
def prepare_clip(registry_path,asset,cue):
    path=require_usable(registry_path,asset);a=pcm(path)
    start=float(cue.get('source_in',0));end=float(cue.get('source_out',len(a)/SR))
    if start<0 or end<=start or end>len(a)/SR+1/SR:raise ValueError(f"Invalid or overrun source region for {asset['id']}")
    a=a[round(start*SR):round(end*SR)]
    rate=float(cue.get('rate',1))
    if rate!=1:raise ValueError('Time stretching is not implicit. Prepare and register a pitch-preserving derived asset explicitly.')
    return a
