import bpy, math, random
from mathutils import Vector

FPS=12
W,H=960,540
END=FPS*30

# reset
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    pass

scene=bpy.context.scene
# try a robust real-time engine
for eng in ("BLENDER_WORKBENCH_NEXT","BLENDER_WORKBENCH"):
    try:
        scene.render.engine=eng
        break
    except: pass
scene.render.resolution_x=W
scene.render.resolution_y=H
scene.render.resolution_percentage=100
scene.render.fps=FPS
scene.frame_start=1
scene.frame_end=END
scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4'
scene.render.ffmpeg.codec='H264'
scene.render.ffmpeg.constant_rate_factor='MEDIUM'
scene.render.filepath='rarely_told_silent.mp4'
scene.world.color=(0.015,0.02,0.028)
try:
    scene.display.shading.light='STUDIO'
    scene.display.shading.color_type='MATERIAL'
    scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type='WORLD'
except: pass

# palette
NAVY=(0.035,0.055,0.08,1)
CREAM=(0.85,0.80,0.69,1)
RED=(0.80,0.055,0.045,1)
GOLD=(0.57,0.38,0.12,1)
STONE=(0.22,0.23,0.23,1)
DARK=(0.055,0.05,0.045,1)
PAPER=(0.78,0.70,0.57,1)
SKIN=(0.46,0.29,0.18,1)
COAT=(0.10,0.11,0.12,1)

def mat(name,color):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color=color
    return m
M={k:mat(k,v) for k,v in {"navy":NAVY,"cream":CREAM,"red":RED,"gold":GOLD,"stone":STONE,"dark":DARK,"paper":PAPER,"skin":SKIN,"coat":COAT}.items()}

def set_mat(o,m):
    if hasattr(o.data,'materials'):
        o.data.materials.clear(); o.data.materials.append(m)

def cube(name,loc,scale,material,bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    set_mat(o,material)
    if bevel>0:
        mod=o.modifiers.new('bev','BEVEL'); mod.width=bevel; mod.segments=2
    return o

def cyl(name,loc,r,depth,material,verts=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc)
    o=bpy.context.object; o.name=name; set_mat(o,material); return o

def sphere(name,loc,r,material):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=r,location=loc)
    o=bpy.context.object; o.name=name; set_mat(o,material); return o

def beam(name,p1,p2,r,material):
    p1,p2=Vector(p1),Vector(p2); mid=(p1+p2)/2; vec=p2-p1
    o=cyl(name,mid,r,vec.length,material,8)
    o.rotation_mode='QUATERNION'; o.rotation_quaternion=vec.to_track_quat('Z','Y')
    return o

def text_obj(name,text,loc,size,material,extrude=0.02,align='CENTER'):
    c=bpy.data.curves.new(name,'FONT'); c.body=text; c.align_x=align; c.align_y='CENTER'
    c.size=size; c.extrude=extrude; c.bevel_depth=0.005
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o); o.location=loc; set_mat(o,material); return o

def key(o,frame,loc=None,rot=None,scale=None):
    if loc is not None: o.location=loc; o.keyframe_insert('location',frame=frame)
    if rot is not None: o.rotation_euler=rot; o.keyframe_insert('rotation_euler',frame=frame)
    if scale is not None: o.scale=scale; o.keyframe_insert('scale',frame=frame)

def linear(o):
    if o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation='BEZIER'

def make_camera():
    bpy.ops.object.camera_add()
    cam=bpy.context.object; scene.camera=cam
    cam.data.lens=45
    return cam
cam=make_camera()

def cam_pose(frame,loc,target,lens=45,cut=False):
    cam.location=loc
    direction=Vector(target)-cam.location
    cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
    cam.data.lens=lens
    cam.keyframe_insert('location',frame=frame)
    cam.keyframe_insert('rotation_euler',frame=frame)
    cam.data.keyframe_insert('lens',frame=frame)
    if cut and cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                if abs(kp.co.x-frame)<0.1: kp.interpolation='CONSTANT'

# ---------- SCENE 1: animated 1925 Paris fly-in ----------
S1=0
ground=cube('ground',(0,0,-0.15),(22,32,0.15),M['navy'])
# street
cube('street',(0,-10,0.02),(4.5,22,0.03),M['stone'])
random.seed(8)
for side in (-1,1):
    for i,y in enumerate(range(-28,20,5)):
        w=random.uniform(2.0,3.2); d=random.uniform(1.7,2.6); h=random.uniform(3.5,8.0)
        x=side*(7.2+random.uniform(0.4,2.0))
        b=cube(f'bld_{side}_{i}',(x,y,h/2),(w,d,h/2),M['dark'],0.08)
        # windows
        for z in (1.4,2.8,4.2):
            if z<h-0.5:
                for xx in (-0.8,0,0.8):
                    win=cube('win',(x-side*(w+0.03),y+xx*1.7,z),(0.03,0.38,0.28),M['gold'])

