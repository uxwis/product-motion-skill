"""Motion compositor: frame-addressable type, camera, reference sampled tracks, PBR plates.
No per-scene title template, corner labels, grid, or persistent product chrome.
python compose.py --preview | python compose.py --render
"""
from pathlib import Path
import sys,json,math,subprocess,functools,wave
import numpy as np
from scipy.interpolate import PchipInterpolator
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops
R=Path(__file__).resolve().parent;A=R/'assets';W,H=1920,1080;FPS=60
WHITE='#fbfbfd';BLACK='#050509';BLUE='#1266ff';SKY='#ddecff';GRAY='#858690'
fonts={'r':A/'Inter-Regular-9.otf','m':A/'Inter-Medium-8.otf','s':A/'Inter-SemiBold-10.otf','b':A/'Inter-Bold-4.otf','cn':A/'NotoSansSC-VF.ttf','mono':A/'consola.ttf' if (A/'consola.ttf').exists() else Path('C:/Windows/Fonts/consola.ttf')}
@functools.lru_cache(600)
def font(n,k='r'):
 f=ImageFont.truetype(str(fonts[k]),max(1,int(n)))
 if k=='cn':
  try:f.set_variation_by_axes([650])
  except Exception:pass
 return f

def cl(x):return max(0,min(1,x))
def out(x):return 1-(1-cl(x))**3
def io(x):x=cl(x);return x*x*x*(10+x*(-15+6*x))
def mix(a,b,p):return a+(b-a)*p

def base(color=WHITE):return Image.new('RGB',(W,H),color)
@functools.lru_cache(1000)
def glyph(s,n,c=BLACK,k='r'):
 f=font(n,k);bb=f.getbbox(s);pad=12;im=Image.new('RGBA',(bb[2]-bb[0]+pad*2,bb[3]-bb[1]+pad*2));ImageDraw.Draw(im).text((pad-bb[0],pad-bb[1]),s,font=f,fill=c);return im

def put(im,a,x=960,y=540,scale=1,rotation=0,opacity=1):
 if scale<=0 or opacity<=0:return
 if a.mode!='RGBA':a=a.convert('RGBA')
 ww=max(1,round(a.width*scale));hh=max(1,round(a.height*scale))
 if ww>12000 or hh>10000:raise ValueError('Unbounded camera scale')
 if ww*hh>W*H*1.6:
  # Sample the camera viewport directly instead of building a huge offscreen
  # image just to crop most of it away during a macro move.
  rad=math.radians(rotation);c=math.cos(rad);s=math.sin(rad)
  mat=(c/scale,-s/scale,a.width/2-c*x/scale+s*y/scale,s/scale,c/scale,a.height/2-s*x/scale-c*y/scale)
  a=a.transform((W,H),Image.Transform.AFFINE,mat,Image.Resampling.BICUBIC)
  if opacity<.999:a.putalpha(a.getchannel('A').point(lambda v:round(v*cl(opacity))))
  im.paste(a,(0,0),a);return
 if (ww,hh)!=a.size:a=a.resize((ww,hh),Image.Resampling.LANCZOS)
 if rotation:a=a.rotate(rotation,Image.Resampling.BICUBIC,expand=True)
 if opacity<.999:a=a.copy();a.putalpha(a.getchannel('A').point(lambda v:round(v*cl(opacity))))
 im.paste(a,(round(x-a.width/2),round(y-a.height/2)),a)

def text(im,s,x=960,y=540,n=100,c=BLACK,k='r',scale=1,rotation=0,opacity=1):put(im,glyph(s,n,c,k),x,y,scale,rotation,opacity)

def rr(im,cx,cy,w,h,fill,r=None,line=None,width=1):
 if w<=0 or h<=0:return
 ImageDraw.Draw(im).rounded_rectangle((round(cx-w/2),round(cy-h/2),round(cx+w/2),round(cy+h/2)),radius=round(min(w,h)/2 if r is None else r),fill=fill,outline=line,width=width)

