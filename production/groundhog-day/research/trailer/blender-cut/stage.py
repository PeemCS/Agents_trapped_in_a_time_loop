"""Miniature stage tools. Inputs use screen-friendly right, up, forward coordinates."""
import bpy
import math
from mathutils import Vector, Euler, Matrix
from pathlib import Path
from functools import lru_cache

HERE = Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
active = None
basis = Matrix(((1,0,0),(0,0,-1),(0,1,0)))
def vec(p):
    return basis @ Vector(p)
def rotate(obj, angles):
    obj.rotation_euler = (basis @ Euler(angles, 'XYZ').to_matrix() @ basis.transposed()).to_euler()
    return obj
def attach(name, data, pos, parent):
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = active if parent is None else parent
    obj.location = vec(pos)
    return obj
def group(name, pos=(0,0,0), parent=None):
    return attach(name,None,pos,parent)
def setroot(name):
    global active
    active = None
    active = group(name)
    return active

@lru_cache(None)
def material(color):
    hexc = color.strip('#')
    if len(hexc)==3: hexc=''.join(ch*2 for ch in hexc)
    rgb = [int(hexc[i:i+2],16)/255 for i in (0,2,4)]
    rgba = [v/12.92 if v<=0.04045 else ((v+.055)/1.055)**2.4 for v in rgb]+[1]
    m=bpy.data.materials.new('#'+hexc)
    m.diffuse_color=rgba
    m.use_nodes=True
    shader=m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=rgba
    shader.inputs['Roughness'].default_value=.76
    return m
@lru_cache(None)
def cube_mesh(sz,color,bevel):
    x,y,z = (v/2 for v in sz)
    vs=[(a,b,c) for c in (-y,y) for b in (-z,z) for a in (-x,x)]
    mesh=bpy.data.meshes.new('carved block')
    mesh.from_pydata(vs,[],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)])
    mesh.materials.append(material(color))
    if bevel:
        import bmesh
        bm=bmesh.new(); bm.from_mesh(mesh); bm.normal_update()
        bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(bevel,min(sz)*.46),segments=3,profile=.5,affect='EDGES')
        bm.to_mesh(mesh); bm.free()
    mesh.update()
    return mesh
def box(name,pos,size,color,bevel=0,parent=None):
    return attach(name,cube_mesh(tuple(size),color,bevel),pos,parent)

@lru_cache(None)
def sphere_mesh(color):
    import bmesh
    bm=bmesh.new()
    bmesh.ops.create_uvsphere(bm,u_segments=16,v_segments=12,radius=.5)
    mesh=bpy.data.meshes.new('turned clay'); bm.to_mesh(mesh); bm.free()
    for poly in mesh.polygons: poly.use_smooth=True
    mesh.materials.append(material(color))
    return mesh
def ball(name,pos,size,color,parent=None):
    o=attach(name,sphere_mesh(color),pos,parent); o.scale=(size[0],size[2],size[1]); return o
@lru_cache(None)
def cylinder_mesh(color):
    import bmesh
    bm=bmesh.new()
    bmesh.ops.create_cone(bm,cap_ends=True,cap_tris=False,segments=16,radius1=1,radius2=1,depth=1)
    mesh=bpy.data.meshes.new('turned dowel'); bm.to_mesh(mesh); bm.free()
    for f in mesh.polygons: f.use_smooth=len(f.vertices)==4
    mesh.materials.append(material(color)); return mesh
def rod(name,a,b,r,color,parent=None):
    aa,bb=Vector(a),Vector(b)
    o=attach(name,cylinder_mesh(color),tuple((aa+bb)*.5),parent)
    d=vec(bb-aa); o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    o.scale=(r,r,max(.001,d.length)); return o
def label(name,txt,pos,size,color,parent=None):
    font=bpy.data.curves.new(name,'FONT'); font.body=txt; font.size=size
    font.align_x='CENTER'; font.align_y='CENTER'; font.extrude=.0006
    font.resolution_u=4
    font.materials.append(material(color))
    obj=attach(name,font,pos,parent); obj.rotation_euler.x=math.pi/2
    return obj

