"""Fetch an explicitly reviewed public asset. Search/rights review remains the agent's job."""
import argparse,urllib.request,urllib.parse,hashlib,tempfile,os
from pathlib import Path
from audio_common import read_json,write_json,probe

def fetch(candidate,library):
    c=read_json(candidate);lic=c.get('license',{})
    if c.get('role')!='usable' or not all(lic.get(k) for k in ['verified','sync_allowed','edit_allowed','source_url','license_url','checked_at']):
        raise ValueError('Reviewed usable-asset provenance is required; reference videos are not music stock')
    parsed=urllib.parse.urlparse(c['download_url'])
    if parsed.scheme!='https':raise ValueError('Use the observed HTTPS download URL from the source page')
    root=Path(library).resolve();dest=(root/c['path']).resolve()
    if not dest.is_relative_to(root):raise ValueError('Asset destination outside library')
    if dest.exists():raise FileExistsError('Existing asset: verify/reuse its hash instead of overwriting')
    regpath=root/'registry.json';reg=read_json(regpath) if regpath.exists() else {'schema_version':1,'assets':[]}
    if any(a['id']==c['id'] for a in reg['assets']):raise ValueError('Duplicate asset ID')
    req=urllib.request.Request(c['download_url'],headers={'User-Agent':'Mozilla/5.0','Referer':lic['source_url']})
    chunks=[];size=0
    with urllib.request.urlopen(req,timeout=30) as r:
        for block in iter(lambda:r.read(1024*1024),b''):
            size+=len(block)
            if size>100*1024*1024:raise ValueError('Asset exceeds 100MB retrieval limit; inspect manually')
            chunks.append(block)
    data=b''.join(chunks)
    if not data:raise ValueError('Empty response')
    sha=hashlib.sha256(data).hexdigest()
    if c.get('sha256') and c['sha256'].lower()!=sha:raise ValueError('Retrieved bytes differ from reviewed hash; re-check source')
    dest.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=dest.parent,suffix='.part');os.close(fd);tmp=Path(tmp)
    try:
        tmp.write_bytes(data)
        if not any(s['codec_type']=='audio' for s in probe(tmp)['streams']):raise ValueError('Download did not contain audio')
        tmp.replace(dest)
    finally:
        if tmp.exists():tmp.unlink()
    c['sha256']=sha
    reg['assets'].append(c);write_json(regpath,reg);return c

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('candidate');p.add_argument('--library',required=True);a=p.parse_args();print(fetch(a.candidate,a.library)['id'])