# Eiffel-ish tower
def eiffel(cx=0,cy=6,base=7.2,h=15.0,matl=None):
    matl=matl or M['cream']
    z0=.2; z1=5.3; z2=10.2; z3=14.2
    corners=[(-base/2,-base/2),(base/2,-base/2),(base/2,base/2),(-base/2,base/2)]
    mids=[(-2,-2),(2,-2),(2,2),(-2,2)]
    tops=[(-.8,-.8),(.8,-.8),(.8,.8),(-.8,.8)]
    for idx,(a,b) in enumerate(zip(corners,mids)):
        beam('legA', (cx+a[0],cy+a[1],z0),(cx+b[0],cy+b[1],z1),.16,matl)
    for a,b in zip(mids,tops):
        beam('legB',(cx+a[0],cy+a[1],z1),(cx+b[0],cy+b[1],z2),.13,matl)
    for a in tops:
        beam('legC',(cx+a[0],cy+a[1],z2),(cx,cy,z3),.10,matl)
    for z,s in [(5.3,4.5),(10.2,1.9),(13.9,.7)]:
        cube('deck',(cx,cy,z),(s,s,.10),matl)
    beam('spire',(cx,cy,z3),(cx,cy,h),.10,matl)
    # cross braces
    for z,s in [(2.3,5.6),(3.8,4.9),(7.0,3.1),(8.6,2.6),(11.5,1.35)]:
        for ang in (0,math.pi/2):
            dx=math.cos(ang)*s; dy=math.sin(ang)*s
            beam('brace',(cx-dx,cy-dy,z),(cx+dx,cy+dy,z),.055,matl)
    return
eiffel()

# title as world object
t1925=text_obj('paris_title','PARIS · 1925',(-4.4,2.2,10.8),0.72,M['cream'],0.03,'LEFT')
t1925.rotation_euler=(math.radians(74),0,0)
key(t1925,1,scale=(0,0,0)); key(t1925,12,scale=(1,1,1))

# red sale tag
tag=cube('tag',(0,4.4,9.0),(2.5,.13,1.05),M['red'],0.12)
tag.rotation_euler=(math.radians(90),0,0)
sold=text_obj('sold','SOLD',(0,4.12,9.0),0.9,M['cream'],0.035)
sold.rotation_euler=(math.radians(90),0,0)
for o in (tag,sold):
    key(o,1,scale=(0,0,0))
    key(o,47,scale=(0,0,0))
    key(o,57,scale=(1.15,1.15,1.15))
    key(o,62,scale=(1,1,1))

# animated banknotes orbiting briefly
for j in range(8):
    note=cube(f'note{j}',(0,0,0),(0.55,0.03,0.28),M['paper'],0.03)
    ang=2*math.pi*j/8
    for fr,rr,z in [(58,0,9.3),(74,4.4,8.0+0.5*math.sin(ang)),(90,7.4,6.3)]:
        x=math.cos(ang+fr*.03)*rr; y=6+math.sin(ang+fr*.03)*rr
        key(note,fr,loc=(x,y,z),rot=(0,ang+fr*.04,ang))
    key(note,54,scale=(0,0,0)); key(note,61,scale=(1,1,1)); key(note,94,scale=(0,0,0))

cam_pose(1,(0,-31,4.3),(0,6,6.0),40,True)
cam_pose(40,(0,-19,5.0),(0,6,7.0),46)
cam_pose(76,(2.3,-12.5,7.2),(0,6,7.8),52)
cam_pose(92,(4.6,-8.8,8.5),(0,6,8.4),58)

# ---------- SCENE 2: animated con man on the move ----------
X=80
cube('street2',(X,0,0),(16,14,.12),M['navy'])
# stylized street walls
for i in range(7):
    cube('wall',(X-8+i*2.6,5.0,4.0),(1.2,1.0,4.0),M['dark'],.05)
for i in range(6):
    p=cyl('lamp',(X-10+i*4,-2.8,2.2),.08,4.3,M['stone'],10)
    sphere('lampglow',(X-10+i*4,-2.8,4.45),.27,M['gold'])

