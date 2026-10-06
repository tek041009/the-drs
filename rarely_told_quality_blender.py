import bpy, os, math, glob, random, subprocess
from mathutils import Vector

FPS=12
W,H=720,406
END=FPS*30
ROOT=os.getcwd()
AS=os.path.join(ROOT,"assets")

# ---------------- scene reset / render ----------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes,bpy.data.curves,bpy.data.materials,bpy.data.cameras,bpy.data.lights):
    pass

scene=bpy.context.scene
for eng in ("BLENDER_EEVEE_NEXT","BLENDER_EEVEE"):
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
scene.render.ffmpeg.ffmpeg_preset='GOOD'
scene.render.filepath='rarely_told_assets_silent.mp4'
scene.render.film_transparent=False
try:
    scene.render.use_motion_blur=True
except: pass
try:
    scene.view_settings.look='AgX - Medium High Contrast'
except:
    try: scene.view_settings.look='Medium High Contrast'
    except: pass
scene.world.color=(0.018,0.028,0.055)

# ---------------- helpers ----------------
def mat(name,color,rough=.5,metal=0.0):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    bsdf=m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=color
    bsdf.inputs['Roughness'].default_value=rough
    bsdf.inputs['Metallic'].default_value=metal
    return m

CREAM=mat('cream',(0.86,0.73,0.50,1),.65)
DARK=mat('dark',(0.035,0.05,0.07,1),.7)
ROAD=mat('road',(0.045,0.05,0.06,1),.9)
RED=mat('red',(0.55,0.025,0.02,1),.48)
PAPER=mat('paper',(0.83,0.73,0.56,1),.85)
BLACK=mat('black',(0.015,0.015,0.018,1),.55)
GOLD=mat('gold',(0.75,0.45,0.12,1),.4,0.15)
GLASS=mat('glass',(0.12,0.22,0.31,1),.25)
WOOD=mat('wood',(0.20,0.095,0.04,1),.7)

def set_mat(o,m):
    if hasattr(o.data,'materials'):
        if len(o.data.materials)==0: o.data.materials.append(m)
        else:
            for i in range(len(o.data.materials)): o.data.materials[i]=m

def cube(name,loc,scale,material,bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    set_mat(o,material)
    if bevel:
        mod=o.modifiers.new('bevel','BEVEL'); mod.width=bevel; mod.segments=2
    return o

def cyl(name,loc,r,depth,material,verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc)
    o=bpy.context.object; o.name=name; set_mat(o,material); return o

def beam(name,p1,p2,r,material):
    a,b=Vector(p1),Vector(p2); vec=b-a
    o=cyl(name,(a+b)/2,r,vec.length,material,10)
    o.rotation_mode='QUATERNION'; o.rotation_quaternion=vec.to_track_quat('Z','Y')
    return o

def text_obj(name,text,loc,size,material,extr=.012,align='CENTER'):
    c=bpy.data.curves.new(name,'FONT'); c.body=text; c.size=size; c.align_x=align; c.align_y='CENTER'
    c.extrude=extr; c.bevel_depth=.003
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o); o.location=loc
    set_mat(o,material); return o

def key(o,frame,loc=None,rot=None,scale=None):
    if loc is not None: o.location=loc; o.keyframe_insert('location',frame=frame)
    if rot is not None: o.rotation_euler=rot; o.keyframe_insert('rotation_euler',frame=frame)
    if scale is not None: o.scale=scale; o.keyframe_insert('scale',frame=frame)

def smooth(obj):
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation='BEZIER'

def import_glb(path,name,loc=(0,0,0),rot=(0,0,0),scale=1.0):
    before=set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new=[o for o in bpy.data.objects if o.name not in before]
    root=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(root)
    root.location=loc; root.rotation_euler=rot; root.scale=(scale,scale,scale)
    for o in new:
        if o.parent is None: o.parent=root
    return root,new

def bbox_world(objs):
    pts=[]
    for o in objs:
        if o.type!='MESH': continue
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    if not pts: return Vector((0,0,0)),Vector((1,1,1))
    mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return (mn+mx)/2,mx-mn

