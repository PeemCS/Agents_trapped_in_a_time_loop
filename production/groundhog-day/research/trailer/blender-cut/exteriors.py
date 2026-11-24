"""Miniature Pennsylvania street and coach sets. Author in metres, Three.js axes."""
from collections import defaultdict
from contextlib import contextmanager
from math import sin, cos, pi, sqrt
from pathlib import Path
import random
import bpy
from mathutils import Vector, Matrix

rng = random.Random(721)
parts = defaultdict(lambda: ([], []))
smooth_faces = defaultdict(list)
labels = []
parents = {}
here = None
# Costumes and prop colours are shared by the two visits to Main Street.
SNOW = "d7e1de"
ICE = "a1b8bc"
METAL = "394747"
BRASS = "b18b54"
CREAM = "eddfb9"
GLASS = "6c8b92"
INK = "242e30"
WOOD = "74503f"
RED = "873f40"
AMBER = "ffc279"
NAVY = "31495c"
BLUE = "91b5c2"
GRAY = "8a9391"
FILM = "39413a"

@contextmanager
def group(name, parent=None):
    global here
    old = here
    here = name
    if parent is not None:
        parents[name] = parent
    yield
    here = old

def mesh(v, faces, color, smooth=False):
    dst, fi = parts[here,color]
    if smooth:
        smooth_faces[here,color].extend(range(len(fi),len(fi)+len(faces)))
    start = len(dst)
    dst.extend((x,-z,y) for x,y,z in v)
    fi.extend([tuple(i+start for i in face) for face in faces])

def box(x,y,z,w,h,d,c,tilt=0):
    v=[]
    for u,vv,ww in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                      (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:
        a,b = vv*h/2,ww*d/2
        v.append((x+u*w/2,y+a*cos(tilt)-b*sin(tilt),z+a*sin(tilt)+b*cos(tilt)))
    mesh(v,[(3,2,1,0),(4,5,6,7),(0,4,7,3),(1,2,6,5),(3,7,6,2),(0,1,5,4)],c)

def rod(a,b,r,c,n=10,r2=None):
    va, vb = Vector(a), Vector(b)
    axis = (vb-va).normalized()
    orth = axis.cross(Vector((0,1,0)))
    if orth.length < 0.01:
        orth = axis.cross(Vector((0,0,1)))
    orth.normalize()
    other = axis.cross(orth)
    vs = []
    for p,rad in ((va,r),(vb,r if r2 is None else r2)):
        vs.extend([tuple(p+(cos(t*2*pi/n)*orth+sin(t*2*pi/n)*other)*rad) for t in range(n)])
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh(vs,faces,c)

def pole(x,y,z,rad,h,c,n=12,r2=None):
    rod((x,y,z),(x,y+h,z),rad,c,n,r2)

def egg(x,y,z,rx,ry,rz,c,n=14,rings=8):
    vs=[(x,y-ry,z)]
    for j in range(1,rings):
        phi=-pi/2+pi*j/rings
        vs.extend((x+rx*cos(phi)*cos(2*pi*i/n),y+ry*sin(phi),z+rz*cos(phi)*sin(2*pi*i/n)) for i in range(n))
    vs.append((x,y+ry,z))
    fs=[(0,1+i,1+(i+1)%n) for i in range(n)]
    for j in range(rings-2):
        a=1+j*n
        fs.extend((a+i,a+i+n,a+n+(i+1)%n,a+(i+1)%n) for i in range(n))
    a=1+(rings-2)*n
    fs.extend((len(vs)-1,a+(i+1)%n,a+i) for i in range(n))
    mesh(vs,fs,c,smooth=True)

def text(s,x,y,z,h,color=CREAM,align='CENTER',font='DIN Condensed Bold.ttf',rot=0):
    labels.append((here,s,x,y,z,h,color,align,font,rot))

def lintel(x,y,z,w,h,c):
    box(x,y,z,w,h,.15,c)
    box(x,y+h*.42,z+.045,w+.07,.04,.17,c)

def glass_window(x,y,z,w,h,frame=CREAM,lit=False):
    box(x,y,z,w+.16,h+.19,.15,frame)
    box(x,y,z+.091,w,h,.08,"bb9f76" if lit else GLASS)
    box(x,y,z+.15,.033,h,.032,frame)
    box(x,y+.10*h,z+.15,w,.035,.033,frame)
    lintel(x,y-h/2-.11,z+.12,w+.32,.13,frame)
    if lit:
        for sign in (-1,1):
            box(x+sign*w*.39,y+.13*h,z+.153,w*.145,h*.72,.025,"eccea0")
    else:
        box(x,y+h*.41,z+.14,w,.13,.025,"94a6a3")

def car(color, wagon=False):
    # Nose toward -X. Body profile swept across width, inset windows and chrome.
    profile=[(-2.02,.47),(-2.04,.75),(-1.90,.89),(-1.13,.97),(-.68,1.43),
             ((1.47 if wagon else .65),1.43),((1.78 if wagon else 1.15),1.02),
             (1.90,.95),(2.02,.75),(1.98,.46)]
    vs=[(x,y,z) for z in (-.78,.78) for x,y in profile]
    n=len(profile)
    # Reverse needed for CCW forward face.
    fs=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]
    fs.extend((i,n+i,n+(i+1)%n,(i+1)%n) for i in range(n))
    mesh(vs,fs,color)
    for side in (-1,1):
        z=.786*side
        for x1,x2,top1,top2 in [(-1.01,-.03,-.66,-.03),(.04,.86,.04,.63)]:
            verts=[(x1,1.015,z),(x2,1.015,z),(top2,1.37,z),(top1,1.37,z)]
            mesh(verts,[(0,1,2,3) if side==1 else (3,2,1,0)],"586c74")
        if wagon:
            box(1.19,1.19,z,.53,.32,.01,"586c74")
        box(.01,.90,z,3.84,.03,.022,"c3bbb0")
        for x in (-.25,.81):
            box(x,.945,z,.13,.028,.04,"d2c8ae")
        for x in (-1.27,1.27):
            rod((x,.43,z-.1*side),(x,.43,z+.085*side),.38,"282d31",24)
            rod((x,.43,z+.09*side),(x,.43,z+.105*side),.238,"bdc0b4",20)
            rod((x,.43,z+.107*side),(x,.43,z+.115*side),.172,"697674",18)
            # Concentric rim and sidewall bands give the hero wheel its rubber profile.
            for radius,thickness,shade in [(.318,.010,"363b3b"),(.292,.007,"404642"),(.217,.011,"929d98")]:
                for j in range(36):
                    t0=j*2*pi/36;t1=(j+1)*2*pi/36
                    rod((x+radius*cos(t0),.43+radius*sin(t0),z+.092*side),
                        (x+radius*cos(t1),.43+radius*sin(t1),z+.092*side),thickness,shade,5)
            for j in range(8):
                th=(j+.45)*2*pi/8
                rod((x+.199*cos(th),.43+.199*sin(th),z+.106*side),
                    (x+.199*cos(th),.43+.199*sin(th),z+.111*side),.019,"63706b",8)
            for j in range(5):
                th=j*2*pi/5
                egg(x+.092*cos(th),.43+.092*sin(th),z+.12*side,.022,.022,.014,"bbb4a3",8,4)
    for side in (-1,1):
        box(side*2.0,.50,0,.09,.10,1.54,"abb4ac")
    for z in (-.53,.53):
        box(-2.035,.73,z,.035,.14,.32,"f2d39d")
        box(2.02,.735,z,.035,.12,.31,"983e32")
    # Windscreens are sloped rather than painted onto an upright face.
    mesh([(-1.11,.993,-.71),(-1.11,.993,.71),(-.676,1.414,.68),(-.676,1.414,-.68)],[(0,1,2,3)],"809398")
    box(.06,1.442,0,1.15,.032,1.34,SNOW)
    box(1.90,.626,0,.1,.13,.32,"ece0b7")