# low-poly victor
root=bpy.data.objects.new('victor_root',None); bpy.context.collection.objects.link(root); root.location=(X,-8,1.55)
torso=cube('torso',(0,0,0.4),(.62,.34,.9),M['coat'],.08); torso.parent=root
head=sphere('head',(0,0,1.65),.46,M['skin']); head.parent=root
hat=cyl('hat',(0,0,2.05),.56,.18,M['dark'],16); hat.parent=root
brim=cyl('brim',(0,0,1.96),.72,.08,M['dark'],16); brim.parent=root
larm=cyl('larm',(-.82,0,.35),.15,1.35,M['coat'],10); larm.parent=root
rarm=cyl('rarm',(.82,0,.35),.15,1.35,M['coat'],10); rarm.parent=root
lleg=cyl('lleg',(-.28,0,-.92),.17,1.55,M['dark'],10); lleg.parent=root
rleg=cyl('rleg',(.28,0,-.92),.17,1.55,M['dark'],10); rleg.parent=root

key(root,109,loc=(X,-8,1.55)); key(root,228,loc=(X,4.2,1.55))
for fr in range(109,229,6):
    ph=(fr-109)/6
    bob=.08*math.sin(ph*math.pi)
    root.location=(X,-8+(fr-109)/(228-109)*12.2,1.55+bob); root.keyframe_insert('location',frame=fr)
    swing=.55*math.sin(ph*math.pi)
    larm.rotation_euler=(swing,0,0); rarm.rotation_euler=(-swing,0,0)
    lleg.rotation_euler=(-swing*.72,0,0); rleg.rotation_euler=(swing*.72,0,0)
    for o in (larm,rarm,lleg,rleg): o.keyframe_insert('rotation_euler',frame=fr)
# brief newspaper/flyer catch
paper=cube('flypaper',(X-2.0,-4.0,4.8),(0.8,.03,.55),M['paper'],.03)
key(paper,120,loc=(X-2,-4,5),rot=(0,0,.5),scale=(0,0,0))
key(paper,150,loc=(X+.8,-1,3.2),rot=(.4,1.1,2.1),scale=(1,1,1))
key(paper,185,loc=(X+2.2,1.2,2.5),rot=(1.1,2.0,3.3),scale=(.8,.8,.8))
key(paper,205,scale=(0,0,0))

# animated alias cards trail him like con-history
for j,txt in enumerate(("PARIS","LONDON","NEW YORK")):
    card=cube('aliascard',(X-4+j*4,5.8,2.7),(1.7,.08,.6),M['paper'],.04)
    label=text_obj('aliastxt'+txt,txt,(X-4+j*4,5.65,2.7),.35,M['dark'],.015)
    label.rotation_euler=(math.radians(90),0,0)
    for o in (card,label):
        key(o,130+j*18,scale=(0,0,0)); key(o,145+j*18,scale=(1,1,1)); key(o,220,scale=(.78,.78,.78))

cam_pose(108,(X-10,-12,4.0),(X,-3,1.7),48,True)
cam_pose(170,(X-7,-4,3.5),(X,0,1.8),58)
cam_pose(228,(X-2,5,3.8),(X,3,1.8),52)

# ---------- SCENE 3: animated newspaper / idea moment ----------
C=160
cube('floor3',(C,0,-.15),(14,12,.15),M['navy'])
# back wall, window and simple Paris skyline
cube('wall3',(C,4.5,4.5),(14,.2,4.5),M['dark'])
cube('window',(C,4.25,5.0),(4.4,.06,2.8),M['gold'])
# table
cube('desk',(C,-.5,1.8),(4.5,2.0,.18),M['stone'],.08)
for sx in (-3.8,3.8):
    cube('deskleg',(C+sx,-.5,.8),(.22,.22,1.0),M['stone'])
# seated Victor torso
body=cube('body3',(C,1.8,3.0),(.7,.45,1.0),M['coat'],.08)
head3=sphere('head3',(C,1.8,4.25),.5,M['skin'])
hat3=cyl('hat3',(C,1.8,4.7),.6,.2,M['dark'],16)
brim3=cyl('brim3',(C,1.8,4.6),.78,.08,M['dark'],16)
arm3=cyl('arm3',(C+.85,.35,2.9),.16,1.65,M['coat'],10); arm3.rotation_euler=(math.radians(62),0,math.radians(-8))
# head tilt
key(head3,229,rot=(0,0,0)); key(head3,310,rot=(0,math.radians(-8),math.radians(-7))); key(head3,360,rot=(0,math.radians(-13),math.radians(-9)))
key(hat3,229,rot=(0,0,0)); key(hat3,310,rot=(0,math.radians(-8),math.radians(-7))); key(hat3,360,rot=(0,math.radians(-13),math.radians(-9)))
key(brim3,229,rot=(0,0,0)); key(brim3,310,rot=(0,math.radians(-8),math.radians(-7))); key(brim3,360,rot=(0,math.radians(-13),math.radians(-9)))

