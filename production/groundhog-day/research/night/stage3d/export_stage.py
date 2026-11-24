"""Export a camera, three independently moving character rigs and both physical sets to OpenUSD."""
import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent


def v(numbers):
    return "("+", ".join(f"{n:.5f}" for n in numbers)+")"


def color(hexv):
    # USD displayColor stores linear values.
    srgb=[int(hexv[i:i+2],16)/255 for i in (1,3,5)]
    return v([n/12.92 if n <= .04045 else ((n+.055)/1.055)**2.4 for n in srgb])


def ident(name):
    return re.sub(r"[^a-zA-Z0-9_]","_",name)


def shape(kind,name,pos,size,paint,extra=""):
    param={"Cube":"double size = 1","Sphere":"double radius = 0.5","Cone":'double radius = 0.5\ndouble height = 1\nuniform token axis = "Y"',
           "Cylinder":'double radius = 0.5\ndouble height = 1\nuniform token axis = "Y"'}[kind]
    return f'''def {kind} "{name}" {{
        {param}
        color3f[] primvars:displayColor = [{color(paint)}]
        double3 xformOp:translate = {v(pos)}
        float3 xformOp:scale = {v(size)}
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
        {extra}
    }}
'''


def group(name, body):
    return f'def Xform "{ident(name)}" {{\n'+body+'}\n'


def townset(data, key):
    delta=data["setOffsets"][key]
    shapes=[shape("Cube","Snow",(10,-.10,10),(30,.19,31),"#e2e6df")]
    for i,(a,b,width) in enumerate(data["roads"][key]):
        cx=(a[0]+b[0])/2;cz=(a[1]+b[1])/2
        sx=abs(a[0]-b[0]);sz=abs(a[1]-b[1])
        if min(sx,sz)>.001:continue
        shapes.append(shape("Cube",f"Street{i}",(cx,.006,cz),(max(sx,width),.015,max(sz,width)),"#8c9c98"))
        along_x=sx>sz
        for j in range(math.floor(max(sx,sz)/2)):
            at=(min(a[0],b[0])+1+j*2 if along_x else cx,.016,cz if along_x else min(a[1],b[1])+1+j*2)
            shapes.append(shape("Cube",f"Line{i}_{j}",at,(.60 if along_x else .06,.013,.06 if along_x else .60),"#e6c381"))
    for i,b in enumerate(data["buildings"][key]):
        x,z,w,d,h=[b[n] for n in ("x","y","w","d","h")]
        part=[shape("Cube","Walls",(x+w/2,h/2,z+d/2),(w,h,d),b["wall"]),
              shape("Cube","Cornice",(x+w/2,h-.08,z+d/2),(w+.13,.15,d+.13),b["roof"]),
              shape("Cube","SnowRoof",(x+w/2,h+.04,z+d/2),(w+.24,.13,d+.24),"#f5f1de"),
              shape("Cube","Door",(x+w*.50,.46,z+d+.016),(.41,.9,.05),"#364f4b")]
        rows=2 if h>=1.7 else 1;cols=max(2,int(w/.80))
        for a in range(rows):
            for c in range(cols):
                if a==0 and abs((c+.5)/cols-.5)<.15:continue
                y=.56+a*(h-.55)/rows
                part.append(shape("Cube",f"Window{a}_{c}",(x+(c+.5)*w/cols,y,z+d+.028),(.35,.43,.045),"#efc36e" if (a+c+i)%3==0 else "#6e8b8d"))
        for c in range(max(2,int(d/.9))):
            part.append(shape("Cube",f"SideWindow{c}",(x+w+.018,min(h-.22,.73),z+(c+.55)*d/max(2,int(d/.9))),(.045,.4,.35),"#788e91"))
        shapes.append(group(b.get("id",b["kind"]+str(i)), "".join(part)))
    # The square’s gazebo and the terminal phone are blocking landmarks for camera operators.
    if key=="town":
        shapes += [shape("Cylinder","Bandstand",(12,.15,12.68),(2.1,.32,2.1),"#9b8370"),
                   shape("Cone","Gazebo",(12,1.85,12.68),(2.55,1.05,2.55),"#7e9182")]
        for i,(dx,dz) in enumerate([(-.7,-.55),(-.7,.55),(.7,-.55),(.7,.55)]):
            shapes.append(shape("Cube",f"GazeboPost{i}",(12+dx,.91,12.68+dz),(.08,1.3,.08),"#a58b6e"))
    else:
        shapes += [shape("Cube","Payphone",(11.5,.53,11.65),(.38,.98,.22),"#426157"),shape("Cube","PayphoneSign",(11.5,1.09,11.65),(.49,.21,.23),"#ded8aa")]
    for i,(x,z) in enumerate([(1.1,3.2),(2.5,2.1),(4.2,2.3),(21,5),(20.6,6.7),(1.2,17.7),(3,18.5),(5.5,18.7),(20.4,18.7)]):
        shapes.append(shape("Cone",f"Spruce{i}",(x,.92,z),(1.35,1.9,1.35),"#587569"))
        shapes.append(shape("Cone",f"Frost{i}",(x,1.50,z),(.88,1.22,.88),"#e4e8dd"))
    transform=f'double3 xformOp:translate = {v((delta,0,0))}\nuniform token[] xformOpOrder = ["xformOp:translate"]\n'
    return group("MillCreek" if key=="town" else "Pittsburgh",transform+"".join(shapes))