def apply_skin(meshes,skin_path):
    try: img=bpy.data.images.load(skin_path,check_existing=True)
    except: return
    m=bpy.data.materials.new("victor_skin")
    m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial'); bs=nt.nodes.new('ShaderNodeBsdfPrincipled'); tex=nt.nodes.new('ShaderNodeTexImage')
    tex.image=img; tex.interpolation='Linear'
    bs.inputs['Roughness'].default_value=.62
    nt.links.new(tex.outputs['Color'],bs.inputs['Base Color']); nt.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    for o in meshes:
        if o.type=='MESH':
            o.data.materials.clear(); o.data.materials.append(m)

def import_character(model,anim,skin,name,loc,scale=1.0,start=1,end=120):
    before=set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=model,automatic_bone_orientation=False)
    new=[o for o in bpy.data.objects if o.name not in before]
    root=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(root)
    root.location=loc; root.scale=(scale,scale,scale)
    for o in new:
        if o.parent is None: o.parent=root
    arms=[o for o in new if o.type=='ARMATURE']
    meshes=[o for o in new if o.type=='MESH']
    apply_skin(meshes,skin)
    if not arms: return root,new,None
    arm=arms[0]

    b2=set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=anim,automatic_bone_orientation=False)
    anim_objs=[o for o in bpy.data.objects if o.name not in b2]
    anim_arms=[o for o in anim_objs if o.type=='ARMATURE' and o.animation_data and o.animation_data.action]
    action=None
    if anim_arms:
        action=anim_arms[0].animation_data.action.copy()
        action.name=name+"_action"
    for o in anim_objs:
        bpy.data.objects.remove(o,do_unlink=True)
    if action:
        arm.animation_data_create()
        arm.animation_data.action=None
        tr=arm.animation_data.nla_tracks.new(); tr.name=name+"_nla"
        st=tr.strips.new(name+"_strip",start,action)
        a0,a1=action.frame_range
        st.action_frame_start=a0; st.action_frame_end=a1
        al=max(1,a1-a0)
        st.repeat=max(1,(end-start)/al)
        st.frame_end=end
    return root,new,arm

def eiffel(cx,cy,z0,scale):
    base=4.4*scale; z1=z0+4.6*scale; z2=z0+9.0*scale; z3=z0+13.0*scale; top=z0+15.5*scale
    corners=[(-base,-base),(base,-base),(base,base),(-base,base)]
    mids=[(-1.65*scale,-1.65*scale),(1.65*scale,-1.65*scale),(1.65*scale,1.65*scale),(-1.65*scale,1.65*scale)]
    tops=[(-.58*scale,-.58*scale),(.58*scale,-.58*scale),(.58*scale,.58*scale),(-.58*scale,.58*scale)]
    for a,b in zip(corners,mids): beam('leg',(cx+a[0],cy+a[1],z0),(cx+b[0],cy+b[1],z1),.12*scale,CREAM)
    for a,b in zip(mids,tops): beam('leg',(cx+a[0],cy+a[1],z1),(cx+b[0],cy+b[1],z2),.10*scale,CREAM)
    for a in tops: beam('leg',(cx+a[0],cy+a[1],z2),(cx,cy,z3),.075*scale,CREAM)
    for z,s in [(z1,2.1*scale),(z2,.72*scale),(z3,.32*scale)]:
        cube('deck',(cx,cy,z),(s,s,.09*scale),CREAM)
    for q in range(8):
        f=(q+1)/9; z=z0+(z1-z0)*f; half=(base*(1-f)+1.65*scale*f)
        beam('brace',(cx-half,cy-half,z),(cx+half,cy+half,z+.18*scale),.035*scale,CREAM)
        beam('brace',(cx-half,cy+half,z),(cx+half,cy-half,z+.18*scale),.035*scale,CREAM)
    for q in range(5):
        f=(q+1)/6; z=z1+(z2-z1)*f; half=(1.65*scale*(1-f)+.58*scale*f)
        beam('brace',(cx-half,cy-half,z),(cx+half,cy+half,z+.14*scale),.025*scale,CREAM)
        beam('brace',(cx-half,cy+half,z),(cx+half,cy-half,z+.14*scale),.025*scale,CREAM)
    beam('spire',(cx,cy,z3),(cx,cy,top),.055*scale,CREAM)

