"""Legacy metronomic diagnostic only; never the default production music."""
import sys
if '--diagnostic' not in sys.argv:
 raise SystemExit('Diagnostic score only. Use --diagnostic explicitly; production requires selected, verified music and an event cue sheet.')
import numpy as np,wave,math,json
from pathlib import Path
R=Path(__file__).resolve().parent;SR=48000;N=30*SR;b=np.zeros((N,2),np.float64);rng=np.random.default_rng(4107);beat=60/128

def add(t,s,g=.1,pan=0):
 at=round(t*SR)
 if at<0:s=s[-at:];at=0
 n=min(len(s),N-at)
 if n<=0:return
 b[at:at+n,0]+=s[:n]*g*(1-pan*.4);b[at:at+n,1]+=s[:n]*g*(1+pan*.4)
def pluck(f,d=.5):
 t=np.arange(int(d*SR))/SR;return (np.sin(2*np.pi*f*t)+.18*np.sin(2*np.pi*f*2*t)+.10*np.sin(2*np.pi*f*3*t))*np.exp(-t*9)*np.minimum(t*300,1)
roots=[130.8128,155.5635,103.8262,116.5409]
for k in range(64):
 t=k*beat;root=roots[(k//8)%4]
 if k<58:
  x=np.arange(int(.3*SR))/SR;fq=43+115*np.exp(-x*32);kick=np.sin(2*np.pi*np.cumsum(fq)/SR)*np.exp(-x*16);add(t,kick,.21 if k%4 else .30)
  add(t,pluck(root/2,.42),.095)
  if k%2==1:
   x=np.arange(int(.12*SR))/SR;ns=rng.normal(0,1,len(x));snap=np.diff(ns,prepend=0)*np.exp(-x*45);add(t,snap,.028)
  for j in [0,.5]:
   x=np.arange(int(.05*SR))/SR;ns=rng.normal(0,1,len(x));add(t+j*beat,np.diff(ns,prepend=0)*np.exp(-x*125),.012,(-.6 if j else .6))
 if 4<=k<60:
  f=root*2**([12,19,24,15,12,19,27,19][k%8]/12);add(t,pluck(f,.6),.062,math.sin(k)*.7);add(t+.16,pluck(f,.5),.019,-math.sin(k)*.7)
# Warm evolving chord layer: space between transients instead of constant noise.
for k in range(0,64,8):
 t=k*beat;d=min(8*beat,30-t);x=np.arange(int(d*SR))/SR;root=roots[(k//8)%4];pad=sum(np.sin(2*np.pi*root*2**(n/12)*x) for n in [0,7,15]);env=np.minimum(1,x/.8)*np.minimum(1,(d-x)/.9);add(t,pad*env,.014)
# Camera sweeps and soft resolution stingers at the actual cut frames.
for start in [1.875,3.75,5.625,7.5,9.375,11.25,13.125,16.875,18.75,21.5625,23.4375,27.1875]:
 x=np.arange(int(.31*SR))/SR;noise=rng.normal(0,1,len(x));noise=np.convolve(noise,np.ones(14)/14,mode='same');env=np.sin(np.linspace(0,np.pi,len(x)))**2;add(start-.22,noise*env,.07)
for t in [0,.46875,.9375,23.4375,24.0625,24.6875]:add(t,pluck(783.99,.15),.065)
for d,n in [(0,0),(.11,7),(.22,12)]:add(27.1875+d,pluck(523.25*2**(n/12),1.5),.12)
fade=np.minimum(1,np.arange(N)/(SR*.03))*np.minimum(1,(N-1-np.arange(N))/(SR*1.6));b*=fade[:,None];b=np.tanh(b*1.4);b*=.87/np.max(np.abs(b))
with wave.open(str(R/'assets/score-v2.wav'),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(SR);f.writeframes((b*32767).astype('<i2').tobytes())
print('Original 128BPM / 64beat score generated')
