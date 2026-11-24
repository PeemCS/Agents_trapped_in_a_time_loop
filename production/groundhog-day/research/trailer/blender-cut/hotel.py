"""Hearthside Hotel sets. All model-space coordinates are in metres, Y up."""
from stage import *
import bpy
import math
import random
from math import sin, cos, pi

rng = random.Random(6025)
WALNUT = '#613a31'
OAK = '#8e5944'
EDGE = '#b98258'
SHADOW = '#392630'
BRASS = '#c59b57'
GOLD = '#e3bd7b'
IVORY = '#e2cfaa'
GREEN = '#788675'
PINE = '#405e5b'
WINE = '#843e48'
PLUM = '#49333e'
CLOTH = '#8f5c62'
INK = '#292b35'
PAPER = '#efdcad'


def rot(node, y=0, x=0, z=0):
    node.rotation_euler = (math.radians(x), -math.radians(z), math.radians(y))
    return node


def material(hexcol):
    name='HotelColor'+hexcol.lstrip('#')
    m=bpy.data.materials.get(name)
    if m: return m
    m=bpy.data.materials.new(name)
    v=[int(hexcol[k:k+2],16)/255 for k in (1,3,5)]
    linear=[c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4 for c in v]
    m.diffuse_color=(*linear,1)
    m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*linear,1);bs.inputs['Roughness'].default_value=.82
    return m


class Surface:
    """Build decorative inlays and architectural surfaces as a single mesh."""
    def __init__(self):
        self.coords=[];self.faces=[];self.colors=[];self.palette=[]
    def face(self, coords, color):
        i=len(self.coords)
        self.coords.extend((x,-z,y) for x,y,z in coords)
        self.faces.append(tuple(range(i,i+len(coords))))
        if color not in self.palette:self.palette.append(color)
        self.colors.append(self.palette.index(color))
    def mesh(self,name,parent):
        m=bpy.data.meshes.new(name);m.from_pydata(self.coords,[],self.faces);m.update()
        for c in self.palette:m.materials.append(material(c))
        for poly,idx in zip(m.polygons,self.colors):poly.material_index=idx
        obj=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(obj);obj.parent=parent
        return obj


def arch(name,w,h,color,parent,z):
    r=w/2; cy=h-r
    pts=[(-r,0,z),(r,0,z),(r,cy,z)]+[(r*cos(i*pi/32),cy+r*sin(i*pi/32),z) for i in range(1,33)]
    f=Surface();f.face(pts,color);return f.mesh(name,parent)


def arcband(name,r,cy,thick,z,color,parent):
    mesh=Surface()
    for i in range(40):
        a=pi*i/40;b=pi*(i+1)/40
        mesh.face([((r+q)*cos(p),cy+(r+q)*sin(p),z) for p,q in [(a,0),(a,thick),(b,thick),(b,0)]],color)
    mesh.mesh(name,parent)


def trimwall(parent,w,h, color, bed=True):
    box('Wallpaper',(0,h/2,-.07),(w,h,.14),color,parent=parent)
    for y,d,t,c in [(0.075,.09,.15,WALNUT),(.19,.055,.035,EDGE),(.73,.035,.052,OAK),(.78,.045,.018,BRASS),(h-.12,.09,.095,OAK),(h-.06,.15,.045,IVORY),(h-.025,.21,.045,WALNUT)]:
        box('CarvedMoulding',(0,y,d*.35),(w,t,d),c,parent=parent)
    box('LowerPanel',(0,.405,.006),(w,.7,.019), PINE if bed else OAK,parent=parent)
    for i in range(max(1,round(w/.53))):
        cnt=max(1,round(w/.53));x=-w/2+w*(i+.5)/cnt
        box('PanelStile',(x,.41,.03),(.035,.61,.04),GREEN if bed else EDGE,parent=parent)
    if bed:
        f=Surface()
        for j in range(int(w/.17)):
            x=-w/2+(j+.5)*.17
            f.face([(x,.8,.005),(x+.008,.8,.005),(x+.008,h-.17,.005),(x,h-.17,.005)],'#b6a88b')
            for k in range(6):
                y=.98+k*.34+(j%2)*.16
                if y+.08>=h-.14:continue
                for sign in (-1,1):
                    f.face([(x,y,.009),(x+.040*sign,y+.027,.009),(x+.045*sign,y+.060,.009),(x+.012*sign,y+.042,.009)],'#a4977f')
                f.face([(x,y+.023,.009),(x+.016,y+.067,.009),(x,y+.099,.009),(x-.016,y+.067,.009)],'#b1997b')
        f.mesh('BlockPrintedWallpaper',parent)