def light_area(name,loc,energy,size,color=(1,1,1)):
    data=bpy.data.lights.new(name,'AREA'); data.energy=energy; data.shape='DISK'; data.size=size; data.color=color
    o=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(o); o.location=loc; return o

def look_at(o,target):
    direction=Vector(target)-o.location
    o.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()

def cam_key(cam,frame,loc,target,lens):
    cam.location=loc; look_at(cam,target); cam.data.lens=lens
    cam.keyframe_insert('location',frame=frame); cam.keyframe_insert('rotation_euler',frame=frame); cam.data.keyframe_insert('lens',frame=frame)

# camera + focus
bpy.ops.object.camera_add()
cam=bpy.context.object; scene.camera=cam
cam.data.lens=48
cam.data.dof.use_dof=True; cam.data.dof.aperture_fstop=2.2
focus=bpy.data.objects.new('focus',None); bpy.context.collection.objects.link(focus)
cam.data.dof.focus_object=focus

# global light
sun_data=bpy.data.lights.new('sun','SUN'); sun_data.energy=1.8; sun_data.angle=.18; sun_data.color=(1.0,.63,.37)
sun=bpy.data.objects.new('sun',sun_data); bpy.context.collection.objects.link(sun); sun.rotation_euler=(math.radians(38),math.radians(-18),math.radians(135))

# Asset paths
CHAR=os.path.join(AS,'kenney-animated-characters-protagonists/3D/characters')
MODEL=os.path.join(CHAR,'Model/characterMedium.fbx')
RUN=os.path.join(CHAR,'Animations/run.fbx')
IDLE=os.path.join(CHAR,'Animations/idle.fbx')
SKIN=os.path.join(CHAR,'Skins/criminalMaleA.png')
COMM=os.path.join(AS,'kenney-city-kit-commercial/3D/city/Models/GLB format')
ROADS=os.path.join(AS,'kenney-city-kit-roads/3D/city/Models/GLB format')
FURN=os.path.join(AS,'kenney-furniture-kit/3D/interior-furniture/Models/GLTF format')
CARS=glob.glob(os.path.join(AS,'kenney-car-kit/**/**.glb'),recursive=True)

# ---------------- Scene A: Paris reveal (frames 1-84) ----------------
X0=0
# ground/road
for iy in range(-3,5):
    rp=os.path.join(ROADS,'road-straight.glb')
    if os.path.exists(rp):
        r,_=import_glb(rp,f'road{iy}',(0,iy*4.0,0),scale=1.0)
    else: cube('road',(0,iy*4,0),(4,2,.05),ROAD)

building_files=[os.path.join(COMM,f'building-{c}.glb') for c in "abcdefghij"]
for side in (-1,1):
    for i,y in enumerate(range(-12,22,5)):
        fp=building_files[(i+(0 if side<0 else 4))%len(building_files)]
        if os.path.exists(fp):
            root,objs=import_glb(fp,f'bld{side}_{i}',(side*6.2,y,0),rot=(0,0,math.radians(90 if side<0 else -90)),scale=1.0)
            root.scale=(1.4,1.4,1.4)
# lamps
lampfile=os.path.join(ROADS,'light-curved.glb')
if os.path.exists(lampfile):
    for side in (-1,1):
        for i,y in enumerate(range(-10,20,5)):
            rr,_=import_glb(lampfile,f'lamp{side}_{i}',(side*3.7,y,0),rot=(0,0,math.radians(180 if side>0 else 0)),scale=.9)

eiffel(0,16,0,.78)
# taxi/car moving through foreground (procedural)
car=cube('taxi',(2,-9,.55),(1.25,2.2,.55),GOLD,.25)
for x in (-.85,.85):
    for y in (-1.35,1.35):
        w=cyl('wheel',(2+x,-9+y,.28),.30,.25,BLACK,16); w.rotation_euler=(0,math.radians(90),0)