def bare_tree(x,z,h):
    pole(x,.12,z,.125,h*.73,"665a55",8,.052)
    for i in range(10):
        f=.32+.043*i
        a=i*2.399
        l=h*(.25+.045*(i%3))
        p=(x,h*f,z)
        tip=(x+l*cos(a),h*(f+.23),z+l*sin(a))
        rod(p,tip,.044,"665a55",6,.009)
        rod(tuple((2*j+k)/3 for j,k in zip(tip,p)),(tip[0]+.25*cos(a+1),tip[1]+.45,tip[2]+.24*sin(a+1)),.02,"796960",5,.006)

def streetlamp(x,z):
    pole(x,.13,z,.21,.19,METAL,12,.16)
    pole(x,.31,z,.095,2.53,METAL,10,.066)
    pole(x,2.75,z,.11,.15,BRASS)
    pole(x,2.88,z,.16,.08,METAL,8,.25)
    pole(x,2.95,z,.17,.38,"ffddab",6,.235)
    pole(x,3.32,z,.27,.17,METAL,6,.05)
    for j in range(6):
        a=(j+.5)*2*pi/6
        rod((x+.18*cos(a),2.95,z+.18*sin(a)),(x+.239*cos(a),3.33,z+.239*sin(a)),.013,METAL,6)

def awning(x,z,w,base=3.2):
    stripe=.29
    n=round(w/stripe)
    for j in range(n):
        xx=x-w/2+(j+.5)*w/n
        color=RED if j%2==0 else "d0bb9f"
        box(xx,base+.18,z+.43,w/n+.001,.075,.97,color,.32)
        box(xx,base-.04,z+.88,w/n,.20,.04,color)
        egg(xx,base-.14,z+.88,w/n*.50,.075,.022,color,8,4)

