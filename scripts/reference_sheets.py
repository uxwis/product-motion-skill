import json,pathlib,subprocess,numpy as np
from PIL import Image,ImageDraw
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
root=pathlib.Path(args.input).resolve();out=pathlib.Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True);inv=[]
from fractions import Fraction
for ix,file in enumerate(sorted(x for x in root.iterdir() if x.suffix.lower() in ['.mp4','.webm','.mov'])):
 meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(file)]));v=next(s for s in meta['streams'] if s['codec_type']=='video');inv.append(dict(id=ix+1,file=file.name,fps=float(Fraction(v['r_frame_rate'])),duration=float(meta['format']['duration'])))
(out/'inventory.json').write_text(json.dumps(inv,indent=2),encoding='utf8')
for r in inv:
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(root/r['file']),'-vf','scale=320:180','-f','rawvideo','-pix_fmt','rgb24','-an','-']);a=np.frombuffer(raw,np.uint8).reshape(-1,180,320,3)
 # Denser full-timeline sheets, 2fps for all. IDs 05/07/08/04 additionally 8fps.
 rates=[2]
 for samplefps in rates:
  frames=list(range(0,len(a),max(1,round(r['fps']/samplefps))))
  for page in range((len(frames)+29)//30):
   sel=frames[page*30:(page+1)*30];im=Image.new('RGB',(6*320,5*204),'#202020');d=ImageDraw.Draw(im)
   for j,f in enumerate(sel):x=j%6*320;y=j//6*204;im.paste(Image.fromarray(a[f]),(x,y));d.text((x+4,y+182),f'{r["id"]:02d} f{f} {f/r["fps"]:.3f}s',fill='white')
   im.save(out/f'{r["id"]:02d}-{samplefps}fps-{page+1:02d}.jpg',quality=92)
 print(r['id'],flush=True)