key(car,1,loc=(2,-10,.55)); key(car,84,loc=(2,14,.55))
# title integrated
title=text_obj('title','PARIS  ·  1925',(-4.7,14.6,6.2),.7,CREAM,.018,'LEFT')
title.rotation_euler=(math.radians(90),0,0)
tag=cube('soldtag',(1.9,15.1,7.0),(2.1,.10,.85),RED,.12)
tag.rotation_euler=(math.radians(90),0,math.radians(-8))
sold=text_obj('sold','SOLD',(1.9,14.87,7.0),.86,CREAM,.025)
sold.rotation_euler=(math.radians(90),0,math.radians(-8))
key(tag,1,scale=(0,0,0)); key(sold,1,scale=(0,0,0))
key(tag,44,scale=(0,0,0)); key(sold,44,scale=(0,0,0))
key(tag,56,scale=(1.15,1.15,1.15)); key(sold,56,scale=(1.15,1.15,1.15))
key(tag,62,scale=(1,1,1)); key(sold,62,scale=(1,1,1))
# money burst
for j in range(10):
    n=cube(f'note{j}',(0,0,0),(.42,.03,.22),PAPER,.02)
    ang=2*math.pi*j/10
    key(n,52,loc=(0,15,7),scale=(0,0,0))
    key(n,64,loc=(math.cos(ang)*2.0,15+math.sin(ang)*1.0,6.8+math.sin(ang*2)*.7),rot=(0,ang,ang),scale=(1,1,1))
    key(n,84,loc=(math.cos(ang)*5.5,15+math.sin(ang)*3.5,3.2+math.sin(ang*2)*1.4),rot=(ang*1.5,ang*2,ang*2.6),scale=(.7,.7,.7))
# lighting
keya=light_area('paris_key',(-5,-6,12),1400,8,(1.0,.55,.32)); look_at(keya,(0,10,4))
fill=light_area('paris_fill',(7,4,8),800,10,(.38,.58,1.0)); look_at(fill,(0,10,4))

cam_key(cam,1,(0,-17,5.1),(0,13,5.0),42)
cam_key(cam,44,(-2.2,-7.5,6.2),(0,15,6.6),52)
cam_key(cam,84,(3.2,-3.2,7.8),(0,15.5,7.2),61)
key(focus,1,loc=(0,13,5)); key(focus,84,loc=(0,15,7))

# ---------------- Scene B: Victor walking (85-204) ----------------
X1=70
# avenue
cube('walk_ground',(X1,0,-.08),(16,18,.08),ROAD)
for side in (-1,1):
    for i,y in enumerate(range(-14,17,5)):
        fp=building_files[(i+(3 if side<0 else 7))%len(building_files)]
        if os.path.exists(fp):
            rt,_=import_glb(fp,f'walkb{side}_{i}',(X1+side*7.2,y,0),rot=(0,0,math.radians(90 if side<0 else -90)),scale=1.2)
# character
victor,objs,arm=import_character(MODEL,RUN,SKIN,'VictorWalk',(X1,-12,0),1.15,85,204)
key(victor,85,loc=(X1,-12,0)); key(victor,204,loc=(X1,10,0))
# add overcoat silhouette by a parented dark outer mesh around torso? simple coat prop
coat=cube('overcoat',(0,0,0),(.46,.25,.86),DARK,.10)
coat.parent=victor; coat.location=(0,0,1.2)
# newspaper loose paper blow
for j in range(4):
    p=cube(f'paperfly{j}',(X1-5+j*3,-4+j*2,2.5),(.56,.02,.34),PAPER,.02)
    key(p,100+j*8,loc=(X1-5+j*3,-4+j*2,2.5),rot=(.2,j,.4))
    key(p,150+j*7,loc=(X1+2+j*.7,1+j*2,3.6+j*.2),rot=(2.0,3.2+j,2.8))
    key(p,195,loc=(X1+7+j,8+j,1.4),rot=(4.0,5.8,6.4))