# newspaper unfolds in 3 panels
newsroot=bpy.data.objects.new('newsroot',None); bpy.context.collection.objects.link(newsroot); newsroot.location=(C,-1.15,2.15)
panels=[]
for j,x in enumerate((-1.7,0,1.7)):
    p=cube('paperpanel',(x,0,0),(1.65,1.55,.035),M['paper'],.02); p.parent=newsroot
    panels.append(p)
# folded -> open
for j,p in enumerate(panels):
    p.rotation_euler=(0,0,(j-1)*math.radians(78)); p.keyframe_insert('rotation_euler',frame=229)
    p.location=(0,0,0); p.keyframe_insert('location',frame=229)
    p.location=((j-1)*3.35,0,0); p.keyframe_insert('location',frame=258)
    p.rotation_euler=(0,0,0); p.keyframe_insert('rotation_euler',frame=258)
key(newsroot,229,rot=(math.radians(90),0,0),scale=(.1,.1,.1))
key(newsroot,250,rot=(math.radians(15),0,0),scale=(1,1,1))
key(newsroot,275,rot=(0,0,0),scale=(1,1,1))

# newspaper headline and rising maintenance-cost bars
headline=text_obj('headline','EIFFEL TOWER\\nCOSTS KEEP RISING',(C,-1.25,2.55),.42,M['dark'],.012)
headline.rotation_euler=(math.radians(90),0,0)
key(headline,229,scale=(0,0,0)); key(headline,268,scale=(0,0,0)); key(headline,279,scale=(1,1,1))
for j,h in enumerate((.35,.65,1.0,1.35,1.8)):
    bar=cube('bar',(C-2.8+j*1.05,-2.28,2.48+h/2),(.32,.08,h/2),M['red'],.03)
    key(bar,277+j*5,scale=(1,1,0)); key(bar,290+j*5,scale=(1,1,1))

# little 3D tower rises out of article as Victor's idea
idea_root=bpy.data.objects.new('idea_root',None); bpy.context.collection.objects.link(idea_root); idea_root.location=(C+2.25,-2.05,2.55)
# simple tower icon
for sx in (-1,1):
    beam('idea_leg',(C+2.25+sx*.55,-2.05,2.55),(C+2.25+sx*.18,-2.05,4.2),.06,M['red'])
beam('idea_top',(C+2.07,-2.05,4.2),(C+2.43,-2.05,4.2),.05,M['red'])
beam('idea_spire',(C+2.25,-2.05,4.2),(C+2.25,-2.05,4.85),.05,M['red'])
# group by parenting recently created idea objects based on name prefix
for o in list(bpy.context.scene.objects):
    if o.name.startswith('idea_') and o is not idea_root:
        o.parent=idea_root
key(idea_root,305,scale=(0,0,0),rot=(0,0,0))
key(idea_root,332,scale=(1.25,1.25,1.25),rot=(0,0,math.radians(8)))
key(idea_root,346,scale=(1,1,1),rot=(0,0,0))
# orbital red ring around idea
bpy.ops.mesh.primitive_torus_add(major_radius=1.15,minor_radius=.045,location=(C+2.25,-2.05,3.72),rotation=(math.radians(90),0,0))
ring=bpy.context.object; set_mat(ring,M['red']); key(ring,318,scale=(0,0,0)); key(ring,342,scale=(1,1,1)); key(ring,360,rot=(math.radians(90),0,math.radians(120)))

cam_pose(229,(C,-10,5.6),(C,-.8,2.8),50,True)
cam_pose(285,(C-2.8,-7.0,5.2),(C,-1.0,2.7),58)
cam_pose(330,(C+1.0,-5.2,4.3),(C+1.6,-1.7,3.1),64)
cam_pose(360,(C+2.2,-4.0,3.8),(C+2.2,-1.9,3.4),70)

# Bezier interpolation for smooth object animation
for o in scene.objects:
    linear(o)

# hard camera cuts at scene starts after smoothing
for cutfr in (1,109,229):
    if cam.animation_data and cam.animation_data.action:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                if abs(kp.co.x-cutfr)<0.1: kp.interpolation='CONSTANT'

bpy.ops.wm.save_as_mainfile(filepath='rarely_told_scene.blend')
bpy.ops.render.render(animation=True)
