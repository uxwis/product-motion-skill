"""Reusable reference time/curve operations. Frames remain floats until raster sampling."""
from dataclasses import dataclass
import math

def clamp(t):return min(1.,max(0.,float(t)))
def cubic_bezier(t,x1,y1,x2,y2):
 t=clamp(t)
 def b(u,a,b):return 3*(1-u)**2*u*a+3*(1-u)*u*u*b+u**3
 def db(u,a,b):return 3*(1-u)**2*a+6*(1-u)*u*(b-a)+3*u*u*(1-b)
 u=t
 for _ in range(10):
  d=db(u,x1,x2)
  if abs(d)<1e-7:break
  new=u-(b(u,x1,x2)-t)/d
  if not 0<=new<=1:break
  u=new
 lo,hi=0.,1.
 for _ in range(28):
  if abs(b(u,x1,x2)-t)<1e-9:break
  if b(u,x1,x2)<t:lo=u
  else:hi=u
  u=(lo+hi)/2
 return b(u,y1,y2)

def map_frame(output_frame,output_start,output_end,reference_start,reference_end):
 if output_end<=output_start:raise ValueError('Positive interval required')
 return reference_start+clamp((output_frame-output_start)/(output_end-output_start))*(reference_end-reference_start)

class DenseTrack:
 def __init__(self,frames,values):
  from scipy.interpolate import PchipInterpolator
  if len(frames)!=len(values) or len(frames)<2:raise ValueError('At least two aligned samples required')
  if any(b<=a for a,b in zip(frames,frames[1:])):raise ValueError('Frames must increase')
  self.first,self.last=frames[0],frames[-1];self.f=PchipInterpolator(frames,values,axis=0)
 def sample(self,frame):return self.f(min(self.last,max(self.first,frame)))

def camera_anchor(object_point,screen_anchor,scale,angle_degrees):
 """Translation for a 2D camera, image coordinates y down. Same anchor through zoom."""
 a=math.radians(angle_degrees);x,y=object_point
 return screen_anchor[0]-scale*(math.cos(a)*x+math.sin(a)*y),screen_anchor[1]-scale*(-math.sin(a)*x+math.cos(a)*y)