@functools.lru_cache(4)
def gradient(kind):
 yy,xx=np.mgrid[0:H,0:W];u=xx/W;v=yy/H
 if kind=='blue':
  co=np.zeros((H,W,3),float);co[:]=[238,244,255]
  for x,y,r,col in [(.14,.12,.52,[-30,-35,0]),(.88,.8,.6,[-40,-15,0]),(.5,.5,.3,[15,7,0])]:co+=np.exp(-((u-x)**2+(v-y)**2)/(r*r))[...,None]*np.array(col)
 else:
  co=np.zeros((H,W,3),float);co[:]=[3,4,10]
  for x,y,r,col in [(.7,.4,.7,[1,5,15]),(.2,.8,.5,[1,3,10])]:co+=np.exp(-((u-x)**2+(v-y)**2)/(r*r))[...,None]*np.array(col)
 return Image.fromarray(np.uint8(np.clip(co,0,255)))

tracks=json.loads((A/'measured-tracks.json').read_text());interp={}
for name,rec in tracks.items():
 for prop in ['x','y','w','h']:
  samples=rec['samples'];interp[name,prop]=PchipInterpolator(np.linspace(0,1,len(samples)),[z[prop] for z in samples])
def track(name,prop,p):return float(interp[name,prop](cl(p)))

@functools.lru_cache(24)
def plate(kind,frame):
 file=A/f'3d-{kind}'/f'{frame:04d}.png'
 if not file.exists():
  if '--preview' in sys.argv:return Image.open(R/'qa'/f'3d-{kind}.png').convert('RGBA').resize((W,H),Image.Resampling.LANCZOS)
  raise FileNotFoundError(file)
 return Image.open(file).convert('RGBA')
logo=Image.open(A/'logo-dark.png').convert('RGBA');logoblack=Image.open(A/'logo-light.png').convert('RGBA');screen=Image.open(A/'screen-install.png').convert('RGBA')

@functools.lru_cache(2)
def phone_flat():
 im=Image.new('RGBA',(1000,2140));d=ImageDraw.Draw(im);d.rounded_rectangle((8,0,992,2135),radius=145,fill='#33363e');d.rounded_rectangle((20,8,980,2125),radius=140,fill='#09090b');a=screen.resize((900,1950));im.paste(a,(50,80));return im

@functools.lru_cache(3)
def shadowpill(w,h):
 layer=Image.new('RGBA',(w+140,h+140));ImageDraw.Draw(layer).rounded_rectangle((70,80,w+70,h+80),radius=h/2,fill=(0,0,0,16));return layer.filter(ImageFilter.GaussianBlur(24))

@functools.lru_cache(1)
def install_control():
 # Preserve the actual 3D-projected control through the match transition.
 angle=math.radians(-5);ax=math.cos(angle)*21+math.sin(angle)*185;ay=-math.sin(angle)*21+math.cos(angle)*185
 im=base();put(im,plate('phone',113),960-2.81*ax,540-2.81*ay,2.81,rotation=-5)
 im=im.crop((425,452,1495,628)).convert('RGBA');mask=Image.new('L',im.size,0);ImageDraw.Draw(mask).rounded_rectangle((0,0,1069,175),radius=50,fill=255);im.putalpha(mask);return im