def cornice_window(name,pos,yaw,width):
    w=width; h=2.18; parent=rot(group(name,pos),y=yaw)
    # Crown follows the arch, with a deep dark reveal and light stopping beads.
    arch(name+'Reveal',w+.16,h+.08,WALNUT,parent,.014)
    arch(name+'Glass',w,h,'#a6cbd2',parent,.025)
    r=w/2;cy=h-r
    lens=Surface()
    for i in range(19):
        xx=-r+(i+.5)*w/19
        skyh=cy+math.sqrt(max(0,r*r-xx*xx))
        for k in range(3):
            y=skyh*(.12+.27*k)+.035*sin(i*.77)
            hh=.025+rng.random()*.06
            lens.face([(xx-.027,y,.029),(xx+.009,y+.013,.029),(xx+.04,y+hh,.029),(xx+.004,y+hh*.67,.029)],'#cce0d9')
        # Print the distant pine silhouettes into the milky lower panes.
        v=.22+.22*(.5+.5*sin(i*.83));wide=w/18
        lens.face([(xx-wide,0,.031),(xx+wide,0,.031),(xx,v,.031)],'#8aaeb4')
    lens.mesh(name+'Frost',parent)
    arcband(name+'ArchedCasing',r,cy,.075,.058,IVORY,parent)
    arcband(name+'ArchBead',r+.067,cy,.021,.072,EDGE,parent)
    for x in [-r,r]:box('Jamb',(x,cy/2,.065),(.068,cy,.09),IVORY,parent=parent)
    for x in [-w/6,w/6]:
        top=cy+math.sqrt(max(0,r*r-x*x))
        box('Muntin',(x,top/2,.065),(.022,top,.04),'#ece1c6',parent=parent)
    for y in [.51,1.04,cy]:box('GlazingBar',(0,y,.069),(w,.023,.045),IVORY,parent=parent)
    for a in [pi/4,pi/2,3*pi/4]:
        rod('FanlightSpoke',(0,cy,.065),(r*cos(a),cy+r*sin(a),.065),.014,IVORY,parent=parent)
    box('DeepWindowSill',(0,-.035,.072),(w+.25,.10,.28),EDGE,.018,parent=parent)


def drape(name,x,y,z,width,height,yaw=0):
    node=rot(group(name,(x,y,z)),y=yaw)
    f=Surface();n=42
    def pt(i,j):
        t=i/n;v=j/10; wave=sin(t*pi*11+.09*sin(v*pi))
        return ((t-.5)*width+.018*sin(pi*v)*wave,height*(1-v)-.023*v*(.5+.5*wave),.08*wave+.026*v*cos(t*pi*6))
    for i in range(n):
        for j in range(10):
            c=['#673d45','#764650','#86515a','#995e62','#ad7774'][int((1+sin((i+.5)/n*pi*11))*.5*4.99)]
            f.face([pt(i,j+1),pt(i+1,j+1),pt(i+1,j),pt(i,j)],c)
    f.mesh(name+'Velvet',node)
    for i in range(7):
        x0=width*((i+.5)/7-.5)
        box('CurtainTab',(x0,height+.022,0),(.04,.075,.035),BRASS,parent=node)
    return node


def legtable(name,pos,w,d,h,parent=None):
    n=group(name,pos,parent=parent)
    box('Apron',(0,h-.13,0),(w-.06,.22,d-.06),OAK,.012,n)
    box('BeadedTableTop',(0,h+.005,0),(w+.035,.075,d+.035),EDGE,.015,n)
    box('TableTop',(0,h+.047,0),(w+.06,.05,d+.06),WALNUT,.011,n)
    for x in [-w*.42,w*.42]:
        for z in [-d*.39,d*.39]:
            rod('TurnedLeg',(x,.035,z),(x,h-.19,z),.035,OAK,parent=n)
            for y,diam in [(.07,.085),(.20,.10),(h-.30,.10)]:ball('LatheBead',(x,y,z),(diam,.08,diam),EDGE,parent=n)
    return n


def lamp(name,pos,parent):
    n=group(name,pos,parent=parent)
    ball('LampFoot',(0,.028,0),(.27,.055,.27),BRASS,parent=n)
    rod('LampStem',(0,.03,0),(0,.42,0),.028,BRASS,parent=n)
    ball('LampBulbBase',(0,.17,0),(.18,.22,.18),'#a96c50',parent=n)
    for y,r in [(.045,.075),(.285,.054),(.33,.035)]:ball('LampCollar',(0,y,0),(2*r,.025,2*r),GOLD,parent=n)
    shade=Surface();nseg=48
    for i in range(nseg):
        points=[]
        for y,r,j in [(.36,.25,i),(.36,.25,i+1),(.73,.135,i+1),(.73,.135,i)]:
            a=j*2*pi/nseg;rf=r*(1 if j%2 else .966);points.append((rf*sin(a),y,rf*cos(a)))
        shade.face(points,'#f9d09b' if i%2==0 else '#e3ae81')
    shade.mesh(name+'PleatedSilk',n)
    for y,r in [(.36,.25),(.73,.135)]:
        for i in range(24):
            a=i*2*pi/24;b=(i+1)*2*pi/24
            rod('LampBiasTrim',(r*sin(a),y,r*cos(a)),(r*sin(b),y,r*cos(b)),.007,OAK,parent=n)
    ball('LampFinial',(0,.755,0),(.035,.052,.035),BRASS,parent=n)


