"""Assemble the three local production files into an editable Blender set library.

Run with Blender's bpy Python, or with Blender --background --python this_file.py.
Use --output <path> or --previews <directory> for a separate build or camera proofs.
The Three.js shot animation remains in the unit .js files.
"""
import argparse
from math import radians, tan
import os
from pathlib import Path
import sys

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SETS = {
    # (display name, unit, eye, aim, vertical FOV, key-light position, fill-light position)
    'street': ('01  Main Street', 'exteriors', (-8.6,4.0,13.4), (.1,3.52,-.6), 44, (-7,10,5), (4,7,8)),
    'bedroom': ('02  Hearthside Bedroom', 'hotel', (-2.34,2.04,2.16), (.10,1.13,-.59), 54, (1.49,2.71,.74), (-1.34,2.49,-1.56)),
    'ballroom': ('03  Ballroom Piano', 'music', (2.59,1.75,.73), (-.33,1.20,-2.15), 42, (2.0,3.15,-.31), (-2.35,2.90,-.74)),
    'depot': ('04  Town Coach Depot', 'exteriors', (-5.20,1.90,2.84), (1.20,1.38,-2.14), 46, (1.91,2.89,1.6), (-3.0,2.47,-1.21)),
    'coach': ('05  Allegheny Coach', 'exteriors', (-7.06,1.90,6.60), (-1.25,1.35,1.01), 43, (-6.6,6.3,5.6), (4.1,5.5,5.1)),
    'phone': ('06  Pittsburgh Terminal', 'exteriors', (-1.41,1.76,2.17), (-.26,1.56,.02), 43, (-.76,2.91,1.29), (1.23,2.34,1.61)),
    'lobby': ('07  Hearthside Lobby', 'hotel', (-2.72,1.91,2.48), (1.52,1.33,-.83), 53, (-1.38,2.89,.28), (1.96,2.99,1.22)),
    'booth': ('08  Rialto Projection and Regional Wire', 'music', (-1.60,1.79,1.61), (-.27,1.47,-1.08), 48, (-1.64,2.71,.64), (1.58,2.28,-.21)),
}

CAST = {
    'StreetRita','StreetLarry','StreetPhil','StreetNed','BedPhil','ShoePhil',
    'LobbyNed','LobbyRita','LobbyLarry','BallRita','BallPhil','BallRitaSeated',
    'BoothLarry','BoothRita','StationRita',
}
INSERTS = {
    'ExtPolicy','ExtBallpoint','ExtReceipt','ExtCarbon','ExtWatch','ExtWatchFinger',
    'ExtWarmWindows','ExtLap','ExtReceiver','ExtPhoneRest','ExtRailHand','ExtWheelHand',
    'BedHandL','BedHandR','ReachClock','CurtainHandL','CurtainHandR','PocketInsert',
    'PocketHand','ReachClockBridge','CurtainHandLBridge','CurtainHandRBridge',
    'FareLeft','FareRight','PaidTicket','LobbyGreetingHand','RitaBoard',
    'BlueCarbon','CarbonOriginal','FareCash','LarryCase',
    'PianoHandL','PianoHandR','LarryCassette','WireHand',
}

def point(xyz):
    x,y,z=xyz
    return Vector((x,-z,y))