def hand(name,pos,side='R',parent=None):
    p=group(name,pos,parent)
    skin='#d19a78'
    ball(name+'.palm',(0,-.035,0),(.100,.122,.057),skin,p)
    sign=1 if side=='R' else -1
    for i,length in enumerate((.058,.073,.078,.065)):
        x=sign*(i-1.5)*.023
        finger=ball(name+'.finger'+str(i),(x,-.081-length*.37,.009),(.026,length,.032),skin,p)
        finger.rotation_euler.y=(i-1.5)*.052*sign
    thumb=ball(name+'.thumb',(sign*.051,-.045,.018),(.04,.076,.042),skin,p)
    thumb.rotation_euler.y=sign*.47
    return p
def profile(name,rings,color,parent,segments=24):
    """Lathe a character part around elliptical horizontal sections."""
    verts=[];faces=[]
    for h,rx,rz,cz in rings:
        for j in range(segments):
            a=2*math.pi*j/segments
            verts.append(tuple(vec((rx*math.cos(a),h,cz+rz*math.sin(a)))))
    for i in range(len(rings)-1):
        for j in range(segments):
            a=i*segments+j; b=i*segments+(j+1)%segments
            faces.append((a,a+segments,b+segments,b))
    faces.append(tuple(range(segments)))
    faces.append(tuple(range(len(verts)-1,len(verts)-segments-1,-1)))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces);mesh.materials.append(material(color));mesh.update()
    for f in list(mesh.polygons)[:-2]: f.use_smooth=True
    return attach(name,mesh,(0,0,0),parent)

def panel(name,points,color,parent):
    mesh=bpy.data.meshes.new(name); mesh.from_pydata([tuple(vec(p)) for p in points],[],[tuple(range(len(points)))])
    mesh.materials.append(material(color));return attach(name,mesh,(0,0,0),parent)