def night_clock(pos):
    n=rot(group('AlarmRadio',pos),y=-82)
    box('ClockHousing',(0,.125,0),(.49,.232,.225),'#382e30',.028,n)
    box('WoodgrainSleeve',(0,.13,-.033),(.505,.222,.171),'#794c38',.02,n)
    box('FacePlate',(0,.123,.115),(.465,.17,.017),'#292929',.009,n)
    for i,(x,digit) in enumerate([(-.164,'6'),(-.092,':'),(-.023,'0'),(.055,'0')]):
        if digit!=':':box('SplitFlapHousing',(x,.131,.128),(.078,.105,.013),'#11151b',.003,n)
        label('ClockNumeral',digit,(x,.118,.139),.096,'#fff4db',parent=n)
        if digit!=':':box('SplitLine',(x,.13,.142),(.073,.003,.002),'#504d48',parent=n)
    for i in range(9):box('TuningScale',(.119+i*.011,.15,.128),(.002,.017 if i%2 else .032,.003),IVORY,parent=n)
    box('RadioNeedle',(.165,.143,.134),(.005,.045,.003),'#e98c51',parent=n)
    for i in range(15):box('SpeakerSlot',(-.177+i*.024,.244,-.012),(.009,.004,.128),'#291e20',.001,n)
    box('SnoozeLever',(.018,.254,.071),(.166,.018,.038),'#3d3c3b',.005,n)
    label('ClockMark','FM  /  AM',(.157,.089,.13),.015,'#d2b991',parent=n)
    for x in [-.179,.179]:box('ClockFoot',(x,.012,0),(.05,.024,.13),INK,parent=n)
    return n


def bed_quilt(parent):
    f=Surface();xs=[-1.00+i*2/48 for i in range(49)];zs=[-.91+i*2.02/42 for i in range(43)]
    def h(x,z):
        drop=max(0,abs(x)-.82)*1.0+max(0,-.76-z)*.85
        return .765-drop+.025*cos(x*7+z*2.5)+.015*sin(z*18+x*4)+.058*math.exp(-((z+.47)/.34)**2)*cos(x*4)**2
    colors=['#7f5058','#b67d71','#728a88','#cdb292','#ab8c83','#7f787f']
    for i in range(48):
        for j in range(42):
            ax=i//6;az=j//6;ii=i%6;jj=j%6
            col=colors[(ax*3+az+(ii+jj>=6)*2)%len(colors)]
            corners=[(xs[k],h(xs[k],zs[l]),zs[l]) for k,l in [(i,j+1),(i+1,j+1),(i+1,j),(i,j)]]
            f.face(corners,col)
            if j%6==0 and i%2==0:
                x=xs[i]+.007;z=zs[j]+.008
                f.face([(xx,h(xx,zz)+.002,zz) for xx,zz in [(x,z+.003),(x+.018,z+.003),(x+.018,z),(x,z)]],IVORY)
    f.mesh('HandPiecedQuilt',parent)


def hand(name,pos,side,parent=None,coat=True):
    """An articulated hand directed toward local -Z, attached at the wrist."""
    n=group(name,pos,parent=parent);sgn=1 if side=='R' else -1
    skin='#c18c71';skinlight='#daab87'
    if name not in ('ReachClock','CurtainHandL','CurtainHandR'):
        rod('CoatSleeve',(0,-.014,.37),(0,0,.05),.071,'#343641' if coat else '#a2a4a2',parent=n)
    rod('SleeveCuff',(0,0,.07),(0,0,.029),.074,'#4c5059' if coat else '#d9d6c5',parent=n)
    if side=='L':
        rod('Watchband',(0,.002,.023),(0,.002,.044),.066,'#6f625b',parent=n)
        ball('WatchCrystal',(0,.059,.032),(.065,.017,.055),'#b1c9cd',parent=n)
    ball('Palm',(0,.001,-.032),(.137,.071,.152),skin,parent=n)
    for i,(xx,ll) in enumerate([(-.048,.090),(-.018,.101),(.015,.095),(.045,.074)]):
        x=xx*sgn
        a=(x,.001,-.079);b=(x*1.07,.002,-.079-ll*.55);c=(x*1.1,-.007,-.079-ll)
        rod('Finger',a,b,.016,skin,parent=n);rod('Fingertip',b,c,.014,skinlight,parent=n);ball('Knuckle',b,(.032,.033,.032),skin,parent=n)
    a=(-sgn*.050,-.004,-.012);b=(-sgn*.080,-.004,-.043);c=(-sgn*.085,-.012,-.082)
    rod('Thumb',a,b,.024,skin,parent=n);rod('ThumbEnd',b,c,.019,skinlight,parent=n)
    return n


def floorboards(name,w,d,parent):
    f=Surface();cols=['#735448','#6b4c40','#866453','#795a49','#805c49'];n=round(w/.17)
    for i in range(n):
        x0=-w/2+i*w/n;x1=x0+w/n-.007;z=-d/2
        while z<d/2-.001:
            z1=min(d/2,z+rng.uniform(.63,1.35));c=rng.choice(cols)
            f.face([(x0,0,z1),(x1,0,z1),(x1,0,z+.004),(x0,0,z+.004)],c)
            if z1-z>.24:
                xx=rng.uniform(x0+.02,x1-.02);zz=z+.07
                f.face([(xx,.001,zz),(xx+.006,.001,zz+.007),(xx+.008,.001,zz+.147),(xx+.002,.001,zz+.12)],'#664b42')
            z=z1
    f.mesh(name,parent)