def storefront(x,w,h,brick,sign,idx):
    z=-1.4
    box(x,h/2,z-2.8,w,h,5.6,brick)
    # Irregular brick relief gives the facade local texture without noisy outlines.
    for row in range(int((h-2.9)/.34)):
        for col in range(int(w/.78)):
            if rng.random()<.23:
                xx=x-w/2+(col+.5+.20*(row%2))*.78
                if xx<x+w/2-.22:
                    box(xx,3.12+.34*row,z+.018,.55,.11,.04,rng.choice([brick,"9c7461","a07963"]))
    for side in (-1,1):
        for y in [.48,2.16,3.81]:
            box(x+side*(w/2-.19),y,z+.12,.30,.98,.30,"b09980")
    for yy in [h-.05,h-.28,3.70]:
        lintel(x,yy,z+.16,w+.13,.11,"c3ac90")
    box(x,h+.085,z-2.8,w+.12,.15,5.8,SNOW)
    for i in range(int(w/2.0)):
        wx=x-w/2+(i+.5)*w/int(w/2.0)
        for wy in [4.72,6.62,8.52]:
            if wy<h-.25: glass_window(wx,wy,z+.08,.92,1.34,"c1ac93",lit=(i+idx)%3==0)
    box(x,1.40,z+.06,w-.73,2.48,.19,"384846")
    for i in range(3):
        xx=x-w*.31+i*w*.31
        if i==1:
            box(xx,1.20,z+.19,.98,2.35,.09,"534d40")
            box(xx,1.52,z+.261,.76,1.32,.05,"8d9387")
            box(xx+.35,1.09,z+.33,.04,.23,.04,BRASS)
        else:
            box(xx,1.58,z+.180,w*.25,1.68,.15,"b4a78b" if idx%2 else "839994")
            for k in range(3):
                box(xx+(k-1)*w*.073,1.42,z+.265,.028,1.47,.014,"596763")
            box(xx,1.71,z+.28,w*.25,.04,.035,"65726b")
            for j in range(4):
                bh=rng.uniform(.09,.38)
                box(xx-w*.097+j*w*.062,.78+bh/2,z+.28,.22,bh,.08,rng.choice(["756855","737d72","a57d55"]))
    box(x,3.19,z+.19,w-.48,.63,.18,["324748","68513f",RED][idx%3])
    text(sign,x,3.18,z+.30,.47,"ecdfbe")
    if idx in (1,3,5): awning(x,z+.26,w-.52,2.72)
    else:
        box(x,2.77,z+.41,w-.39,.10,.68,"abb7ad")
        box(x,2.838,z+.41,w-.4,.03,.69,SNOW)

def weather_camera():
    # Largely silhouetted against the white February street.
    for x,z in [(-.46,.33),(.43,.35),(.03,-.46)]:
        rod((0,1.23,0),(x,.04,z),.041,"364447",8)
        rod((x*.59,.55,z*.59),(x,.04,z),.019,"9ca8a6",8)
    pole(0,1.21,0,.09,.14,INK)
    box(0,1.47,0,.37,.26,.5,INK)
    rod((.02,1.53,.21),(.02,1.53,.40),.105,METAL,14,.10)
    rod((.02,1.53,.385),(.02,1.53,.45),.12,INK,14)
    rod((.02,1.53,.453),(.02,1.53,.457),.08,"7297a3",14)
    box(.16,1.64,.08,.16,.10,.17,"333a39")
    box(0,1.647,-.025,.177,.060,.25,"767d71")
    box(0,1.47,-.264,.26,.137,.029,"415b5b")
    text("WPTV",0,1.468,-.286,.096,"e5dcbc")
    box(.166,1.53,.264,.03,.028,.008,"d64e40")
    rod((-.169,1.665,.056),(-.169,1.668,.31),.031,"525959",12)
    box(-.11,1.714,-.03,.05,.038,.17,"3a4647")