# warm shop lights
for side in (-1,1):
    for y in (-7,1,9):
        la=light_area(f'shop{side}{y}',(X1+side*5.8,y,3.2),450,3,(1.0,.43,.20)); look_at(la,(X1,y,1.8))
# label
lab=text_obj('victor_name','VICTOR LUSTIG',(X1-4.2,6.0,5.7),.72,CREAM,.018,'LEFT')
lab.rotation_euler=(math.radians(90),0,0)
sub=text_obj('victor_sub','CAREER CON MAN',(X1-4.2,5.98,4.85),.32,RED,.012,'LEFT')
sub.rotation_euler=(math.radians(90),0,0)

cam_key(cam,84,(3.2,-3.2,7.8),(0,15.5,7.2),61)
cam_key(cam,85,(X1-8.0,-13.4,3.2),(X1,-7,1.8),47)
cam_key(cam,145,(X1-5.4,-3.2,2.8),(X1,1.0,1.8),59)
cam_key(cam,204,(X1-2.0,9.5,2.7),(X1,8.2,1.8),72)
key(focus,85,loc=(X1,-7,1.8)); key(focus,204,loc=(X1,8,1.8))

# ---------------- Scene C: café / newspaper (205-360) ----------------
X2=140
# room shell
cube('cafefloor',(X2,0,0),(9,8,.10),WOOD)
cube('cafeback',(X2,7.5,4.0),(9,.12,4),DARK)
cube('cafeside',(X2-8.8,0,4.0),(.12,8,4),DARK)
# window
win=cube('window',(X2,7.33,4.4),(4.4,.04,2.7),GLASS,.02)
# simple external skyline visible through window
for i in range(7):
    cube('skyline',(X2-5+i*1.7,7.65,1.7+(i%3)*.45),(.75,.4,1.7+(i%3)*.45),DARK,.03)
eiffel(X2+4.4,8.2,.1,.22)
# furniture real assets
for fname,loc,rot,sc in [
    ('desk.glb',(X2,0,0),(0,0,0),1.35),
    ('chairDesk.glb',(X2,2.3,0),(0,0,math.pi),1.35),
    ('lampRoundTable.glb',(X2-2.4,-.3,1.8),(0,0,0),1.2),
]:
    fp=os.path.join(FURN,fname)
    if os.path.exists(fp): import_glb(fp,'f_'+fname,loc,rot,sc)
# seated-ish character; lower body hidden by desk
vic2,objs2,arm2=import_character(MODEL,IDLE,SKIN,'VictorCafe',(X2,2.2,0),1.12,205,360)
vic2.rotation_euler=(0,0,math.pi)
# table props
cup=cyl('cup',(X2+2.4,-.55,2.15),.28,.62,CREAM,20)
handle=cyl('handle',(X2+2.75,-.55,2.15),.11,.08,CREAM,16); handle.rotation_euler=(math.radians(90),0,0)
# newspaper pages
pageL=cube('pageL',(X2-.85,-.15,2.25),(1.55,.025,1.05),PAPER,.025)
pageR=cube('pageR',(X2+.85,-.15,2.25),(1.55,.025,1.05),PAPER,.025)
pageL.rotation_euler=(math.radians(90),0,math.radians(70))
pageR.rotation_euler=(math.radians(90),0,math.radians(-70))
key(pageL,205,rot=(math.radians(90),0,math.radians(70)),scale=(.15,.15,.15))
key(pageR,205,rot=(math.radians(90),0,math.radians(-70)),scale=(.15,.15,.15))
key(pageL,232,rot=(math.radians(90),0,math.radians(70)),scale=(1,1,1))
key(pageR,232,rot=(math.radians(90),0,math.radians(-70)),scale=(1,1,1))
key(pageL,252,rot=(math.radians(90),0,math.radians(3)))
key(pageR,252,rot=(math.radians(90),0,math.radians(-3)))
# headline lies just above paper facing camera-ish
h1=text_obj('headline1','EIFFEL TOWER',(X2-.1,-1.21,2.64),.34,BLACK,.006)
h2=text_obj('headline2','COSTS KEEP RISING',(X2-.1,-1.22,2.22),.31,RED,.006)
for h in (h1,h2):
    h.rotation_euler=(math.radians(90),0,0)
    key(h,205,scale=(0,0,0)); key(h,255,scale=(0,0,0)); key(h,268,scale=(1,1,1))