def rug(name,pos,w,d,parent):
    n=group(name,pos,parent=parent)
    for i,c in enumerate([PLUM,'#c8a074','#7d424a','#ae775c','#536565','#954f55']):
        box('WovenBorder',(0,.004+i*.001,0),(w-i*.047,.007,d-i*.047),c,parent=n)
    f=Surface();nx=max(3,round(w/.35));nz=max(3,round(d/.35))
    for i in range(nx):
        for j in range(nz):
            x=(i+.5-nx/2)*(w-.25)/nx;z=(j+.5-nz/2)*(d-.25)/nz;r=.052
            for scale,c in [(1,'#bd9073'),(.55,'#713e48')]:
                p=r*scale;y=.011+.003*(1-scale)
                f.face([(x,y,z-p*1.3),(x-p,y,z),(x,y,z+p*1.3),(x+p,y,z)],c)
    f.mesh('WovenDiamonds',n)
    for sign in [-1,1]:
        for j in range(26):
            x=(j+.5-13)*(w-.05)/26;z=sign*(d/2+.033)
            box('WovenFringe',(x,.004,z),(.016,.008,.066),IVORY,parent=n)


def picture(name,pos,yaw,w,h,parent=None):
    n=rot(group(name,pos,parent=parent),y=yaw)
    box('GildedFrame',(0,0,0),(w,h,.055),OAK,.015,n)
    box('GoldFillet',(0,0,.032),(w-.025,h-.025,.016),GOLD,.005,n)
    box('LinenMat',(0,0,.043),(w-.055,h-.055,.014),IVORY,parent=n)
    ww=(w-.13)/2;hh=(h-.13)/2;f=Surface()
    f.face([(-ww,-hh,.055),(ww,-hh,.055),(ww,hh,.055),(-ww,hh,.055)],'#9cb4ac')
    for k,(c,v) in enumerate([('#87988c',.14),('#69847e',.00),('#455f61',-.33)]):
        for j in range(16):
            x0=-ww+2*ww*j/16;x1=-ww+2*ww*(j+1)/16
            def top(i):return hh*(v+.23*sin(i*.65+k)+.1*cos(i*.32+k))
            f.face([(x0,-hh,.056+k*.001),(x1,-hh,.056+k*.001),(x1,top(j+1),.056+k*.001),(x0,top(j),.056+k*.001)],c)
    f.mesh(name+'Print',n)


def flowers(pos,parent):
    v=group('RoseBottle',pos,parent=parent)
    ball('Bottle',(0,.09,0),(.12,.18,.12),'#759394',parent=v)
    rod('BottleNeck',(0,.13,0),(0,.20,0),.03,'#809c9b',parent=v)
    for i in range(4):
        a=i*2.25;x=.09*cos(a);z=.06*sin(a);y=.31+.035*cos(a*.65)
        rod('FlowerStem',(0,.14,0),(x,y,z),.005,'#64725b',parent=v)
        for q in range(5):
            t=q*2*pi/5;ball('RosePetal',(x+.019*cos(t),y+.004*sin(t),z+.019*sin(t)),(.043,.032,.04),['#bc807b','#b16c70','#d49688'][i%3],parent=v)
        ball('RoseHeart',(x,y+.013,z),(.026,.026,.026),'#985765',parent=v)