def build_street():
    with group("Street_miniature","street"):
        box(0,-.21,2,110,.4,64,"a7b7b8")
        box(0,-.058,7.1,105,.10,8.4,"616d70")
        box(0,-.02,6.9,105,.01,1.9,"737e80")
        for x in range(-38,40,5):
            box(x,.001,7.0,1.9,.014,.075,"ceba83")
        for x in range(-32,40,2):
            box(x,.046,.28,1.989,.145,4.21,"b9c4c1" if x%4 else "bcc8c6")
            box(x,.14,2.52,1.99,.19,.28,"a1afae")
            box(x,.249,2.53,1.97,.032,.33,SNOW)
        for j in range(220):
            x=rng.uniform(-32,35)
            z=rng.choice([rng.uniform(2.59,3.37),rng.uniform(-1.02,-.13),rng.uniform(10.56,11.4)])
            egg(x,.10 if z<0 else .05,z,rng.uniform(.13,.8),rng.uniform(.02,.13),rng.uniform(.07,.29),rng.choice([SNOW,"c5d2d0","d4deda"]),8,4)
        colors=["8e7767","836454","b09070","8d6057","a08f76","7d7770","7c7367","8b6856"]
        stores=[(-22,7.1,9.2,"GROCER"),(-15,6.8,7.1,"SILVER SPOON"),(-8,6.9,8.9,"MERCANTILE"),(-1.0,6.9,8.1,"HOLLIS  &  SON"),(6.35,7.7,9.3,"HEARTHSIDE   HOTEL"),(13.3,6.0,7.3,"RIALTO"),(19.4,6,8.9,"RECORDS"),(25.6,6.2,7.4,"MILLER'S")]
        for idx,(x,w,h,sign) in enumerate(stores):
            storefront(x,w,h,colors[idx],sign,idx)
            box(x+.29*w,h+.79,-4.2,.58,1.65,.67,"856b5e")
            box(x+.29*w,h+1.64,-4.2,.67,.12,.77,SNOW)
        # Traditional blade sign and canopy at the hotel entrance.
        box(8.06,4.36,-.32,.75,2.7,.33,"394c49")
        for i,letter in enumerate("HOTEL"):
            text(letter,8.06,5.37-i*.50,-.138,.44,"e7c393")
        for y in [3.28,5.42]:
            rod((8.05,y,-1.23),(8.05,y,-.31),.035,METAL)
        for x in (-17.0,-5.86,2.25,11.8,22):
            streetlamp(x,2.04)
        for x in [-20.6,-11.5,3.62,16.45,28]:
            bare_tree(x,2.12,rng.uniform(3.1,4.2))
        for x in range(-32,38,4):
            # Buildings across the street sit behind most camera positions, but
            # appear when Phil glances toward the passing coach.
            h=rng.uniform(5,10)
            box(x,h/2,17.0,3.97,h,5,rng.choice(["75888a","9a9e92","7e8c87"]))
            box(x,h+.12,17.0,4.13,.25,5.19,SNOW)
        for x in [-31,-17,0,17.5,32]:
            pole(x,.1,-7,.14,10.3,"756e5c",10,.09)
            box(x,9.93,-7,2.55,.10,.12,"7e745f")
        for z in [-6.84,-7.22]:
            for x in range(-34,36,13):
                for j in range(4):
                    a=x+j*3.25
                    rod((a,10.26-.21*sin(j*pi/4),z),(a+3.25,10.26-.21*sin((j+1)*pi/4),z),.021,"66716d",5)
        for x,z in [(1.02,-.2),(1.32,-.2)]:
            pole(x,.13,z,.026,.16,BRASS)
        rod((1.02,.29,-.2),(1.32,.29,-.2),.025,BRASS)
        # Enamel weather slate and chalk forecast.
        for x in [-6.33,-5.29]:
            rod((x,.15,.02),(x,1.9,.06),.035,WOOD)
        box(-5.81,1.60,.04,1.35,.91,.09,"293e43")
        box(-5.81,1.60,.095,1.27,.82,.03,CREAM)
        text("W E A T H E R",-5.81,1.81,.125,.135,FILM)
        text("TUE   FEB  2",-5.81,1.54,.125,.195,"3f595b")
        text("W P T V    •    9",-5.81,1.34,.125,.084,RED)
        # Planted snow prints follow the pavement to the entry.
        for i in range(32):
            xx=-5+i*.44
            zz=.55+.13*(-1)**i
            egg(xx,.124,zz,.063,.007,.13,"a2afac",8,4)
    with group("ExtCamera","street"): weather_camera()
    with group("ExtWagon","street"): car("344c58",True)
    with group("ExtSedan","street"): car("66715a")
    with group("ExtPolicy","street"):
        box(0,0,0,.41,.027,.28,RED)
        box(0,.019,.01,.382,.011,.247,"93b5c8")
        box(-.008,.028,-.004,.37,.006,.236,"eee6ce")
        for j in range(7):
            box(-.015,.033,-.076+j*.024,.27,.001,.003,"99938a")
        box(-.10,.033,-.105,.12,.002,.009,"65594c")
    with group("ExtBallpoint","street"):
        rod((-.07,0,0),(.07,0,0),.008,INK,10)
        rod((.07,0,0),(.087,0,0),.008,BRASS,8,.001)
    with group("ExtReceipt","street"):
        box(0,0,0,.257,.002,.16,"e4dfc6")
        for j in range(4): box(.005,.002,-.045+j*.021,.19,.001,.002,"9e9a86")
    with group("ExtCarbon","street"):
        box(0,0,0,.257,.003,.16,"87aec4")
    with group("ExtWatch","street"):
        # X axis follows the gloved arm from left to the centre.
        rod((-.43,-.11,.12),(-.05,0,0),.102,"303b40",14,.082)
        rod((-.10,-.012,.014),(-.047,.004,0),.086,"70685d",12,.09)
        egg(-.005,0,-.004,.085,.045,.10,"3c4240")
        for j in range(4):
            rod((.008,.014,-.052+j*.028),(.118,.009,-.042+j*.026),.016,"484843",8,.012)
        rod((.0,0,.068),(.056,-.045,.093),.023,"484843",8,.015)
        pole(-.074,.068,.006,.060,.012,"c9cec4",24)
        pole(-.074,.083,.006,.051,.005,"e4dbbc",24)
        for j in range(12):
            a=j*pi/6
            box(-.074+.042*sin(a),.089,.006+.042*cos(a),.004,.002,.004,INK)
        rod((-.074,.091,.006),(-.055,.091,-.018),.0025,INK,6)
        rod((-.074,.092,.006),(-.096,.092,.011),.003,INK,6)
    with group("ExtWheelHand","street"):
        rod((.25,.35,.10),(.06,.12,.01),.058,"323d43",12,.051)
        egg(.022,.084,.025,.060,.072,.031,"bc977c",14)
        for j in range(4):
            xx=-.021+j*.024
            rod((xx,.072,.038),(xx-.047,.005+j*.004,.051),.012,"bf987e",10,.0095)
        rod((.034,.10,.011),(.094,.046,.048),.020,"bd9579",10,.012)
    with group("ExtRooftop","street"):
        # Rear street, church bell and the outline of the town beyond Main Street.
        for xx in [-17,-8,-1,7,16]:
            hh=6.4+1.2*sin(xx)
            box(xx,hh/2,-9.8,5.42,hh,3.5,"85877b")
            mesh([(xx-2.95,hh,-7.9),(xx+2.95,hh,-7.9),(xx,hh+2.1,-7.9),
                  (xx-2.95,hh,-11.75),(xx+2.95,hh,-11.75),(xx,hh+2.1,-11.75)],
                 [(0,1,2),(5,4,3),(0,2,5,3),(2,1,4,5)],"a5b3b2")
        box(-2.8,6.05,-15.4,1.71,12.1,1.74,"8a8677")
        box(-2.8,11.38,-14.51,1.06,1.09,.08,"424a48")
        for j in range(4): box(-2.8,10.95+j*.22,-14.44,1.1,.065,.088,"959987")
        for yy in [10.58,12.13]: box(-2.8,yy,-15.4,1.96,.17,1.99,"bec0ac")
        pole(-2.8,12.21,-15.4,1.44,3.00,"65756e",4,.02)
        rod((-2.8,15.18,-15.4),(-2.8,15.78,-15.4),.024,"8f7752",6)
        for x in range(-48,49,4):
            egg(x,3.3,-33,7.15,rng.uniform(3.1,5.5),5.2,"839598",10,5)
    with group("ExtWarmWindows","street"):
        for idx,(x,w,h,sign) in enumerate(stores):
            for i in range(int(w/2.0)):
                wx=x-w/2+(i+.5)*w/int(w/2.0)
                for wy in [4.72,6.62,8.52]:
                    if wy<h-.25 and (i+idx+int(wy))%3!=0:
                        for k in (-1,1):
                            box(wx+k*.216,wy+.04,-1.148,.385,.98,.012,"dfb17b")
    with group("ExtWatchFinger","street"):
        rod((.35,-.09,.07),(.11,0,0),.073,"353e41",12,.064)
        egg(.082,.006,-.006,.091,.045,.067,"434642")
        rod((.059,.017,-.048),(-.055,.012,-.045),.018,"4d4b43",8,.014)
        for j in range(3):
            rod((.04,.0,-.018+j*.029),(-.002,-.036,-.020+j*.029),.018,"3f403c",8,.013)