def actor(name,pos,style='phil',pose='stand',parent=None):
    palette={'phil':('#343d48','#594738','#793d34','#e0ac89'),'rita':('#3d6958','#51352c','#e5d7b3','#c18b6a'),'ned':('#856747','#673d26','#567563','#dcad88'),'larry':('#435e61','#4c3a35','#bc8e55','#aa7659')}
    coat,hair,scarf,skin=palette.get(style,palette['phil'])
    A=group(name,pos,parent)
    seated=pose=='sit'
    hip=.54 if seated else .89
    def B(n,p,d,c,par=A): return ball(name+n,p,d,c,par)
    def G(n,p,par=A): return group(name+n,p,par)
    hem=hip-(.06 if seated else .21)
    profile(name+'.overcoat',[(hem,.244,.159,.003),(hem+.018,.249,.163,.003),
        (hip+.035,.225,.163,.006),(hip+.15,.207,.148,.008),(hip+.31,.232,.155,0),
        (hip+.414,.252,.146,-.004),(hip+.456,.211,.125,0),(hip+.495,.088,.081,0)],coat,A)
    trim={'phil':'#44505b','ned':'#9d7d54','rita':'#4d7c68','larry':'#577376'}.get(style,coat)
    for sign in (-1,1):
        panel(name+'.lapel'+str(sign),[(sign*.093,hip+.493,.058),(sign*.188,hip+.427,.103),
              (sign*.125,hip+.367,.137),(sign*.154,hip+.357,.135),(sign*.036,hip+.215,.154)],trim,A)
        rod(name+'.welt'+str(sign),(sign*.115,hip+.038,.145),(sign*.195,hip+.088,.095),.009,trim,A)
    rod(name+'.placket',(-.03,hem+.02,.163),(-.03,hip+.29,.157),.004,trim,A)
    B('.collar',(0,hip+.49,0),(.273,.105,.212),scarf)
    panel(name+'.scarf',[(.024,hip+.51,.100),(.112,hip+.48,.102),(.077,hip+.30,.155),(.006,hip+.319,.156)],scarf,A)
    for i in range(4):
        y=hip+.25-i*.095
        if y>hem:B('.button'+str(i),(-.047,y,.155),(.023,.023,.013),'#302d28',A)
    B('.neck',(0,hip+.55,0),(.13,.15,.13),skin)
    H=G('.head',(0,hip+.70,0))
    profile(name+'.face',[(-.17,.046,.055,.014),(-.15,.088,.091,.016),(-.105,.116,.111,.013),
        (-.035,.141,.134,0),(.045,.146,.135,0),(.111,.137,.126,-.002),
        (.16,.104,.097,-.003),(.18,.053,.042,-.01)],skin,H)
    B('.hair',(0,.118,-.022),(.309,.193,.272),hair,H)
    B('.side part',(-.092,.09,.068),(.14,.13,.112),hair,H)
    B('.nose',(0,-.014,.139),(.055,.097,.065),skin,H)
    B('.nose tip',(0,-.041,.158),(.064,.044,.049),skin,H)
    strand={'phil':'#67513f','ned':'#765037','rita':'#604133','larry':'#60483b'}.get(style,hair)
    for i in range(7):
        x=-.114+.034*i
        tuft=B('.fringe'+str(i),(x,.117+.014*math.cos(i*.65),.099-.038*(abs(x)/.114)**1.9),
               (.049,.084,.045),strand if i%3==0 else hair,H)
        rotate(tuft,(.20,-.28,.48 if style!='rita' else -.39))
    B('.mouth',(.002,-.096,.111),(.067,.011,.012),'#995e53',H)
    for side,sign in [('L',1),('R',-1)]:
        x=sign*.059
        B('.ear'+side,(sign*.142,-.013,0),(.051,.086,.043),skin,H)
        B('.eye'+side,(x,.013,.116),(.041,.021,.018),'#ede2d0',H)
        B('.iris'+side,(x,.013,.125),(.016,.019,.008),'#383431',H)
        B('.brow'+side,(x,.057,.118),(.068,.015,.021),hair,H)
        if style=='rita':
            for i in range(3):
                B('.curl'+side+str(i),(sign*(.13+.006*i),.075-i*.056,-.009-i*.014),(.077,.105,.099),strand if i==1 else hair,H)
        if style=='ned':
            box(name+'.lens top'+side,(x,.043,.141),(.097,.011,.012),'#493b32',.003,H)
            for t in (-1,1): box(name+'.rim'+side+str(t),(x+t*.046,.012,.14),(.009,.056,.009),'#493b32',.002,H)
            box(name+'.lens base'+side,(x,-.016,.141),(.09,.008,.009),'#493b32',.002,H)
        arm=G('.arm'+side,(sign*.228,hip+.421,0))
        B('.sleeve'+side,(sign*.014,-.13,0),(.145,.307,.153),coat,arm)
        fore=G('.fore'+side,(sign*.021,-.263,0),arm)
        B('.cuff'+side,(0,-.118,.008),(.126,.27,.144),coat,fore)
        hand(name+'.hand'+side,(0,-.244,.01),side,fore)
        leg=G('.leg'+side,(sign*.12,hip-.025,0))
        knee=(0,-.05,.34) if seated else (0,-.38,0)
        rod(name+'.trouser'+side,(0,0,0),knee,.089,'#38404a',leg)
        B('.knee'+side,knee,(.18,.17,.18),'#38404a',leg)
        ankle=(0,-hip+.121,.34 if seated else .012)
        rod(name+'.shin'+side,knee,ankle,.077,'#38404a',leg)
        B('.shoe'+side,(0,-hip+.086,ankle[2]+.052),(.170,.122,.273),'#463a31',leg)
        box(name+'.sole'+side,(0,-hip+.044,ankle[2]+.051),(.154,.021,.24),'#302c2b',.009,leg)
    if style=='rita':
        B('.back hair',(0,.03,-.094),(.329,.36,.18),hair,H)
        B('.bun',(.04,.12,-.16),(.171,.17,.159),hair,H)
    if style=='ned':
        B('.hat brim',(0,.158,0),(.403,.035,.34),'#61513f',H)
        B('.hat crown',(0,.196,-.005),(.283,.135,.237),'#72614b',H)
    return A

def finish(name):
    # Flatten text to geometry so every renderer sees the same lettering.
    for obj in list(bpy.context.scene.objects):
        if obj.type=='FONT':
            st=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh=bpy.data.meshes.new_from_object(st)
            holder=bpy.data.objects.new(obj.name+' converted',mesh)
            bpy.context.collection.objects.link(holder); holder.parent=obj.parent
            holder.matrix_basis=obj.matrix_basis.copy(); old=obj.name
            bpy.data.objects.remove(obj,do_unlink=True); holder.name=old
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(name+'.blend')))
    bpy.ops.export_scene.gltf(filepath=str(HERE/(name+'.glb')),export_format='GLB',export_yup=True,export_cameras=False,export_lights=False,export_animations=False)

    # The standalone bpy wheel can crash in native destructor order after a successful export.
    # Running inside the Blender application should return control to the user normally.
    import os, sys
    if not bpy.app.binary_path and Path(sys.argv[0]).stem == name:
        sys.stdout.flush();sys.stderr.flush();os._exit(0)