def make_bedroom():
    setroot('bedroom');world=group('BedroomArchitecture');height=3.04
    floorboards('VintageOakFloor',5.35,5.4,world)
    box('PlasterCeiling',(0,height+.042,0),(5.44,.07,5.53),'#c6bcaa',parent=world)
    # Shallow three-sided bay; the centre window directly faces the sleeper.
    center=group('BedNorthWall',(0,0,-2.62),world);trimwall(center,2.34,height,'#c8b99f')
    for side in [-1,1]:
        wing=rot(group('BedBayWing',(side*1.9,0,-2.22),world),y=-side*29)
        trimwall(wing,1.72,height,'#c4b59b')
    for s in [-1,1]:
        n=rot(group('SideWall',(s*2.65,0,.43),world),y=-s*90);trimwall(n,4.64,height,'#c3b19a')
    sw=rot(group('SouthWall',(0,0,2.73),world),y=180);trimwall(sw,5.4,height,'#bfae9a')
    cornice_window('BayCenter',(0,.58,-2.59),0,1.72)
    cornice_window('BayLeft',(-1.86,.58,-2.18),29,1.08)
    cornice_window('BayRight',(1.86,.58,-2.18),-29,1.08)
    for s in [-1,1]:
        drape('SideDrape'+str(s),s*2.40,.39,-1.74,.45,2.38,-s*29)
        drape('DrawCurtain'+('L' if s<0 else 'R'),s*1.04,.36,-2.36,.39,2.45)
    rod('CurtainPole',(-1.35,2.85,-2.37),(1.35,2.85,-2.37),.023,BRASS,parent=world)
    for x in [-1.37,1.37]:ball('PoleFinial',(x,2.85,-2.37),(.084,.084,.084),GOLD,parent=world)
    # Victorian steam radiator, bottom return pipe and valve under the middle bay.
    box('RadiatorFeet',(0,.087,-2.32),(1.06,.09,.19),'#4f625e',.015,world)
    for i in range(15):box('CastIronFin',((i-7)*.073,.295,-2.32),(.056,.427,.162),'#7a9089',.024,world)
    for y in [.13,.45]:rod('RadiatorPipe',(-.57,y,-2.32),(.57,y,-2.32),.024,'#788981',parent=world)
    rod('ReturnValve',(.55,.14,-2.32),(.66,.14,-2.32),.022,BRASS,parent=world)
    # Wainscot, east dresser and the hall door on the west wall stay fixed on every Tuesday.
    door=rot(group('HallDoor',(-2.59,0,1.33),world),y=90)
    box('DoorCasing',(0,1.15,0),(1.13,2.30,.10),EDGE,.015,door)
    box('DoorSlab',(0,1.10,.062),(.99,2.20,.045),WALNUT,.012,door)
    for x in [-.22,.22]:
        for y,h in [(.55,.72),(1.55,.85)]:
            box('RaisedDoorPanel',(x,y,.10),(.34,h,.025),OAK,.015,door)
            box('DoorRecess',(x,y,.12),(.28,h-.07,.013),'#70483d',.009,door)
    box('LatchPlate',(.35,.96,.105),(.07,.17,.018),BRASS,.012,door);ball('Knob',(.35,.965,.15),(.075,.075,.07),GOLD,parent=door)
    dress=rot(group('Dresser',(2.29,0,-.6),world),y=-90)
    box('DresserCase',(0,.43,0),(1.05,.81,.46),WALNUT,.022,dress)
    for i in range(3):
        box('DrawerFront',(0,.20+i*.237,.24),(.963,.206,.04),OAK,.010,dress)
        for x in [-.29,.29]:ball('DrawerPull',(x,.20+i*.237,.277),(.042,.037,.029),GOLD,parent=dress)
    box('DresserTop',(0,.86,0),(1.12,.071,.52),EDGE,.015,dress)
    picture('WinterLandscape',(2.57,1.68,-.6),-90,.91,.70,world)
    picture('SmallLandscape',(-2.56,1.74,-.44),90,.66,.48,world)
    bed=group('MahoganyBed',(-.22,0,.99),world)
    box('BedBase',(0,.40,.14),(1.87,.25,2.58),WALNUT,.04,bed)
    for xx in [-.875,.875]:
        for zz in [-1.04,1.35]:
            box('BedLeg',(xx,.23,zz),(.11,.46,.12),WALNUT,.014,bed)
    box('Mattress',(0,.61,.13),(1.835,.26,2.5),'#c5b9a3',.080,bed)
    box('BedHead',(0,1.05,1.37),(1.98,.97,.091),WALNUT,.03,bed)
    for xx in [-.91,.91]:
        rod('HeadPost',(xx,.47,1.36),(xx,1.63,1.36),.052,EDGE,parent=bed)
        ball('HeadFinial',(xx,1.68,1.36),(.15,.19,.15),WALNUT,parent=bed)
    hdr=Surface()
    for i in range(44):
        x0=(i/44-.5)*1.82;x1=((i+1)/44-.5)*1.82
        def hh(x):return 1.47+.24*(.5+.5*cos(x*pi/.9))+.035*cos(x*18)
        hdr.face([(x0,1.40,1.301),(x1,1.40,1.301),(x1,hh(x1),1.301),(x0,hh(x0),1.301)],OAK)
    hdr.mesh('ScallopedHeadboard',bed)
    for x in [-.45,.45]:
        b=box('Pillow',(x,.78,1.06),(.82,.19,.43),'#d4c6b2',.084,bed);rot(b,x=7)
    bed_quilt(bed)
    rug('BedroomCarpet',(-1.59,.012,.28),.72,1.85,world)
    stand=legtable('Nightstand',(1.39,0,1.91),.81,.66,.76,world)
    box('DrawerFront',(0,.621,-.337),(.66,.14,.022),OAK,.007,stand);ball('DrawerPull',(0,.632,-.37),(.045,.045,.035),BRASS,parent=stand)
    night_clock((1.12,.849,1.73));lamp('BedLamp',(1.62,.832,2.08),world);flowers((1.62,.832,1.72),world)
    for s in [-1,1]:hand('BedHand'+('L' if s<0 else 'R'),(-.22+s*.31,.83,1.59),'L' if s<0 else 'R',coat=False)
    hand('ReachClock',(.28,.94,1.61),'R',coat=False)
    for side,x in [('L',-.37),('R',.37)]:hand('CurtainHand'+side,(x,1.58,-1.94),side)
    actor('BedPhil',(-.22,.91,1.9),'phil','stand')
    seated=actor('ShoePhil',(-1.02,.17,.9),'phil','sit')
    torso=group('ShoeTorso',(0,.54,0),seated)
    for piece in list(seated.children):
        if piece != torso and not piece.name.startswith('ShoePhil.leg'):
            piece.parent=torso;piece.location.z-=.54
    for name,color in [('ReachClockBridge','#a2a4a2'),('CurtainHandLBridge','#343641'),('CurtainHandRBridge','#343641')]:
        rod(name,(0,0,0),(0,1,0),.069,color)

    # Pocket insert: coat panels and hank of burgundy scarf closest to the camera.
    pocket=group('PocketInsert',(0,1.07,.80));rot(pocket,x=12)
    sewing=Surface()
    def clothpoly(pts,c,z):sewing.face([(x,y,z+.014*cos(x*5)*sin(y*8)) for x,y in pts],c)
    clothpoly([(-.48,-.43),(.45,-.42),(.46,.16),(.32,.25),(.15,.30),(-.17,.29),(-.36,.24),(-.47,.10)],'#39434d',.045)
    clothpoly([(-.43,-.42),(-.18,-.38),(-.046,-.07),(-.19,.25),(-.37,.22)],'#49535c',.055)
    clothpoly([(.01,-.40),(.39,-.41),(.43,.10),(.16,.26),(-.015,.22)],'#414b55',.057)
    clothpoly([(-.18,.25),(-.07,.26),(.006,-.09),(-.22,.062),(-.177,.092),(-.25,.104)],'#71808a',.084)
    clothpoly([(.08,.26),(.19,.24),(.23,.091),(.16,.083),(.182,.054),(-.018,-.081)],'#65717a',.09)
    clothpoly([(-.12,.256),(-.032,.29),(.078,.227),(.01,-.124),(-.058,-.255),(-.109,-.182)],'#864952',.093)
    for i in range(9):
        y=.16-i*.035;x=-.066-.012*sin(i*.4)
        clothpoly([(x-.023,y),(x+.035,y+.008),(x+.038,y+.003),(x-.02,y-.005)],'#a66a70',.095)
    for i in range(13):
        y=.18-i*.036
        clothpoly([(.31,y),(.315,y+.002),(.31,y+.016),(.306,y+.015)],'#8b8983',.072)
    sewing.mesh('TailoredPocketInsert',pocket)
    for y in [-.14,-.28]:ball('CoatButton',(-.018,y,.072),(.030,.030,.012),'#ac9577',parent=pocket)
    rot(box('PocketWelt',(.15,-.02,.116),(.20,.03,.027),'#65717a',.004,pocket),z=-12)
    bill('PocketBill',(.15,.055,.136),pocket,.50)
    hand('PocketHand',(.25,1.04,1.12),'R')