story=json.loads((R/'storyboard.json').read_text(encoding='utf8'))
# Main camera and local object animation are sampled at subframe times, so fast
# 2D moves get temporal shutter blur instead of hard frame-to-frame edges.
def scene(t):
 frame=min(1799,t*60);s=next(x for x in story['scenes'] if x['start_frame']<=frame<x['end_frame']);m=s['mode'];dt=(frame-s['start_frame'])/60;dur=s['duration_frames']/60;p=dt/dur
 im=base()
 if m in ['code','out','device']:
  if m=='code':word,n,k,col='Code.',150,'m',BLACK
  elif m=='out':word,n,k,col='Out.',190,'s',BLUE
  else:word,n,k,col='上真机。',160,'cn',BLACK
  z=mix(.86,1,out(dt/.18));scale=z*(1+.12*out(max(0,p-.65)/.35));text(im,word,n=n,k=k,c=col,scale=scale,y=540+36*(1-out(dt/.18)))
 elif m=='coins':
  im=gradient('blue').copy();f=min(120,max(1,round(dt*60)+1));scale=1+.11*io(p);put(im,plate('coin',f),960,510,scale)
  if dt>.60:text(im,'COOT',960,935,66,BLACK,'s',opacity=out((dt-.6)/.2))
  # Coin cluster moves towards camera as the next command takes the same centre.
  if p>.82:
   sc=1+.8*io((p-.82)/.18);im=im.resize((round(W*sc),round(H*sc)),Image.Resampling.BICUBIC).crop((round((W*sc-W)/2),round((H*sc-H)/2),round((W*sc+W)/2),round((H*sc+H)/2)))
 elif m=='command':
  im=gradient('blue').copy();txt='Deploy with Coot.';count=max(0,min(len(txt),int(dt*28)+1));phrase=txt[:count]
  # Begin in a macro field. It contracts from full frame into the next capsule.
  z=mix(1.28,1,io(min(1,dt/.6)));z*=mix(1,.67,io((p-.74)/.26));w=1500*z;h=290*z
  rr(im,960,540,w,h,'#ffffff',52*z)
  text(im,phrase,960,540,n=123,k='m',scale=z)
  if count<len(txt) or p<.75:
   tx=glyph(phrase,123,BLACK,'m').width*z;ImageDraw.Draw(im).rectangle((960+tx/2+7,540-68*z,960+tx/2+13,540+68*z),fill=BLUE)
 elif m=='pill':
  im=base('#06030f');q=cl(dt/dur);w=track('pill','w',q)*W;h=track('pill','h',q)*H;cx=track('pill','x',q)*W;cy=track('pill','y',q)*H
  # Bounding boxes clip after q~.8 in the source; continue the full object camera
  # beyond the raster edge, rather than freezing at a screen-width box.
  extra=1+5*io((q-.77)/.23);w*=extra;h*=extra;cx-=900*io((q-.72)/.28)
  if .1<q<.64:
   for j in range(3,0,-1):
    z=1+j*.26+q*.15;rr(im,cx,cy,w*z,h*z,None,min(h*.24*z,90),line=tuple([32+j*6,18+j*2,69+j*10]),width=3)
  rr(im,cx,cy,w,h,'#f9f9fe',min(h*.24,100));text(im,'Deploy with Coot.',cx,cy,n=100,c=BLUE,k='m',scale=w/1125,rotation=mix(0,3,io((q-.6)/.4)))
 elif m=='terminal':
  im=base('#050509');d=ImageDraw.Draw(im);sc=1+.12*io(p);dx=-80*io(p);dy=-70*io(p)
  # Macro content without window chrome: a readable fragment is the environment.
  text(im,'$ coot deploy',960+dx,330+dy,n=105,k='mono',c=WHITE,scale=sc)
  for i,(a,b) in enumerate([('Build','Ready'),('Upload','Complete'),('Install link','Ready')]):
   tt=dt-.22-i*.27
   if tt>0:
    y=485+i*110+dy+35*(1-out(tt/.22));text(im,a,620+dx,y,n=48,k='r',c='#828491');text(im,b,1160+dx,y,n=48,k='m',c=('#fff' if i<2 else '#48dbaa'))
  # Match the measured accelerating disc, anchored in the UI before takeover.
  if dt>dur-.4:
   q=(dt-dur+.4)/.4;cx=track('disc','x',q)*W;cy=track('disc','y',q)*H;r=track('disc','w',q)*W/2
   if q>.9:r=mix(r,1250,io((q-.9)/.1))
   d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=WHITE)
 elif m=='upload':
  # White disc shrinks into the progress-control knob, reversing the camera scale.
  im=base();dt2=dt;cx=960;cy=540;w=1150;h=126
  rr(im,cx,cy,w,h,'#eceef4');vv=io((dt-.15)/1.15);left=cx-w/2;end=left+60+(w-120)*vv
  rr(im,(left+end)/2,cy,max(1,end-left),h,BLUE)
  radius=mix(1050,49,out(dt/.38));ImageDraw.Draw(im).ellipse((end-radius,cy-radius,end+radius,cy+radius),fill=WHITE)
  if dt>.28:
   text(im,'Build',left+45,360,80,k='m',opacity=out((dt-.28)/.22));text(im,'Upload',left+w-110,360,80,k='m',c=BLUE,opacity=out((dt-.42)/.22))
   text(im,'CootTest.ipa',960,730,n=40,k='r',c='#9d9ea7',opacity=out((dt-.5)/.3))
  if p>.76:
   # Control reduces while the next phone is entering, changing negative space.
   z=mix(1,.35,io((p-.76)/.24));im=im.resize((round(W*z),round(H*z)),Image.Resampling.LANCZOS);canvas=base();canvas.paste(im,(round((W-W*z)/2),round((H-H*z)/2)));im=canvas
 elif m=='phone':
  im=base();f=min(120,max(1,round(dt*60)+1));put(im,plate('phone',f),960,540)
  # Passing type behind the object: no fixed text-card + object composition.
  if p<.27:
   behind=base();text(behind,'On iPhone.',960-900*out(p/.27),540,n=170,k='m',c='#dce7fc');put(behind,plate('phone',f));im=behind
 elif m=='macro':
  im=base();q=io(p);sc=mix(1,2.81,q);angle=math.radians(-5*q)
  ax=math.cos(angle)*21+math.sin(angle)*185;ay=-math.sin(angle)*21+math.cos(angle)*185
  cx=960-q*sc*ax;cy=540-q*sc*ay
  # Real 3D final pose; camera proceeds continuously to its install control.
  put(im,plate('phone',113),cx,cy,sc,rotation=-5*q)
  if p>.76:
   # Remove surrounding UI while preserving the very same rendered control.
   # There is no duplicate text crossfade at this match transition.
   aa=io((p-.76)/.24);mask=Image.new('L',(W,H),round(255*aa));ImageDraw.Draw(mask).rounded_rectangle((425,452,1495,628),radius=50,fill=0);im=Image.composite(base(),im,mask)
 elif m=='install':
  im=base();q=out(dt/.32);scale=1.0;w=1070;h=mix(176,220,q)
  # Press -> collapse -> successful status, with one stable reading interval.
  click=io((p-.36)/.13);collapse=io((p-.53)/.22);w=mix(w,220,collapse)
  put(im,shadowpill(1070,220),960,560,scale,opacity=1-collapse)
  rr(im,960,540,w,h,BLACK if collapse<.3 else BLUE,h/2)
  if collapse<.90:
   control=install_control().resize((max(1,round(w)),max(1,round(h))),Image.Resampling.LANCZOS)
   put(im,control,960,540,scale=mix(1,.96,click),opacity=1-collapse)
  if p<.5:
   x=mix(1330,960,io((p-.1)/.3));y=mix(790,570,io((p-.1)/.3));cursor=Image.new('RGBA',(120,140));dd=ImageDraw.Draw(cursor);dd.polygon([(18,10),(18,106),(44,83),(62,128),(78,121),(60,78),(100,77)],fill='white',outline='#565862',width=3);put(im,cursor,x,y,scale=.65)
  if collapse>.5:
   v=io((collapse-.5)/.5);d=ImageDraw.Draw(im);d.line((913,541,949,577,1014,505),fill=WHITE,width=11)
 elif m=='resolve':
  im=base();q=io(dt/.43);w=mix(220,2700,q);h=mix(220,1800,q);rr(im,960,540,w,h,BLACK,min(w,h)/2)
  if dt>.27:text(im,'On your iPhone.',n=99,c=WHITE,k='m',opacity=out((dt-.27)/.25),scale=1+.06*io(p))
 elif m=='stack':
  im=base('#020409');q=io(p);text(im,'iPhone.',960+180*math.sin(p*2),540,n=305,c='#0e47d4',k='m',scale=1.3+.2*q)
  put(im,plate('stack',min(168,max(1,round(dt*60)+1))),960,540)
 elif m=='proof':
  im=base('#111111');ix=min(112,max(1,round(dt*60)+1));path=A/'proof'/f'{ix:04d}.jpg'
  if path.exists():
   footage=Image.open(path).convert('RGBA');sc=1+.1*io((p%0.5)/.5);put(im,footage,960,535,scale=sc)
 elif m=='verbs':
  # Large type changes along one spatial direction; typography is the shot.
  k=min(2,int(p*3));pp=p*3-k;word=['Build.','Upload.','Install.'][k];colors=[BLACK,BLUE,BLACK];
  n=[230,220,230][k];x=960+120*(1-out(pp/.2))-300*io((pp-.75)/.25);text(im,word,x,540,n=n,c=colors[k],k='m',scale=1+.08*io(pp))
 elif m=='payoff':
  im=gradient('blue').copy()
  if p<.44:text(im,'从 AI 代码',960,540,n=142,k='cn',scale=1+.12*io(p/.44))
  else:text(im,'到你的 iPhone。',960,540,n=144,k='cn',c=BLUE,scale=mix(.88,1.08,out((p-.44)/.3)))
 elif m=='end':
  im=base();q=out(dt/.45);put(im,logoblack,720,480,scale=.76*q);text(im,'COOT',1035,480+35*(1-q),n=167,k='s');text(im,'coot.dev',960,700,n=53,k='r',c='#767883',opacity=out((dt-.32)/.3))
 return im