def bench(x,z,length=3.45):
    for xx in [x-length*.38,x+length*.38]:
        for zz in [z-.17,z+.17]:
            pole(xx,.1,zz,.035,.39,METAL)
        rod((xx,.35,z-.19),(xx,.98,z-.31),.035,METAL)
    for k in range(5):
        box(x,.51,z-.21+k*.105,length,.055,.093,"976c50" if k%2 else "88664e")
    for k in range(3):
        box(x,.66+k*.13,z-.247-k*.020,length,.106,.052,"9a7659")

def build_depot():
    with group("Depot_shell","depot"):
        box(0,-.056,.1,14,.12,8,"a9ada5")
        for i in range(220):
            xx=rng.uniform(-6,6); zz=rng.uniform(-3.5,3.6)
            egg(xx,.008,zz,.012,.002,.012,rng.choice(["7b8785","cad0c9","b3b6a6"]),6,3)
        for xx in range(-6,7):
            box(xx,.007,0,.015,.006,7.5,"889696")
        for zz in range(-3,4):
            box(0,.007,zz,13,.006,.015,"889696")
        for x in [-6,6]: box(x,1.52,.2,.2,3.1,7.2,"acb4a9")
        box(0,.574,-3.02,12.1,1.16,.14,"8f9a92")
        box(0,1.166,-2.98,12.15,.09,.23,"687a76")
        for x in range(-6,7,2):
            box(x,2.11,-3.02,.083,1.88,.11,METAL)
            box(x+.96,2.50,-3.04,1.89,.040,.06,"78918c")
        box(0,3.04,-3.04,12.15,.12,.14,METAL)
        box(0,3.32,.15,13,.18,7.42,"c4c7b7")
        for x in [-4.4,-.2,4.0]:
            box(x,3.18,-.60,2.13,.086,.28,"697773")
            box(x,3.12,-.60,1.96,.037,.17,"fff1ba")
        for i in range(7):
            box(-5.2+i*1.10,1.85,-13,.4,rng.uniform(2.5,4.0),.42,"7e8b87")
        box(0,-.02,-12,65,.22,22,SNOW)
        box(0,8,-23.2,90,17,.11,"c2d0d1")
        for x in range(-36,40,4):
            egg(x,.08,-21.55,5.3,rng.uniform(1.1,2.5),1.16,"9caeb0",10,5)
        for i in range(23):
            bare_tree(rng.uniform(-14,16),rng.uniform(-18,-7),rng.uniform(2.4,5.6))
        bench(-3.6,-1.70,3.3)
        bench(1.6,1.95,4.3)
        box(3.48,1.90,-2.78,.88,1.27,.09,WOOD)
        box(3.48,1.9,-2.715,.79,1.15,.040,"d3cdb3")
        text("DEPARTURES",3.48,2.31,-2.687,.125,FILM)
        for i,hh in enumerate(["07 : 10","09 : 45","13 : 00","15 : 40","19 : 05"]):
            text(hh,3.44,2.095-i*.139,-2.68,.097,FILM)
            box(3.48,2.029-i*.139,-2.684,.62,.008,.006,"8e9486")
        box(-1.1,2.88,-2.95,3.15,.34,.12,"334449")
        text("P U N X S U T A W N E Y",-1.1,2.87,-2.874,.215,"e5d9bf")
        for x in [4.89,5.55]:
            pole(x,0,-2.71,.041,2.59,METAL)
        pole(-.83,.05,-2.1,.21,.75,"62766c")
        pole(-.83,.78,-2.1,.234,.07,"4b5953")
    with group("ExtLap","depot"):
        for x in (-.21,.21):
            egg(x,.365,.027,.163,.141,.385,"48505a")
            box(x,.53,.375,.153,.125,.42,"30393e")
            rod((x,.548,.35),(x,.548,.074),.073,"394346",16,.066)
            egg(x,.547,.027,.079,.041,.113,"d29d7d",18,10)
            egg(x+(.066 if x<0 else -.066),.534,-.010,.027,.025,.053,"c99778",12)
            for j in range(4):
                xx=x-.047+j*.031
                rod((xx,.555,-.038),(xx-.003,.531,-.144+.012*abs(j-1.5)),.0165,"d5a485",12,.012)
                egg(xx,.545,-.10,.012,.009,.015,"ddad92",10,5)
        box(-.21,.62,.139,.124,.018,.052,"b0b3a9")
        pole(-.21,.635,.139,.041,.006,"eee1c7",24)
        rod((-.21,.642,.139),(-.193,.642,.123),.0025,INK,6)