def bill(name,pos,parent,scale=1):
    n=group(name,pos,parent=parent);n.scale=(scale,scale,scale)
    box('PaperMoney',(0,0,0),(.26,.115,.006),'#aec3a1',.002,n)
    for x in [-.121,.121]:box('CurrencyBorder',(x,0,.004),(.002,.102,.001),'#617d68',parent=n)
    for y in [-.05,.05]:box('CurrencyBorder',(0,y,.004),(.242,.002,.001),'#617d68',parent=n)
    ball('MoneyPortrait',(0,0,.005),(.055,.079,.005),'#74977f',parent=n)
    ball('EngravedHead',(.003,.008,.009),(.024,.033,.004),'#bac7a8',parent=n)
    for x in [-.094,.094]:label('Denomination','5',(x,-.001,.008),.038,'#446552',parent=n)
    label('BankName','FEDERAL RESERVE NOTE',(0,.039,.009),.009,'#45664e',parent=n)
    label('BankSerial','B  11649317  A',(.061,-.032,.009),.008,'#496c54',parent=n)
    return n


def couch_chair(name,pos,parent):
    n=rot(group(name,pos,parent=parent),y=85)
    for x in [-.25,.25]:
        for z in [-.23,.23]:rod('UpholsteryLeg',(x,.02,z),(x,.24,z),.036,WALNUT,parent=n)
    box('Seat',(0,.31,0),(.70,.22,.66),'#516d63',.08,n)
    back=box('TuftedBack',(0,.62,-.27),(.69,.65,.19),'#506b64',.08,n);rot(back,x=-6)
    for x in [-.29,.29]:box('ArmRest',(x,.49,.015),(.15,.34,.57),'#60796c',.055,n)
    for x in [-.15,0,.15]:
        for y in [.53,.74]:ball('UpholsteryButton',(x,y,-.159),(.025,.025,.013),'#998b6d',parent=n)