def samples_block(kind,name,values):
    return f'{kind} {name}.timeSamples = {{\n'+",\n".join(f"  {t}: {val}" for t,val in values)+"\n}\n"


def actor(data,index):
    frames=data["samples"];parts=[];c=["#a85c49","#617b89","#6d8169"][index]
    parts.append(shape("Cube","Coat",(0,.66,0),(.36,.58,.24),c))
    parts.append(shape("Sphere","Head",(0,1.07,0),(.30,.33,.29),["#d3a083","#a87354","#d0a380"][index]))
    parts.append(shape("Sphere","Cap",(0,1.18,-.009),(.32,.19,.30),["#4b5654","#594839","#4d5552"][index]))
    parts.append(shape("Sphere","Nose",(0,1.06,.14),(.075,.085,.085),["#cfa88a","#af8469","#c09473"][index]))
    for eye,x in enumerate((-.055,.055)):
        parts.append(shape("Sphere",f"Eye{eye}",(x,1.095,.133),(.026,.025,.024),"#3c3832"))
    parts.append(shape("Cube","Scarf",(0,.91,.015),(.36,.084,.255),["#8f4c3a","#d1a15f","#86523d"][index]))
    for k,dx in enumerate((-.095,.095)):
        offsets=[];arms=[]
        for s in frames:
            f=s["frame"];a=s["actors"][index];wave=math.sin(f*.37+k*math.pi) if a["moving"] else 0
            offsets.append((f,round(19*wave,2)));arms.append((f,round(-14*wave,2)))
        for nm,x,y,length,angles,col in [("Leg",dx,.42,.39,offsets,"#45524c"),("Arm",dx*2.12,.85,.38,arms,c)]:
            joint=f'double3 xformOp:translate = {v((x,y,0))}\n'+samples_block("float","xformOp:rotateX",angles)
            joint+='uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateX"]\n'
            bone=shape("Cube","Cloth",(0,-length/2,0),(.12,length,.14),col)
            parts.append(group(nm+str(k),joint+bone))
    if index==2:parts.append(shape("Cube","Camera",(.16,.83,.16),(.3,.18,.26),"#35403f"))
    moves=[];angles=[];previous=None;heading=[14.0,35.0,-20.0][index]
    for s in frames:
        a=s["actors"][index];t=s["frame"];position=(a["x"],0,a["z"])
        if previous:
            dx,dz=a["x"]-previous["x"],a["z"]-previous["z"]
            teleported=previous["scene"]!=a["scene"] or math.hypot(dx,dz)>2.0
            if teleported:
                moves.append((round(t-.001,3),v((previous["x"],0,previous["z"]))))
            elif a["moving"] and math.hypot(dx,dz)>.002:
                # Unwrapped yaw keeps the rig from spinning 360° as a route crosses north.
                target=math.degrees(math.atan2(dx,dz))
                heading+=(target-heading+180)%360-180
        moves.append((t,v(position)));angles.append((t,round(heading,2)));previous=a
    transforms=samples_block("double3","xformOp:translate",moves)+samples_block("float","xformOp:rotateY",angles)
    visibility=samples_block("token","visibility",[(s["frame"],'"inherited"' if s["actors"][index]["visible"] else '"invisible"') for s in frames if s["frame"]==0 or s["actors"][index]["visible"]!=frames[s["frame"]-1]["actors"][index]["visible"]])
    extras=f'custom string characterRole = "{frames[0]["actors"][index]["role"]}"\n'
    return group(frames[0]["actors"][index]["name"],extras+visibility+transforms+'uniform token[] xformOpOrder = ["xformOp:translate","xformOp:rotateY"]\n'+"".join(parts))