# article bars rise
for j,h in enumerate((.25,.45,.72,.98,1.25)):
    bar=cube(f'costbar{j}',(X2-2.0+j*.55,-1.18,2.0+h/2),(.16,.025,h/2),RED,.02)
    key(bar,270+j*3,scale=(1,1,0)); key(bar,285+j*3,scale=(1,1,1))
# idea tower rises from paper
idea_root=bpy.data.objects.new('idea_root',None); bpy.context.collection.objects.link(idea_root); idea_root.location=(X2+2.4,-1.05,2.35)
for sx in (-1,1):
    q1=beam('idea_leg',(X2+2.4+sx*.45,-1.05,2.35),(X2+2.4+sx*.16,-1.05,3.65),.05,RED); q1.parent=idea_root
beam('idea_cross',(X2+2.08,-1.05,3.0),(X2+2.72,-1.05,3.0),.035,RED).parent=idea_root
beam('idea_spire',(X2+2.4,-1.05,3.65),(X2+2.4,-1.05,4.4),.04,RED).parent=idea_root
key(idea_root,295,scale=(0,0,0)); key(idea_root,326,scale=(1.22,1.22,1.22)); key(idea_root,338,scale=(1,1,1))
# thought rings
for r in (1.1,1.6):
    bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=.025,location=(X2+2.4,-1.05,3.25),rotation=(math.radians(90),0,0))
    ring=bpy.context.object; set_mat(ring,RED); key(ring,308,scale=(0,0,0)); key(ring,338,scale=(1,1,1))
# café lighting
k1=light_area('cafe_key',(X2-3,-4,7),1300,6,(1.0,.50,.25)); look_at(k1,(X2,0,2.4))
k2=light_area('window_blue',(X2+3,6.5,5),900,5,(.28,.48,1.0)); look_at(k2,(X2,0,2.5))

cam_key(cam,204,(X1-2.0,9.5,2.7),(X1,8.2,1.8),72)
cam_key(cam,205,(X2,-8.4,4.4),(X2,0,2.6),47)
cam_key(cam,265,(X2-2.8,-5.4,3.6),(X2-.3,-.1,2.5),60)
cam_key(cam,315,(X2+1.1,-3.5,3.2),(X2+.9,-.5,2.8),73)
cam_key(cam,360,(X2+2.1,-2.7,3.3),(X2+2.2,-.8,3.1),83)
key(focus,205,loc=(X2,0,2.5)); key(focus,270,loc=(X2,-.15,2.5)); key(focus,360,loc=(X2+2.2,-.8,3.1))

# camera interpolation smooth except hard cuts
for o in scene.objects:
    smooth(o)
for cut in (85,205):
    for fc in cam.animation_data.action.fcurves:
        # enforce near-instant jump from preceding shot
        for kp in fc.keyframe_points:
            if abs(kp.co.x-cut)<.1: kp.interpolation='CONSTANT'

# volumetric haze as huge cube using principled volume
volmat=bpy.data.materials.new('haze'); volmat.use_nodes=True
nt=volmat.node_tree; nt.nodes.clear(); out=nt.nodes.new('ShaderNodeOutputMaterial'); pv=nt.nodes.new('ShaderNodeVolumePrincipled')
pv.inputs['Density'].default_value=.008; pv.inputs['Color'].default_value=(.35,.43,.55,1)
nt.links.new(pv.outputs['Volume'],out.inputs['Volume'])
# volumetric box disabled on CPU prototype; lighting/fog retained via grade

bpy.ops.wm.save_as_mainfile(filepath='rarely_told_assets.blend')
bpy.ops.render.render(animation=True)