def build_coach():
    with group("Coach_frame","coach"):
        # The bus drives towards -X. Boarding door and seats share one shell.
        box(0,.43,0,9.85,.58,2.43,"7f918f")
        box(0,1.57,-1.23,9.82,2.41,.11,"59716e")
        box(0,2.85,0,9.83,.18,2.54,"8d9f9e")
        box(.54,1.10,1.23,8.58,.88,.12,"8f9c98")
        box(.54,1.20,1.303,8.63,.115,.025,"6b8079")
        box(.54,.97,1.304,8.63,.072,.025,"a68b6c")
        for y in [.48,.58,.68,.78]:
            box(.67,y,1.315,8.14,.019,.021,"bac3b7")
        for z in [-1.245,1.245]:
            box(.42,2.62,z,8.83,.17,.13,"69817e")
            for i in range(8):
                xx=-3.59+i*1.17
                box(xx,2.035,z,.115,1.05,.13,"435654")
                box(xx+.583,2.345,z,1.055,.045,.065,"637574")
                if z<0: box(xx+.58,2.03,z,1.05,1.04,.076,"9daeb0")
        for z in [-.80,.80]:
            box(.4,2.54,z,8.29,.08,.72,"71847e")
            box(.4,2.49,z+.27,8.27,.045,.033,BRASS)
        for x in [-4.82,4.88]:
            box(x,1.11,0,.12,.9,2.45,"8d9b96")
            box(x,2.02,0,.09,1.03,2.30,"99acaf")
        box(-4.82,2.02,0,.15,1.08,.08,METAL)
        for i in range(6):
            xx=-2.93+i*1.30
            for zz in [-.81,-.42,.44,.82]:
                box(xx,.95,zz,.63,.18,.33,"566e74")
                box(xx+.28,1.28,zz,.14,.71,.35,"526a72")
                box(xx+.27,1.60,zz,.16,.12,.355,"92a19a")
                for j in [-1,0,1]:
                    box(xx+.36,1.25,zz+j*.078,.006,.42,.013,"687c7b")
        for x in [-3.12,3.0]:
            for z in [-1.191,1.191]:
                rod((x,.46,z-.095),(x,.46,z+.095),.44,"2f3637",20)
                rod((x,.46,z-.103),(x,.46,z+.103),.25,"9eaaa6",20)
        for i in range(3):
            box(-4.17,.145+i*.19,1.36-i*.29,1.09,.10,.30,"677471")
            box(-4.17,.20+i*.19,1.509-i*.29,1.09,.025,.012,"d4bd81")
        for xx in [-4.77,-3.57]:
            rod((xx,.28,1.43),(xx,2.60,1.43),.044,BRASS)
            rod((xx,2.58,1.43),(xx,2.65,1.16),.041,BRASS)
        box(-4.17,2.65,1.30,1.32,.33,.16,"374946")
        text("PITTSBURGH",-4.17,2.64,1.39,.19,"f0dfad")
        box(.56,1.02,1.31,3.52,.30,.018,"c0c4b3")
        text("A L L E G H E N Y     C O A C H",.56,1.025,1.332,.17,"3f5356")
        # Cool horizon also fills apertures on the off-side of the bus.
        box(0,6.1,-19.1,150,13,.14,"b9cacc")
        box(0,7.02,28.1,160,15,.14,"c4d2d2")
        box(0,-.11,6,125,.20,48,SNOW)
        for x in [-6.55,-2.87,1.81]:
            box(x,.035,3.78,3.49,.08,2.0,"b4bab1")
        box(-6.38,1.63,2.82,.069,3.26,.08,"526865")
        box(-6.38,2.40,2.82,.97,.63,.065,"38565a")
        text("GATE  2",-6.38,2.4,2.86,.218,"e2dbc4")
        # Cab and stepwell. The driver's wheel and ribbed stair edges make
        # a closer boarding view legible between the two jambs.
        box(-4.52,1.38,-.43,.51,.20,1.10,"485956")
        rod((-4.46,1.41,-.44),(-4.36,1.71,-.40),.043,"4b554f")
        for j in range(15):
            a=j*2*pi/15; b=(j+1)*2*pi/15
            rod((-4.35+.18*cos(a),1.69+.08*sin(a),-.42+.15*sin(a)),
                (-4.35+.18*cos(b),1.69+.08*sin(b),-.42+.15*sin(b)),.020,INK,8)
        for z in [1.32,1.23]:
            rod((-4.66,.25,z),(-4.51,1.48,z-.51),.034,BRASS)
        for i in range(2):
            box(-4.77,1.66,.59+i*.29,.074,1.79,.27,"51635f")
            box(-4.72,1.84,.59+i*.29,.031,.96,.195,"9facaa")
        for i in range(3):
            for j in range(3):
                box(-4.17,.204+i*.19,1.30-i*.29+j*.054,.99,.013,.012,"86928b")
    with group("ExtRailHand","coach"):
        rod((.16,-.21,.64),(.089,-.045,.114),.075,"35414a",14,.064)
        rod((.091,-.045,.126),(.078,-.038,.075),.068,"49535a",14,.060)
        egg(.056,-.005,.045,.070,.080,.048,"3a4241",16)
        for j in range(4):
            yy=.037-j*.029
            rod((.068,yy,.072),(-.028,yy,.058),.015,"4a4e48",10,.014)
            rod((-.028,yy,.058),(-.048,yy,.014),.014,"474b45",10,.011)
        rod((.068,.038,-.005),(-.017,.065,-.023),.019,"434941",10,.015)
    with group("Boarding_platform","coach"):
        box(-9,.02,3.50,6.35,.085,1.51,"a7afa6")
        box(-9.21,3.25,2.41,5.37,.28,2.86,"74897f")
        for x in [-11.42,-7.29]:
            box(x,1.62,1.62,.12,3.24,.12,"697a72")
        for j in range(8):
            box(-10.86+j*.52,1.51,1.27,.50,2.81,.10,"98a8a0")
        for j in range(3):
            box(-10.44+j*1.19,2.12,1.345,.77,.91,.048,"c4c6ae")
        text("COACH   STATION",-9,2.91,1.345,.256,"ecdfbc")
        for xx in [-16,-10,0,5,10]:
            box(xx,2.3,-8,3.98,4.60,4.2,"949e95")
            box(xx,4.63,-8,4.08,.11,4.3,SNOW)
            for j in range(3):
                box(xx-1.24+j*1.16,3.50,-5.88,.56,.71,.08,"7d9090")
    with group("ExtScenery","coach"):
        for i in range(44):
            x=(i-21)*1.63
            bare_tree(x+rng.uniform(-.7,.7),rng.uniform(8,16),rng.uniform(2.1,5.5))
        for i in range(-4,5):
            x=i*9.1
            pole(x,0,6.58,.09,5.6,"726e5f",8,.055)
            box(x,5.17,6.58,1.63,.14,.12,"777564")
            rod((x,5.42,6.58),(x+9.1,5.42,6.58),.024,"68716c",5)
        for x in range(-30,40,5):
            egg(x,-.23,23,6.3,2.6,3.25,"99aaac",10,5)