def export(data,sha):
    frames=data["samples"]
    body="".join(townset(data,key) for key in ("town","city"))
    body+=group("Cast","".join(actor(data,i) for i in range(3)))
    vehicle=samples_block("double3","xformOp:translate",[(s["frame"],v((s["bus"]["x"],.40,s["bus"]["z"]) if s["bus"] else (0,-20,0))) for s in frames])
    vehicle+='uniform token[] xformOpOrder = ["xformOp:translate"]\n'
    vehicle+=shape("Cube","Body",(0,0,0),(1.9,.66,.67),"#aa7750")+shape("Cube","Glass",(0,.15,.337),(1.68,.24,.023),"#729393")+shape("Cube","Roof",(0,.36,0),(1.94,.09,.71),"#e7dbb5")
    for i,x in enumerate((-.65,.65)):
        vehicle+=shape("Sphere",f"Wheel{i}",(x,-.25,.32),(.35,.35,.12),"#364541")
    body+=group("Coach",vehicle)
    # Camera is Y-up, looking down its -Z axis. Discontinuous set changes use adjacent frame keys.
    cam_positions=[(s["frame"],v((s["actors"][0]["x"]+4.8,5.2,s["actors"][0]["z"]+7))) for s in frames]
    camera='def Camera "ReporterCamera" {\nfloat focalLength = 27\nfloat horizontalAperture = 30\nfloat verticalAperture = 16.875\n'
    camera+=samples_block("double3","xformOp:translate",cam_positions)
    camera+='float xformOp:rotateY = 34.44\nfloat xformOp:rotateX = -28.20\nuniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateY", "xformOp:rotateX"]\n}\n'
    body+=camera
    for i,e in enumerate(data["shots"]):
        props=[f'custom string eventId = "{e["id"]}"',f'custom string action = "{e["action"]}"',f'custom int startFrame = {i*data["framesPerSlot"]}']
        body+=group("Shot"+str(i), "\n".join(props)+"\n")
    return ('#usda 1.0\n(\n defaultPrim = "Stage"\n upAxis = "Y"\n metersPerUnit = 1\n startTimeCode = 0\n'
            +f' endTimeCode = {frames[-1]["frame"]}\n framesPerSecond = {data["fps"]}\n timeCodesPerSecond = {data["fps"]}\n)\n'
            +group("Stage",f'custom string sourceSHA256 = "{sha}"\n'+body))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("take",type=Path);p.add_argument("--begin",type=int,default=4);p.add_argument("--end",type=int,default=10)
    p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    data=json.loads(subprocess.check_output(["node",str(HERE/"sample.cjs"),str(a.take),str(a.begin),str(a.end)]))
    sha=hashlib.sha256(a.take.read_bytes()).hexdigest();file=a.out/"another-tuesday.usda"
    file.write_text(export(data,sha))
    meta={"source_sha256":sha,"shots":data["shots"],"frames":len(data["samples"]),"fps":data["fps"],"city_offset_metres":data["setOffsets"]["city"],
          "stage_file":file.name,"camera":"/Stage/ReporterCamera","moving_rigs":3,"geometry":"original replaceable proxy meshes and props"}
    (a.out/"shot-manifest.json").write_text(json.dumps(meta,indent=2)+"\n")
    print(file)

if __name__=="__main__":
    main()
