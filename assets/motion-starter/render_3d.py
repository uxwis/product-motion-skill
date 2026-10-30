import bpy,math,sys,json
from mathutils import Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parent
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
mode=args[0] if args else 'phone';preview='--preview' in args
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES' if '--cycles' in args else 'CYCLES'
scene.cycles.samples=12;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='CUDA';prefs.get_devices()
for dev in prefs.devices:dev.use=dev.type=='CUDA'
scene.cycles.device='GPU'
if '--eevee' in args:
 scene.render.engine='BLENDER_EEVEE'
 scene.eevee.taa_render_samples=32
 scene.eevee.use_raytracing=True
scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=67 if preview else 100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8';scene.render.image_settings.compression=15
scene.render.fps=60;scene.render.use_motion_blur=True;scene.render.motion_blur_shutter=.5;scene.world.color=(.3,.3,.3)
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0

def material(name,color,metal=0,rough=.25):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough;return m
metal=material('Polished Titanium',(.20,.23,.28),.95,.16);glass=material('Obsidian Glass',(.006,.009,.018),.45,.12);blue=material('Coot Cobalt Metal',(.012,.12,.60),.8,.19)
def image_mat(file):
 m=bpy.data.materials.new(file);m.use_nodes=True;nd=m.node_tree.nodes;nd.clear();tex=nd.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'assets'/file),check_existing=True);em=nd.new('ShaderNodeEmission');em.inputs['Strength'].default_value=.9;out=nd.new('ShaderNodeOutputMaterial');m.node_tree.links.new(tex.outputs['Color'],em.inputs['Color']);m.node_tree.links.new(em.outputs[0],out.inputs['Surface']);return m
screenmat=image_mat('screen-install.png');coinmat=image_mat('coin-front.png')
def rounded(name,w,h,r,z,depth,mat,parent=None):
 pts=[]
 for cx,cy,a in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
  for k in range(13):ang=math.radians(a+k*90/12);pts.append((cx+r*math.cos(ang),cy+r*math.sin(ang)))
 n=len(pts);verts=[(x,y,z-depth/2) for x,y in pts]+[(x,y,z+depth/2) for x,y in pts];faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);obj.data.materials.append(mat);obj.parent=parent
 uv=mesh.uv_layers.new(name='UVMap')
 for pol in mesh.polygons:
  for li in pol.loop_indices:
   v=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(v.x/w+.5,v.y/h+.5)
 if depth>.001:
  be=obj.modifiers.new('Light catching bevel','BEVEL');be.width=.012;be.segments=3;obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return obj

def empty(name):o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);return o

def phone(name):
 root=empty(name);rounded('Titanium frame',2.6,5.59,.37,0,.20,metal,root);rounded('Glass black bezel',2.56,5.55,.35,.11,.025,glass,root);rounded('Install page display',2.43,5.27,.29,.131,.001,screenmat,root)
 for y,h in [(.9,.48),(-.1,.76)]:rounded('Side key',.055,h,.025,.005,.1,metal,root).location.x=-1.32;scene.objects[-1].location.y=y
 return root

def coin(name):
 root=empty(name);bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=1,depth=.21,location=(0,0,0));o=bpy.context.object;o.name='Anodized rim';o.data.materials.append(blue);o.parent=root;be=o.modifiers.new('Rounded rim','BEVEL');be.width=.04;be.segments=4
 for p in o.data.polygons:p.use_smooth=True
 # Image mapped onto a disc, avoiding transparent plane artifacts.
 n=96;verts=[(math.cos(2*math.pi*j/n)*.96,math.sin(2*math.pi*j/n)*.96,.12) for j in range(n)];me=bpy.data.meshes.new('Decal disc');me.from_pydata(verts,[],[tuple(range(n))]);ob=bpy.data.objects.new('Brand face',me);scene.collection.objects.link(ob);ob.parent=root;ob.data.materials.append(coinmat);uv=me.uv_layers.new()
 for loop in me.loops:co=me.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(co.x/1.92+.5,co.y/1.92+.5)
 return root

def area(name,loc,power,color,size):
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.energy=power;o.data.color=color;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,0))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key softbox',(2,4,8),900,(1,1,1),6);area('Cyan rim',(-5,1,4),750,(.23,.65,1),4);area('White strip',(4,-3,6),1100,(1,1,1),3)
bpy.ops.object.camera_add(location=(0,0,14));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=12;scene.camera=cam
objects=[]
if mode=='coin':objects=[coin('Hero coin')]+[coin('Satellite '+str(i)) for i in range(5)];N=120
elif mode=='stack':objects=[phone('Layer '+str(i)) for i in range(4)];N=168
else:objects=[phone('Hero phone')];N=120
if '--test' in args:N=8

def ease(t):return 1-(1-max(0,min(1,t)))**3
for f in range(1,N+1):
 t=(f-1)/60
 if mode=='coin':
  for j,o in enumerate(objects):
   if j==0:o.location=(0,.15,0);o.scale=(1.5,)*3;o.rotation_euler=(.14,.8*(1-ease(t/.8))+.12*math.sin(t*1.4),-.2+.2*ease(t/.9));o.scale=(.25+1.25*ease(t/.65),)*3
   else:
    ang=j*math.tau/5+t*.6;rad=3.6+.15*math.sin(t+j);o.location=(rad*math.cos(ang),rad*.58*math.sin(ang),-1-j*.2);o.scale=(.27+.06*j,)*3;o.rotation_euler=(math.sin(t+j)*.4,math.cos(t+j)*.6,t*.5+j)
 elif mode=='phone':
  o=objects[0];e=ease(t/.85);o.location=(.5*(1-e),-7*(1-e),0);o.rotation_euler=(math.radians(8-6*e),math.radians(-35+45*e),math.radians(-15+20*e));o.scale=(1.07+.10*ease(max(0,t-1)/.8),)*3
 elif mode=='stack':
  for j,o in enumerate(objects):
   e=ease(t/1.15);spread=(1-e);o.location=((j-1.5)*1.1*spread,(j-1.5)*.35*spread,-j*.34);o.rotation_euler=(math.radians(18-15*e),math.radians(-32+40*e),math.radians(-15+20*e));o.scale=(.93+.08*ease(t/2),)*3
 for o in objects:
  for prop in ['location','rotation_euler','scale']:o.keyframe_insert(data_path=prop,frame=f)
scene.frame_start=1;scene.frame_end=N
out=ROOT/'assets'/('3d-'+mode);out.mkdir(exist_ok=True);scene.render.filepath=str(out/'')+ '/'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(mode+'.blend')))
if preview:
 scene.frame_set(85);scene.render.filepath=str(ROOT/'qa'/('3d-'+mode+'.png'));bpy.ops.render.render(write_still=True)
else:bpy.ops.render.render(animation=True)