def make_lobby():
    setroot('lobby');world=group('LobbyArchitecture');h=3.35
    # Pale and umber octagonal encaustic floor; little diamond tile at each joint.
    tile=Surface();s=.355
    for col in range(20):
        for row in range(19):
            x=(col-10)*s;z=(row-9.5)*s;cut=.058
            tile.face([(x+a,.002,z+b) for a,b in [(cut,s),(s-cut,s),(s,s-cut),(s,cut),(s-cut,0),(cut,0),(0,cut),(0,s-cut)]],rng.choice(['#c7b69e','#d0bea5','#c6b59d','#c6b79e']))
            tile.face([(x,.003,z-cut),(x-cut,.003,z),(x,.003,z+cut),(x+cut,.003,z)],'#776e61')
    tile.mesh('EncausticFloor',world)
    box('FloorGrout',(0,-.028,0),(7.2,.05,7),'#9a8b79',parent=world)
    box('CoiffedCeiling',(0,h+.05,0),(7.1,.10,6.65),'#d1bf9e',parent=world)
    for x in [-2.02,0,2.02]:box('CeilingRib',(x,h-.04,0),(.12,.085,6.7),OAK,.015,world)
    for z in [-1.68,0,1.68]:box('CrossBeam',(0,h-.045,z),(7.0,.095,.13),OAK,.015,world)
    for x,z,yaw,width in [(0,-3.28,0,7.0),(0,3.28,180,7.0),(-3.50,0,90,6.60),(3.50,0,-90,6.60)]:
        n=rot(group('LobbyWall',(x,0,z),world),y=yaw);trimwall(n,width,h,'#acaa8a',bed=False)
    south=rot(group('Vestibule',(0,0,3.19),world),y=180)
    box('VestibuleCase',(0,1.31,-.01),(2.11,2.62,.10),EDGE,.022,south)
    for x in [-.46,.46]:
        box('DoorStile',(x,1.22,.053),(.90,2.43,.09),WALNUT,.012,south)
        box('LeadGlass',(x,1.51,.104),(.72,1.55,.024),'#a5bcc1',parent=south)
        box('DoorKickPlate',(x,.22,.116),(.68,.23,.02),BRASS,.004,south)
        for y in [.98,1.78,2.10]:box('VestibuleGlazingBar',(x,y,.134),(.73,.027,.04),OAK,parent=south)
        for dx in [-.142,.142]:box('VestibuleMuntin',(x+dx,1.50,.134),(.018,1.54,.04),OAK,parent=south)
        box('DoorPushPlate',(x+(-.29 if x>0 else .29),1.0,.151),(.059,.25,.02),GOLD,.005,south)
    label('TransomName','HEARTHSIDE',(0,2.51,.073),.124,PAPER,parent=south)
    # A small street silhouette lies beyond the glass, drawn behind the glazing bars.
    transom=Surface()
    for side in [-1,1]:
        for i in range(6):
            x=side*.46-.31+i*.11;hh=.83+.10*(1+sin(i*1.35))
            transom.face([(x,.75,.12),(x+.10,.75,.12),(x+.10,hh,.12),(x+.043,hh+.09,.12),(x,hh,.12)],'#7f989e')
    transom.mesh('SnowStreetInGlass',south)
    # NW stairs and cast balusters.
    for i in range(12):
        y=.12*(i+1);z=-.98-i*.175
        box('StairRiser',(-2.45,y/2,z),(1.27,y,.19),WALNUT,parent=world)
        box('StairNosing',(-2.45,y+.004,z+.006),(1.31,.034,.21),OAK,.008,world)
        box('StairRunner',(-2.45,y+.025,z+.01),(.68,.011,.19),WINE,parent=world)
        for x in [-2.79,-2.11]:box('RunnerStripe',(x,y+.034,z+.01),(.016,.005,.19),GOLD,parent=world)
        if i%2==0:
            rod('StairSpindle',(-1.81,y,z),(-1.81,y+.78,z),.021,OAK,parent=world)
            ball('StairBead',(-1.81,y+.43,z),(.077,.16,.077),EDGE,parent=world)
    rod('Handrail',(-1.81,.89,-.90),(-1.81,2.27,-3.11),.043,EDGE,parent=world)
    for x,z,y in [(-1.81,-.90,0),(-1.81,-3.11,1.38)]:
        box('NewelPost',(x,y+.47,z),(.13,.94,.13),WALNUT,.012,world)
        ball('NewelFinial',(x,y+.98,z),(.18,.18,.18),EDGE,parent=world)
    couch_chair('ArmchairOne',(-2.83,0,.43),world);couch_chair('ArmchairTwo',(-2.84,0,1.72),world)
    small=legtable('TeaTable',(-2.83,0,1.07),.52,.48,.53,world);flowers((0,.60,0),small)
    for i,(x,z,yaw) in enumerate([(-3.41,.12,90),(-3.41,1.42,90),(1.19,-3.19,0)]):
        picture('LobbyChromolithograph'+str(i),(x,1.68,z),yaw,.76,.56,world)
    rug('LobbyRunner',(-.28,.014,.13),1.52,4.19,world)
    desk=rot(group('ReceptionCounter',(2.15,0,-.48),world),y=-90)
    box('CarvedDeskCase',(0,.53,0),(3.55,1.04,.87),WALNUT,.025,desk)
    for i in range(6):
        x=(i-2.5)*.57
        box('PanelFrame',(x,.56,.446),(.52,.66,.03),EDGE,.013,desk)
        box('PanelRecess',(x,.56,.465),(.48,.61,.025),OAK,.012,desk)
        box('RaisedPanel',(x,.56,.484),(.39,.52,.018),'#84503b',.015,desk)
    for y in [.085,.94,1.005]:box('CounterRail',(0,y,.447),(3.60,.06,.10),EDGE,.014,desk)
    box('CounterLip',(0,1.075,0),(3.69,.088,1.02),EDGE,.02,desk)
    box('CounterTop',(0,1.125,0),(3.73,.054,1.06),'#67443a',.016,desk)
    # Guest book, ruled pages and a brass bell.
    book=rot(group('GuestBook',(.49,1.16,.04),desk),y=-8)
    box('LedgerBinding',(0,.014,0),(.61,.027,.36),WINE,.006,book)
    for sign in [-1,1]:
        box('LedgerLeaf',(sign*.139,.034,0),(.265,.022,.327),PAPER,.004,book)
        for i in range(9):box('LedgerRule',(sign*.14,.047,-.112+i*.029),(.22,.001,.0015),'#ad9c78',parent=book)
        for i in [2,4,6]:box('RegisterEntry',(sign*.148,.049,-.117+i*.029),(.126,.001,.005),'#80745e',parent=book)
    bell=group('DeskBell',(-.13,1.156,-.17),desk)
    ball('BellBase',(0,.015,0),(.15,.035,.15),'#52443e',parent=bell)
    ball('BellDome',(0,.055,0),(.12,.093,.12),GOLD,parent=bell)
    rod('BellButton',(0,.083,0),(0,.118,0),.011,BRASS,parent=bell)
    ball('BellPlunger',(0,.119,0),(.043,.018,.043),GOLD,parent=bell)
    # Guest-facing bank of 24 wood cubbies, individual keys and brass tags.
    rack=rot(group('KeyRack',(3.41,1.69,-.65),world),y=-90)
    box('Pigeonholes',(0,0,0),(2.12,1.15,.12),WALNUT,.03,rack)
    for i in range(8):
        for j in range(3):
            x=(i-3.5)*.246;y=(j-1)*.33
            box('CubbyRecess',(x,y,.067),(.216,.284,.02),'#463731',.008,rack)
            box('BrassNumber',(x,y-.097,.082),(.114,.045,.015),GOLD,.003,rack)
            label('RoomNumber',str(201+i+j*8),(x,y-.096,.093),.029,'#53432f',parent=rack)
            if (i+j*2)%4:
                rod('RoomKey',(x,y+.115,.098),(x+.024,y-.007,.099),.007,BRASS,parent=rack)
                ball('KeyFob',(x+.024,y+.001,.099),(.043,.065,.011),'#9b6d51',parent=rack)
    label('HotelWallName','H E A R T H S I D E',(0,.785,.117),.174,PLUM,parent=rack)
    label('HotelWallSub','H  O  T  E  L',(0,.601,.117),.076,PLUM,parent=rack)
    # Two sconces flank the rack on the office side.
    for z in [-2.17,.88]:
        lampbase=rot(group('LobbySconce',(3.40,1.66,z),world),y=-90)
        ball('Backplate',(0,0,0),(.17,.27,.067),BRASS,parent=lampbase)
        rod('SconceBracket',(0,0,0),(0,.042,.15),.025,BRASS,parent=lampbase)
        ball('MilkGlassShade',(0,.15,.16),(.19,.28,.18),'#f3d09c',parent=lampbase)
    # Work envelope, peeled banknote and separate punched ticket, each independently animated.
    env=rot(group('FareEnvelope',(1.96,1.170,.39)),y=-91,x=-90)
    box('EnvelopeStock',(0,0,0),(.395,.206,.008),'#ceac77',.003,env)
    f=Surface();f.face([(-.193,.098,.005),(.193,.098,.005),(0,.013,.006)],'#bc9563');f.mesh('EnvelopeFlap',env)
    for x,y in [(-.149,-.050),(.143,-.050)]:box('EnvelopeEmDash',(x,y,.007),(.031,.004,.002),WALNUT,parent=env)
    label('EnvelopeOwner','CREW FARES',(0,.000,.009),.039,'#4b403a',parent=env)
    label('EnvelopeReturn','RETURN  /  WED.',(0,-.071,.009),.018,'#67513f',parent=env)
    n=bill('FareCash',(1.997,1.179,.375),None);rot(n,y=-91,x=-90)
    # Ticket shown toward Phil; opposed tricolour bands keep it distinct from green fare cash.
    ticket=group('PaidTicket',(.95,1.28,.44));box('TicketStock',(0,0,0),(.226,.104,.005),'#edd3a0',.003,ticket)
    for yy in [-.042,.044]:box('TicketStripe',(0,yy,.004),(.213,.009,.002),WINE,parent=ticket)
    label('TicketText','PITTSBURGH',(0,.012,.006),.023,PLUM,parent=ticket)
    label('TicketMark','ONE WAY     |     PAID',(0,-.018,.006),.012,PLUM,parent=ticket)
    ball('Punch',(.088,.028,.006),(.013,.013,.004),INK,parent=ticket)
    hand('FareLeft',(1.23,1.21,.46),'L');hand('FareRight',(1.33,1.24,.44),'R');hand('LobbyGreetingHand',(-1.11,1.29,-.53),'L')
    actor('LobbyRita',(0,0,1.77),'rita');actor('LobbyLarry',(-.66,0,2.36),'larry');actor('LobbyNed',(-.24,0,.14),'ned')
    case=group('LarryCase',(-.37,.62,2.40));box('CameraCase',(0,0,0),(.46,.30,.25),INK,.028,case)
    for x in [-.14,.14]:box('CaseLatch',(x,.054,.13),(.040,.039,.017),BRASS,.004,case)
    box('CaseHandle',(0,.192,0),(.17,.028,.041),'#4c433c',.007,case)
    for x in [-.065,.065]:box('CaseHandleFoot',(x,.167,0),(.023,.055,.04),'#4c433c',.005,case)
    board=group('RitaBoard',(0,0,0));box('Clipboard',(0,0,0),(.225,.323,.024),OAK,.007,board)
    box('CallSheet',(0,-.003,.015),(.197,.284,.003),PAPER,parent=board)
    box('BoardClip',(0,.132,.022),(.09,.03,.012),'#929798',parent=board)
    for i in range(7):box('ShotList',(0,.077-i*.023,.020),(.145-.016*(i%3),.003,.001),'#989482',parent=board)
    cc=group('BlueCarbon',(0,0,0));box('InsuranceCarbon',(0,0,0),(.229,.296,.004),'#82acc1',.003,cc)
    label('CarbonTitle','INSURANCE',(0,.105,.006),.024,'#364d59',parent=cc)
    for i in range(9):box('InsuranceRule',(0,.076-i*.023,.006),(.169,.003,.001),'#517581',parent=cc)
    original=group('CarbonOriginal',(0,0,0));box('PolicyOriginal',(0,0,0),(.228,.296,.004),PAPER,.003,original)


make_bedroom()
make_lobby()
finish('hotel')