# Temporal accumulation, half-frame shutter at 60fps.
def frame_image(f,blur=True):
 if not blur:return scene(f/60)
 shot=next(s for s in story['scenes'] if s['start_frame']<=f<s['end_frame'])
 mode=shot['mode'];p=(f-shot['start_frame'])/shot['duration_frames']
 rapid=(mode=='pill' and p>.65) or (mode=='coins' and p>.82) or (mode=='macro' and p<.92) or (mode=='terminal' and p>.77) or (mode=='upload' and (p<.3 or p>.75)) or (mode=='verbs') or (mode=='install' and .5<p<.8) or (mode=='resolve' and p<.3)
 if not rapid:return scene(f/60)
 # Do not accumulate across editorial cuts. Native 3D motion blur is already
 # in the plates; 2D fast movement gets four continuous shutter samples.
 result=None
 for i,offset in enumerate([-.1875,-.0625,.0625,.1875]):
  sf=min(shot['end_frame']-.0001,max(shot['start_frame'],f+offset));im=scene(sf/60)
  result=im if result is None else Image.blend(result,im,1/(i+1))
 return result

if __name__=='__main__':
 if '--preview' in sys.argv:
  for t in [.22,.65,1.40,2.8,4.3,5.9,6.6,7.25,8.4,9.18,9.6,10.55,12.2,13.6,14.8,15.5,16.3,17.5,19.25,20.6,22,22.8,23.7,24.35,25.0,25.7,26.6,28.5]:
   scene(t).save(R/'qa'/f'v2-{t:05.2f}.jpg',quality=94)
  print('Previews ready')
 elif '--render' in sys.argv:
  if '--audio' not in sys.argv and '--silent-preview' not in sys.argv:
   raise SystemExit('Supply --audio <reviewed mix.wav> or --silent-preview. The legacy score is not a production default.')
  proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','60','-i','-','-an','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(R/'coot-v2-silent.mp4')],stdin=subprocess.PIPE)
  try:
   for f in range(1800):
    proc.stdin.write(frame_image(f).tobytes())
    if f%60==0:print(f'{f}/1800',flush=True)
  finally:proc.stdin.close()
  if proc.wait():raise RuntimeError('FFmpeg encoding failed')
  if '--audio' in sys.argv:
   audio=Path(sys.argv[sys.argv.index('--audio')+1]).resolve()
   if not audio.is_file():raise FileNotFoundError(audio)
   subprocess.run(['ffmpeg','-v','error','-y','-i',str(R/'coot-v2-silent.mp4'),'-i',str(audio),'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','256k','-ar','48000','-t','30','-movflags','+faststart',str(R/'coot-v2-30s.mp4')],check=True)
  print('Complete',flush=True)