def build_phone():
    with group("Terminal_shell","phone"):
        box(0,-.075,1,11,.15,8.9,"646e69")
        for x in range(-4,5):
            box(x,0,1,.009,.008,8.9,"828983")
        for z in range(-2,6):
            box(0,0,z,11,.008,.009,"828983")
        box(0,1.63,-.23,11,3.3,.22,"77877b")
        tilecols=["a7b3a5","aab4a6","9daea0","a4b1a3","b3bdac","aab6a8"]
        for i in range(-11,12):
            for j in range(12):
                if -4.29<i*.46<-1.30 and j*.275>1.00: continue
                box(i*.46,(j+.5)*.275,-.098,.454,.268,.062,rng.choice(tilecols))
        for x in [-4.26,-1.37]:
            box(x,2.15,-.044,.065,2.24,.083,METAL)
        box(-2.815,2.10,-.079,2.87,2.10,.048,"536e7b")
        for x in [-3.58,-2.79,-1.99]:
            box(x,2.13,-.039,.047,2.14,.09,"485d5b")
        box(-2.80,1.09,.005,3.02,.084,.20,"87938a")
        box(-2.80,2.20,-.03,2.91,.054,.10,"485d5b")
        for i in range(9):
            x=-4.0+i*.28
            h=rng.uniform(.16,.55)
            box(x,1.11+h/2,-.045,.25,h,.011,"405962")
            for j in range(2):
                if j*.105<h-.08:
                    box(x+.02,1.17+j*.105,-.035,.034,.028,.005,"d3ad6e")
        box(0,3.41,1.53,11,.20,8,"aab6a9")
        for x in [-2.0,1.38,4.0]:
            box(x,3.24,.54,1.91,.085,.24,"65766c")
            box(x,3.186,.54,1.81,.04,.15,"e5edbf")
        box(-1.63,2.70,.002,2.37,.31,.08,"384d48")
        text("PITTSBURGH   /   GATES", -1.63,2.699,.055,.187,"e1dfbf")
        bench(-2.35,2.71,2.67)
        # Aluminium backplate, handset hook, coin lever, twelve individual buttons.
        box(.13,1.59,.005,.76,1.34,.11,"3d4847")
        box(.13,1.66,.105,.683,1.050,.17,"a2aba3")
        box(.13,1.73,.199,.622,.89,.035,"7f8b85")
        box(.13,2.183,.19,.63,.18,.05,"425a60")
        text("Telephone",.13,2.185,.221,.126,"e6e5ce")
        box(.232,1.94,.231,.27,.12,.024,CREAM)
        text("LOCAL   25¢",.233,1.947,.25,.053,INK)
        box(-.08,1.958,.222,.154,.093,.022,"c5d0c3")
        text("DIAL   0",-.08,1.967,.238,.036,INK)
        for jj in range(2): box(-.08,1.938-jj*.009,.238,.105,.003,.001,"87958a")
        for jj in range(5):
            box(.40,1.67-jj*.041,.224,.024,.012,.008,"a7b0a4")
        box(.235,1.821,.228,.198,.039,.024,METAL)
        box(.235,1.83,.247,.113,.011,.016,"c9c9b7")
        for j in range(4):
            for i in range(3):
                x=.135+i*.1
                y=1.69-j*.091
                box(x,y,.239,.078,.067,.042,"cdd0bb")
                text("123456789*0#"[j*3+i],x,y,.265,.047,"364640")
        box(-.108,1.63,.245,.083,.48,.073,"394441")
        for yy in [1.53,1.78]:
            box(-.10,yy,.296,.102,.044,.1,"7a847c")
        for xx in [-.151,.375]:
            for yy in [1.27,2.05]:
                rod((xx,yy,.213),(xx,yy,.22),.017,"bcc2b4",8)
                box(xx,yy,.224,.018,.003,.002,METAL)
        box(.13,1.134,.192,.71,.211,.091,"677571")
        box(.258,1.153,.254,.194,.076,.026,"34453f")
        box(.13,.998,.235,.896,.053,.47,"909d92")
        box(.11,.911,.106,.66,.111,.29,"c5b987")
        box(.11,.969,.106,.66,.009,.29,"84794d")
        box(.313,.897,.17,.101,.024,.19,"dfc891")
        for i in range(7):
            x=.36+.031*i
            y=2.36+sin(i*1.1)*.012
            box(x,y,-.06,.033,.019,.013,"7f897d")
        # The slender armored cable describes a single sag to the caller's hand.
        curve=[(-.095,1.285,.28),(-.115,1.046,.36),(-.22,.995,.44),(-.38,1.075,.57),(-.51,1.282,.69),(-.565,1.433,.79),(-.592,1.485,.82)]
        for a,b in zip(curve,curve[1:]):
            rod(a,b,.0125,"69766d",9)
        for x in [-.7,.86]:
            box(x,3.07,-.043,1.35,.027,.065,"849285")
    with group("ExtReceiver","phone"):
        # Receiver has twin flared caps. The cord remains anchored low on the wall.
        rod((-.04,0,0),(.045,.30,-.035),.032,"2c3636",14,.040)
        egg(-.04,.016,.007,.058,.051,.057,"273231")
        egg(.048,.306,-.02,.067,.060,.064,"263030")
        rod((.049,.312,-.02),(.032,.315,.045),.052,"38413e",12)
        rod((-.041,.021,.003),(-.057,.02,.053),.047,"39413d",12)
        egg(-.015,.14,.038,.059,.084,.042,"c89677",18,10)
        egg(-.033,.195,.050,.035,.033,.030,"c58e72",14)
        rod((-.038,.116,.068),(.049,.194,.068),.018,"d29f80",12,.014)
        for i in range(4):
            rod((-.061,.084+i*.032,.055),(-.023,.086+i*.032,.084),.0155,"d1a082",12,.015)
            rod((-.023,.086+i*.032,.084),(.035,.094+i*.032,.070),.015,"ce9c7e",12,.013)
            egg(.029,.095+i*.032,.076,.010,.008,.005,"deb19a",8,5)
        rod((-.05,.038,.07),(-.16,-.11,.29),.059,"323f45",14,.075)
        rod((-.062,.025,.079),(-.074,.008,.098),.062,"a4a89a",12)
    with group("ExtPhoneRest","phone"):
        rod((.56,.94,.57),(.34,1.027,.37),.06,"344044",12,.048)
        egg(.304,1.033,.328,.062,.025,.077,"414842",12)
        for j in range(4):
            rod((.27+j*.021,1.026,.304),(.263+j*.021,1.022,.225+.008*abs(j-1)),.011,"454941",8,.009)

