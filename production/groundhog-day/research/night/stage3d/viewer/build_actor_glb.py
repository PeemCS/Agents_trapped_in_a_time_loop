"""Make an interchangeable, animated field-coat GLB from the native reporter's joints and materials."""
import json
import math
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent


def primitive(kind):
    points=[];normals=[];indices=[]
    if kind=="Cube":
        for axis,sgn in [(a,s) for a in range(3) for s in (-1,1)]:
            u,v=(axis+1)%3,(axis+2)%3
            offset=len(points)
            for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                p=[0.0]*3;p[axis]=sgn*.5;p[u]=a*.5;p[v]=b*.5;points.append(p)
                n=[0.0]*3;n[axis]=sgn;normals.append(n)
            winding=[0,1,2,0,2,3] if sgn==1 else [2,1,0,3,2,0]
            indices.extend(offset+i for i in winding)
    else:
        for row in range(9):
            latitude=math.pi*row/8
            for col in range(13):
                angle=2*math.pi*col/12
                n=[math.sin(latitude)*math.cos(angle),math.cos(latitude),math.sin(latitude)*math.sin(angle)]
                normals.append(n);points.append([v*.5 for v in n])
        for row in range(8):
            for col in range(12):
                a=row*13+col;b=a+13;indices.extend([a,a+1,b,a+1,b+1,b])
    return points,normals,indices


def main():
    data=json.loads((HERE/"geometry.js").read_text().split(" = ",1)[1].rstrip(";\n"))
    rig=data["rigs"]["reporter"]
    binary=bytearray()
    doc={"asset":{"version":"2.0","generator":"Another Tuesday stage wardrobe"},
         "scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"name":"Reporter","children":[]}],
         "meshes":[],"materials":[],"animations":[],"bufferViews":[],"accessors":[],"buffers":[],
         "extras":{"source_usda_sha256":data["usda_sha256"],"variant":"mustard field coat"}}
    def acc(values,n,code="f",component=5126,target=None,bounds=False):
        while len(binary)%4:binary.append(0)
        flat=[v for row in values for v in row] if n>1 else list(values)
        start=len(binary);binary.extend(struct.pack("<"+code*len(flat),*flat))
        view={"buffer":0,"byteOffset":start,"byteLength":len(binary)-start}
        if target:view["target"]=target
        v=len(doc["bufferViews"]);doc["bufferViews"].append(view)
        a={"bufferView":v,"componentType":component,"count":len(values),"type":{1:"SCALAR",3:"VEC3",4:"VEC4"}[n]}
        if bounds:
            cols=list(zip(*values)) if n>1 else [values]
            a["min"]=[min(c) for c in cols];a["max"]=[max(c) for c in cols]
        i=len(doc["accessors"]);doc["accessors"].append(a);return i
    geometry={}
    for shape in ("Cube","Sphere"):
        pts,ns,ix=primitive(shape)
        geometry[shape]=(acc(pts,3,target=34962,bounds=True),acc(ns,3,target=34962),acc(ix,1,"H",5123,34963))
    def child(parent,node):
        i=len(doc["nodes"]);doc["nodes"].append(node);doc["nodes"][parent].setdefault("children",[]).append(i);return i
    joints={name:child(0,{"name":name,"translation":pos,"children":[]}) for name,pos in rig["joints"].items()}
    cache={}
    def mesh(parent,name,kind,pos,size,color):
        key=(kind,tuple(color))
        if key not in cache:
            material=len(doc["materials"]);doc["materials"].append({"pbrMetallicRoughness":{"baseColorFactor":[*color,1],"metallicFactor":0,
                                                                                           "roughnessFactor":.82}})
            v,n,ix=geometry[kind];cache[key]=len(doc["meshes"])
            doc["meshes"].append({"primitives":[{"attributes":{"POSITION":v,"NORMAL":n},"indices":ix,"material":material}]})
        return child(parent,{"name":name,"mesh":cache[key],"translation":pos,"scale":size})
    sources={}
    mustard=[.64,.36,.070];trim=[.052,.13,.104]
    for s in rig["shapes"]:
        name=s["path"].split("/")[-1];parts=s["path"].split("/");joint=parts[1] if len(parts)>2 else None
        color=mustard if name=="Coat" or joint and joint.startswith("Arm") else trim if name in ("Scarf","Cap") else s["color"]
        sources[name]=mesh(joints.get(joint,0),name,s["type"],s["position"],s["size"],color)
    mesh(0,"Cap visor","Cube",[0,1.166,.112],[.35,.025,.19],trim)
    mesh(0,"Scarf tail","Cube",[.07,.825,.14],[.084,.22,.036],trim)
    for i in range(3):mesh(0,"Coat button "+str(i),"Sphere",[.024,.55+i*.12,.13],[.028,.028,.022],[.20,.14,.071])
    for i in range(2):
        mesh(joints["Leg"+str(i)],"Weather boot","Sphere",[0,-.36,.04],[.17,.13,.245],[.052,.061,.046])
        mesh(joints["Arm"+str(i)],"Glove","Sphere",[0,-.375,0],[.135,.135,.125],[.098,.112,.078])
    t=[i/8 for i in range(9)];time=acc(t,1,bounds=True)
    walk={"name":"Walk","samplers":[],"channels":[]}
    for number in range(2):
        for name,amp in [("Leg",.42),("Arm",-.34)]:
            angle=[amp*math.sin(2*math.pi*p+number*math.pi) for p in t]
            quat=[[math.sin(v/2),0,0,math.cos(v/2)] for v in angle];out=acc(quat,4)
            k=len(walk["samplers"]);walk["samplers"].append({"input":time,"output":out,"interpolation":"LINEAR"})
            walk["channels"].append({"sampler":k,"target":{"node":joints[name+str(number)],"path":"rotation"}})
    idle={"name":"Idle","samplers":[],"channels":[]}
    head=doc["nodes"][sources["Head"]]["translation"]
    out=acc([[head[0],head[1]+.004*math.sin(2*math.pi*v),head[2]] for v in t],3)
    idle["samplers"].append({"input":time,"output":out,"interpolation":"LINEAR"})
    idle["channels"].append({"sampler":0,"target":{"node":sources["Head"],"path":"translation"}})
    doc["animations"]=[idle,walk];doc["buffers"]=[{"byteLength":len(binary)}]
    header=json.dumps(doc,separators=(",",":")).encode();header+=b" "*((-len(header))%4);binary.extend(b"\0"*((-len(binary))%4))
    output=b"glTF"+struct.pack("<II",2,28+len(header)+len(binary))+struct.pack("<I4s",len(header),b"JSON")+header+struct.pack("<I4s",len(binary),b"BIN\0")+binary
    out=HERE/"assets/field-coat.glb";out.parent.mkdir(exist_ok=True);out.write_bytes(output);print(out,len(output))


if __name__=="__main__":main()