def aim(obj, target):
    obj.rotation_euler=(point(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def collection(scene,name,hidden=False):
    col=bpy.data.collections.new(name)
    scene.collection.children.link(col)
    col.hide_viewport=hidden
    col.hide_render=hidden
    return col

def camera(col,name,eye,target,fovy):
    data=bpy.data.cameras.new(name)
    data.sensor_fit='HORIZONTAL'
    data.lens=data.sensor_width/(2*(16/9)*tan(radians(fovy)/2))
    data.clip_start=.022
    data.clip_end=320
    data.passepartout_alpha=.90
    data.display_size=.22
    obj=bpy.data.objects.new(name,data)
    col.objects.link(obj)
    obj.location=point(eye)
    aim(obj,target)
    return obj

def area(col,name,position,target,power,size,tint):
    data=bpy.data.lights.new(name,'AREA')
    data.shape='DISK'
    data.energy=power
    data.size=size
    data.color=tint
    obj=bpy.data.objects.new(name,data)
    col.objects.link(obj)
    obj.location=point(position)
    aim(obj,target)

def shelve_receiver(root, source, col):
    """The receiver is part of the hand insert. Give the idle phone a handset."""
    if source is None: return
    model=bpy.data.objects.new('Payphone receiver on cradle',None)
    col.objects.link(model)
    model.parent=root
    model.location=point((-.101,1.495,.338))
    keep={'2c3636','273231','263030','38413e','39413d'}
    for obj in source.children:
        if obj.type!='MESH':continue
        if not any(m and m.name.lower().lstrip('#').split('.')[0] in keep for m in obj.data.materials):continue
        duplicate=obj.copy()
        duplicate.name='Cradled receiver '+obj.name.split()[-1]
        duplicate.parent=model
        col.objects.link(duplicate)

def configure(scene,key,objects,original_names):
    title,unit,eye,target,fovy,key_pos,fill_pos=SETS[key]
    scene.name=title
    short=title.split('  ',1)[1]
    scene.render.engine='CYCLES'
    scene.cycles.samples=24
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.render.fps=24
    scene.frame_start=1
    scene.frame_end=1
    scene.unit_settings.system='METRIC'
    scene.world=bpy.data.worlds.new(short+'  |  ambient')
    scene.world.use_nodes=True
    exterior=key in ('street','coach')
    bg=scene.world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value=(.54,.68,.79,1) if exterior else (.56,.57,.55,1)
    bg.inputs['Strength'].default_value=.63 if exterior else .27
    scene.view_settings.view_transform='AgX'
    scene.view_settings.exposure=-.65 if key in ('street','coach','phone') else -.08
    set_col=collection(scene,short+'  |  Set and furnishings')
    cast_col=collection(scene,short+'  |  Cast',True)
    alt_col=collection(scene,short+'  |  Shot inserts',True)
    rig_col=collection(scene,short+'  |  Cameras and lighting')
    root=objects[key]
    source_nodes=[root,*root.children_recursive]
    for obj in source_nodes:
        p=obj
        target_col=set_col
        while p:
            name=original_names.get(p,p.name)
            if name in CAST:
                target_col=cast_col
                break
            if name in INSERTS:
                target_col=alt_col
                break
            p=p.parent
        target_col.objects.link(obj)
        if obj.type=='EMPTY':
            obj.empty_display_size=.10
    if key=='phone':
        shelve_receiver(root,objects.get('ExtReceiver'),set_col)
    if not len(cast_col.objects):
        bpy.data.collections.remove(cast_col)
    if not len(alt_col.objects):
        bpy.data.collections.remove(alt_col)
    scene.camera=camera(rig_col,short+'  |  Set camera',eye,target,fovy)
    if exterior:
        area(rig_col,short+'  |  Winter sun',key_pos,target,3200,7.5,(1,.87,.73))
        area(rig_col,short+'  |  Skylight',fill_pos,target,1400,8,(.72,.85,1))
    else:
        area(rig_col,short+'  |  Key',key_pos,target,120 if key=='phone' else 220,1.65,(1,.88,.73))
        area(rig_col,short+'  |  Fill',fill_pos,target,65 if key=='phone' else 125,1.9,(.72,.85,1))
    if key=='booth':
        camera(rig_col,'Regional wire  |  Console camera',(10.41,1.81,1.46),(12.03,1.19,-1.09),44)
        area(rig_col,'Regional wire  |  Desk softbox',(11.27,2.63,.61),(12.1,1.21,-.99),245,1.55,(1,.89,.76))
    scene['Source file']=unit+'.blend'
    scene['Source root']=key
    scene['Shot animation']=unit+'.js'
    scene['Set objects']=len(source_nodes)
    # Solid-mode workbench mirrors the material colours even without a renderer.
    scene.display.shading.color_type='MATERIAL'
    scene.display.shading.light='STUDIO'
    scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type='WORLD'

def open_camera_views(first):
    for win in bpy.context.window_manager.windows:
        win.scene=first
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type!='VIEW_3D':continue
            space=area.spaces.active
            space.use_local_camera=False
            space.shading.type='SOLID'
            space.shading.color_type='MATERIAL'
            space.shading.light='STUDIO'
            space.shading.show_shadows=True
            space.shading.show_cavity=True
            space.shading.cavity_type='WORLD'
            space.shading.cavity_ridge_factor=.8
            space.shading.cavity_valley_factor=.7
            space.overlay.show_extras=False
            space.overlay.show_floor=False
            space.overlay.show_axis_x=False
            space.overlay.show_axis_y=False
            space.overlay.show_cursor=False
            space.overlay.show_relationship_lines=False
            space.region_3d.view_perspective='CAMERA'
            space.region_3d.view_camera_zoom=4

def verify(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    assert {s.name for s in bpy.data.scenes}=={spec[0] for spec in SETS.values()}
    assert all(s.camera and s.camera.type=='CAMERA' and s.camera in set(s.objects) for s in bpy.data.scenes)
    assert all(len([o for o in s.objects if o.type=='LIGHT'])>=2 for s in bpy.data.scenes)
    assert all(s['Source root'] in s.objects for s in bpy.data.scenes)
    assert not bpy.data.libraries, 'The library must work without its source files.'
    print('Verified eight self-contained sets and eight active cameras.',flush=True)

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output',type=Path,default=HERE/'Play-It-Again-sets.blend')
    cli.add_argument('--previews',type=Path)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ([] if bpy.app.binary_path else sys.argv[1:])
    args=cli.parse_args(argv)
    target=args.output.expanduser().resolve()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    first=bpy.context.scene
    files={}
    for unit in ('exteriors','hotel','music'):
        with bpy.data.libraries.load(str(HERE/(unit+'.blend')),link=False) as (src,dst):
            names=tuple(src.objects)
            dst.objects=list(names)
        objects=dict(zip(names,dst.objects))
        files[unit]=(objects,{obj:name for name,obj in objects.items() if obj})
    for i,(root,(name,unit,*_)) in enumerate(SETS.items()):
        scene=first if i==0 else bpy.data.scenes.new(name)
        configure(scene,root,*files[unit])
    open_camera_views(first)
    bpy.context.preferences.filepaths.save_version=0
    target.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
    verify(target)
    if args.previews:
        dest=args.previews.expanduser().resolve()
        dest.mkdir(exist_ok=True,parents=True)
        for s in bpy.data.scenes:
            s.render.resolution_percentage=35
            s.cycles.samples=4
            s.render.image_settings.file_format='JPEG'
            s.render.filepath=str(dest/(s['Source root']+'.jpg'))
            bpy.ops.render.render(scene=s.name,write_still=True)
    print(target,flush=True)

if __name__=='__main__':
    main()
    if not bpy.app.binary_path:
        sys.stdout.flush();sys.stderr.flush();os._exit(0)