def produce():
    import stage
    for n in ["street","depot","coach","phone"]:
        stage.setroot(n)
    build_street()
    build_depot()
    build_coach()
    build_phone()
    nodes={}
    for child, parent in parents.items():
        nodes[child]=stage.group(child,parent=bpy.data.objects[parent])
    for (name,col),(vertices,faces) in parts.items():
        data=bpy.data.meshes.new(name+' '+col)
        data.from_pydata(vertices,[],faces)
        for index in smooth_faces[name,col]: data.polygons[index].use_smooth=True
        data.materials.append(stage.material(col))
        data.update()
        stage.attach(name+' '+col,data,(0,0,0),nodes[name])
    loaded={}
    for i,(name,s,x,y,z,h,c,align,font,rot) in enumerate(labels):
        obj=stage.label('painted legend '+str(i),s,(x,y,z),h,c,nodes[name])
        path=Path('/System/Library/Fonts/Supplemental')/font
        if path.exists():
            if font not in loaded: loaded[font]=bpy.data.fonts.load(str(path))
            obj.data.font=loaded[font]
        obj.data.align_x=align
        obj.data.resolution_u=2
    place={
        'ExtCamera':(-5.44,.145,1.54),'ExtWagon':(4.87,.02,3.75),
        'ExtSedan':(-7.38,.02,4.43),'ExtLap':(1.25,.077,1.13),
        'ExtReceiver':(-.59,1.49,.82)
    }
    for n,p in place.items(): nodes[n].location=stage.vec(p)
    root=bpy.data.objects['street']
    stage.actor('StreetRita',(-4.15,.13,.45),'rita',parent=root)
    stage.actor('StreetLarry',(-5.69,.13,1.42),'larry',parent=root)
    stage.actor('StreetNed',(.68,.13,.74),'ned',parent=root)
    stage.actor('StreetPhil',(-.38,.13,.79),'phil',parent=root)
    stage.finish('exteriors')

if __name__=='__main__':
    produce()
