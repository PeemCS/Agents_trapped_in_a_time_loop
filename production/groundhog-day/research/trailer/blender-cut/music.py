"""The Hearthside ballroom, Rialto projection booth and regional sound desk.

Run with the same Blender Python environment as stage.py. Coordinates and
rotations in the public helpers use Three's y-up, +z-toward-camera convention.
"""
import math
import random
from stage import *

RNG = random.Random(1193)
TAU = math.tau
walnut, darkwood, oak, gold = '#684631', '#352d2b', '#987250', '#c4a16a'
plaster, trim, panel, inset = '#bac1ad', '#d0c8aa', '#7d8f83', '#697e76'
skin, skinlight, coat = '#ca9078', '#d7a58a', '#313a47'
iron, bakelite = '#323c43', '#282b2e'


def block(name, xyz, size, color, r=0, parent=None):
    return box(name, xyz, size, color, bevel=r, parent=parent)


def beam(name, start, end, radius, color, parent=None):
    return rod(name,start,end,radius,color,parent=parent)


def oval(name,xyz,size,color,parent=None):
    return ball(name,xyz,size,color,parent=parent)


def turn(obj,x=0,y=0,z=0):
    rotate(obj,(x,y,z))
    return obj


def text(name, words, xyz, height, ink, parent=None):
    return label(name,words,xyz,height,ink,parent=parent)


def woodgrain(name,x0,x1,y,z,count):
    for n in range(count):
        x=RNG.uniform(x0,x1-.12); width=min(x1-x,RNG.uniform(.05,.38))
        block(name+str(n),(x+width/2,y+RNG.uniform(-.10,.10),z),(width,.002,.001),RNG.choice(['#7b563d','#71513d','#574236']))


def furniture(name, x,y,z,w,h,d, color=walnut):
    block(name+' top',(x,y+h,z),(w,.07,d),color,.015)
    for i,(sx,sz) in enumerate([(-1,-1),(-1,1),(1,-1),(1,1)]):
        leg=(x+sx*(w/2-.07), y+h/2,z+sz*(d/2-.07))
        block(name+' leg '+str(i),leg,(.075,h,.075),darkwood,.008)


def simple_chair(name,pos):
    g=group(name,pos)
    block(name+'.seat',(0,.45,0),(.43,.066,.42),'#916648',.016,g)
    for i,(sx,sz) in enumerate([(-1,-1),(-1,1),(1,-1),(1,1)]):
        h=.97 if sz<0 else .43
        block(name+'.leg'+str(i),(.175*sx,h/2,.175*sz),(.047,h,.047),darkwood,.007,g)
    for x in [-.095,0,.095]:
        block(name+' slat',(x,.72,-.174),(.027,.39,.034),walnut,.006,g)
    block(name+' crest',(0,.968,-.174),(.44,.067,.064),walnut,.009,g)
    return g


def sconce(name,x,z):
    block(name+' back',(x,2.33,z),(.16,.33,.045),'#9a7e4a',.025)
    beam(name+' bent',(x,2.28,z),(x,2.28,z+.18),.027,gold)
    oval(name+' diffuser',(x,2.48,z+.16),(.205,.32,.205),'#ffda95')
    block(name+' shade cap',(x,2.33,z+.16),(.15,.045,.15),gold,.015)


def tall_window(name,x):
    z=-3.21; w=1.18; base=1.01; h=2.30
    block(name+' architrave',(x,base+h/2,z),(w+.22,h+.18,.16),trim,.023)
    block(name+' shadow',(x,base+h/2,z+.073),(w+.06,h+.02,.045),'#524e45',.009)
    block(name+' glass',(x,base+h/2,z+.10),(w,h,.034),'#a8c0c4')
    # Muted geometric tree silhouettes are sandwiched behind the window bars.
    for i in range(15):
        xx=x+RNG.uniform(-w*.43,w*.43); yy=base+RNG.uniform(.03,.86)
        dx=RNG.uniform(-.16,.16); length=RNG.uniform(.13,.45)
        beam(name+' winter branch',(xx,yy,z+.132),(xx+dx,yy+length,z+.132),.005,'#899da4')
    for height in [.64,1.16,1.71]:
        block(name+' sash',(x,base+height,z+.155),(w+.01,.048,.055),trim,.004)
    block(name+' upright',(x,base+h/2,z+.157),(.042,h,.05),trim,.004)
    block(name+' sill',(x,base-.065,z+.15),(w+.29,.089,.29),'#dbcfaf',.012)
    # Crown, header, crest and a pair of small capital blocks.
    block(name+' header',(x,base+h+.13,z+.065),(w+.36,.08,.21),trim,.011)
    block(name+' cornice',(x,base+h+.205,z+.07),(w+.42,.07,.24),'#c7b998',.012)
    for s in [-1,1]:
        block(name+' cap',(x+s*(w/2+.055),base+h+.015,z+.084),(.13,.13,.12),'#d7ccac',.012)


def ballroom():
    setroot('ballroom')
    block('music floor base',(0,-.1,.25),(10,.18,8.7),'#614c3b')
    # Real parquet in basket-weave blocks. Alternate direction and tint by block.
    boardcolors=['#86694f','#8e7154','#977a5a','#9e805b','#a28262','#887058','#ab8a65']
    for i in range(11):
        for j in range(9):
            cx=-4.5+i*.9; cz=-2.85+j*.9; vertical=(i+j)%2==0
            for k in range(3):
                shift=(k-1)*.3
                block('Parquet',(cx+(shift if vertical else 0),-.006,cz+(0 if vertical else shift)),(.294 if vertical else .894,.012,.894 if vertical else .294),RNG.choice(boardcolors))
    block('Ballroom north wall',(0,2.0,-3.38),(10,.0+4,.2),plaster)
    block('Ballroom west wall',(-4.97,2,.4),(.2,4,7.6),'#abb7aa')
    block('Ballroom east wall',(4.97,2,.4),(.2,4,7.6),'#b7b8a1')
    block('Ballroom ceiling',(0,4.10,.4),(10,.2,8), '#c1bda8')
    for y,h,c,d in [(.055,.11,darkwood,.15),(.58,1.04,panel,.09),(1.12,.073,trim,.14),(1.18,.037,gold,.11),(3.68,.11,'#c9c4a6',.15),(3.78,.09,trim,.19),(3.88,.11,'#e2d0ac',.27)]:
        block('North millwork',(0,y,-3.24),(9.94,h,d),c,.005)
        for s in [-1,1]:
            block('Side millwork',(s*4.88,y,.4),(d,h,7.6),c,.005)
    for i in range(17):
        x=-4.64+i*.58
        block('raised panel',(x,.57,-3.176),(.47,.72,.035),inset,.015)
        block('rail',(x,.56,-3.153),(.397,.64,.023),panel,.01)
    for x in [-3.91,-1.22,1.22,3.91]:
        block('north pilaster',(x,2.43,-3.215),(.135,2.6,.13),'#a2a99a',.012)
        block('north capital',(x,3.53,-3.16),(.24,.12,.14),trim,.016)
    tall_window('West Frost',-2.38); tall_window('East Frost',2.38)
    for i,x in enumerate([-3.5,-.88,.88,3.5]): sconce('Brass sconce '+str(i),x,-3.12)
    # A frame with period ballroom dance program on the west end of the wall.
    for i,x in enumerate([-4.44,4.44]):
        block('framed program',(x,2.12,-3.19),(.52,.74,.09),darkwood,.018)
        block('program paper',(x,2.12,-3.135),(.43,.65,.014),'#c7b795')
        text('program title','WINTER',(x,2.27,-3.118),.066,darkwood)
        text('program subtitle','SOCIAL',(x,2.17,-3.118),.072,darkwood)
        for n in range(4): block('program rule',(x,2.03-n*.047,-3.117),(.27-n*.03,.01,.002),'#8d7c61')
    # The walnut upright. Strings, sides, panels, keybed and brass pedals are modelled.
    block('Piano case',(0,.69,-2.77),(1.63,1.38,.48),darkwood,.045)
    block('Piano bottom apron',(0,.35,-2.50),(1.56,.67,.10),walnut,.025)
    block('Piano low inset',(0,.36,-2.437),(1.32,.47,.026),'#5d493b',.018)
    block('Piano low face',(0,.36,-2.414),(1.22,.37,.018),'#664c38',.013)
    block('Piano fallboard',(0,1.045,-2.49),(1.57,.51,.115),'#76503a',.027)
    block('Piano upper inset',(0,1.15,-2.416),(1.35,.24,.022),'#503b31',.019)
    block('Piano upper burl',(0,1.15,-2.397),(1.28,.185,.02),'#78543a',.018)
    woodgrain('Fallboard grain',-.63,.63,1.145,-2.383,21)
    block('Piano bevel crown',(0,1.41,-2.72),(1.70,.075,.57),'#755138',.022)
    block('Piano music rail',(0,.954,-2.403),(1.46,.033,.07),gold,.005)
    text('maker label','H A R R I N G T O N',(0,1.071,-2.38),.033,'#dfbe7b')
    block('Music stand lower',(0,1.011,-2.37),(.57,.045,.095),walnut,.007)
    block('Keyboard ledger',(0,.748,-2.32),(1.62,.093,.49),darkwood,.018)
    block('Ivory slip',(0,.765,-2.06),(1.53,.022,.024),'#986e47',.004)
    for side in [-1,1]:
        block('Keyboard cheek',(side*.794,.812,-2.31),(.074,.12,.49),walnut,.012)
        block('Console leg',(side*.709,.40,-2.135),(.086,.71,.11),darkwood,.014)
        block('Console foot',(side*.709,.06,-2.18),(.15,.10,.26),walnut,.012)
        oval('Piano caster',(side*.709,.045,-2.2),(.059,.059,.04),gold)
        beam('piano brass handle',(side*.565,.861,-2.37),(side*.565,.877,-2.37),.008,gold)
    block('Treble cheek scuff',(.789,.841,-2.055),(.042,.008,.003),'#c29964')
    for i in range(52):
        x=-.73+i*.0286
        block('whiteKey%02d'%i,(x,.81,-2.265),(.02765,.04,.36),RNG.choice(['#e7decb','#e5ddca','#eee5d1']),.002)
        if (i+5)%7 not in (2,6) and i<51:
            block('blackKey%02d'%i,(x+.0143,.843,-2.323),(.017,.045,.226),'#28292a',.002)
    for x in [-.065,0,.065]:
        beam('pedal shaft',(x,.088,-2.46),(x,.075,-2.30),.016,'#90734c')
        oval('brass pedal',(x,.08,-2.294),(.044,.036,.094),gold)
    furniture('piano bench',0,0,-1.62,.79,.46,.36)
    block('leather bench',(0,.50,-1.62),(.815,.09,.385),'#453f3b',.028)
    # Played both in the close POV and by the full figure in the evening return.
    for side in ['L','R']:
        model_hand(side)
    phil=actor('BallPhil',(0,0,-1.60),'phil','sit'); turn(phil,y=math.pi)
    rita=actor('BallRita',(-1.44,0,-1.1),'rita','stand'); turn(rita,y=-.40)
    seated=actor('BallRitaSeated',(-.92,0,-1.53),'rita','sit'); turn(seated,y=1.75)
    chair=simple_chair('RitaChair',(-1.43,0,-1.43)); turn(chair,y=1.64)


def model_hand(side):
    left=side=='L'; s=-1 if left else 1; x=s*.185
    g=group('PianoHand'+side,(x,.875,-2.225))
    # Sleeve/palm/fingers laid horizontally. Camera sits behind the wrists.
    beam('Sleeve '+side,(s*.17,-.13,.57),(s*.032,-.026,.077),.077,coat,g)
    oval('cuff '+side,(s*.032,-.025,.102),(.142,.105,.14),'#414b54',g)
    oval('wrist '+side,(s*.011,-.006,.04),(.086,.062,.11),skin,g)
    oval('palm '+side,(0,0,-.02),(.126,.061,.127),skinlight,g)
    if left:
        oval('steel watchband',(s*.025,.009,.088),(.12,.078,.046),'#898d87',g)
        oval('watch case',(s*.025,.048,.087),(.069,.020,.066),'#c0bb9c',g)
        oval('watch dial',(s*.025,.061,.086),(.054,.008,.05),'#323c43',g)
        beam('watch hand',(s*.025,.068,.088),(s*.035,.068,.074),.0023,'#e1d0ab',g)
    for i in range(5):
        # From thumb at inside edge to shorter pinkie.
        fx=s*[-.059,-.034,0,.03,.053][i]
        z=[-.02,-.063,-.074,-.063,-.044][i]
        finger=group('PianoFinger'+side+str(i),(fx,.006,z),parent=g)
        dx=s*[-.036,-.008,.001,.008,.018][i]; length=[.065,.083,.091,.080,.067][i]
        beam('proximal finger',(0,0,0),(dx*.57,.007,-length*.55),.014 if i<4 else .012,skinlight,finger)
        beam('distal finger',(dx*.57,.007,-length*.55),(dx,-.028,-length),.0128 if i<4 else .0107,skinlight,finger)
        oval('fingertip',(dx,-.028,-length),(.025,.021,.026),skinlight,finger)
        oval('nail',(dx,-.017,-length+.003),(.013,.004,.018),'#dfb59e',finger)


def reel(name,pos,radius,parent=None):
    # Horizontal axis points toward the camera so spoke motion reads immediately.
    g=group(name,pos,parent=parent)
    oval('reel black rim',(0,0,0),(radius*2,.0+radius*2,.060),iron,g)
    oval('reel film',(0,0,.04),(radius*1.83,radius*1.83,.035),'#7b6756',g)
    oval('reel inner',(0,0,.061),(radius*1.44,radius*1.44,.025),'#373d3e',g)
    for i in range(5):
        a=i*TAU/5
        beam('reel spoke',(0,0,.09),(math.cos(a)*radius*.93,math.sin(a)*radius*.93,.09),.018,'#94a49e',g)
    oval('reel hub',(0,0,.095),(.09,.09,.032),'#b8aea0',g)
    return g


def cassette(name,pos,parent=None):
    g=group(name,pos,parent=parent)
    block('cassette shell',(0,0,0),(.179,.114,.026),bakelite,.004,g)
    block('cassette sticker',(0,.010,.015),(.159,.072,.002),'#ccbfa3',.002,g)
    block('cassette stripe',(0,.027,.017),(.149,.011,.002),'#aa674e',0,g)
    for x in [-.044,.044]:
        oval('cassette spindle',(x,.003,.020),(.029,.029,.004),'#3c4242',g)
    text('cassette type','ALMA',(0,.037,.02),.016,'#292c2f',g)
    return g


def workroom(x,regional):
    # Distinct station and booth, shot on opposite sides of a transition.
    tag='Studio' if regional else 'Booth'
    def B(n,a,b,c,r=0): return block(tag+n,(a[0]+x,a[1],a[2]),b,c,r)
    def L(n,t,a,h,c): return text(tag+n,t,(a[0]+x,a[1],a[2]),h,c)
    wall='#626e73' if regional else '#728080'
    B('floor',(0,-.065,.2),(7,.13,6),'#66665e')
    B('rear',(0,1.65,-2.45),(7,3.3,.16),wall)
    for s in [-1,1]: B('side',(s*3.4,1.65,.1),(.16,3.3,5.3),wall)
    B('ceiling',(0,3.36,.1),(7,.1,5.3),'#697777')
    # Absorptive wall strips, utility raceways and paned control glass.
    B('baseboard',(0,.08,-2.31),(6.8,.15,.08),'#404d50')
    for j in range(3):
        B('conduit',(0,2.99-j*.055,-2.32),(6.8,.023,.028),'#929996')
    wx=-1.05
    B('window trim',(wx,1.91,-2.33),(2.9,1.39,.14), '#a49a86' if regional else trim,.02)
    B('window rubber',(wx,1.91,-2.241),(2.77,1.26,.055),'#363f44',.006)
    B('blue glass',(wx,1.91,-2.20),(2.67,1.17,.03),'#526f80')
    for j in range(6):
        w=RNG.uniform(.2,.57); h=RNG.uniform(.2,.67); xx=wx-1.1+j*.42
        B('far skyline',(xx,1.32+h/2,-2.174),(w,h,.016),RNG.choice(['#4b616b','#596b70','#465b68']))
        B('snow roof',(xx,1.325+h,-2.157),(w+.02,.033,.018),'#a0b6b9')
        for n in range(2): B('far light',(xx-w*.22+n*.15,1.28+h-.09,-2.151),(.037,.06,.012),'#c3a47a')
    for dx in [-.47,.47]: B('mullion',(wx+dx,1.91,-2.135),(.039,1.17,.05),'#53636a')
    B('blind rail',(wx,2.49,-2.11),(2.70,.068,.075),'#9da29a')
    for j in range(4): B('venetian',(wx,2.42-j*.055,-2.102),(2.69,.027,.047),'#aeb4a7')
    furniture(tag+' desk',x,0,-1.05,4.2,.95,.89,'#8c7254')
    B('desk front',(0,.68,-.65),(4.0,.46,.075),'#6b5447',.013)
    B('edge trim',(0,.914,-.603),(4.24,.067,.064),darkwood,.008)
    for xx in [-1.8,-.65,.6,1.8]:B('desk pull',(xx,.78,-.594),(.15,.025,.02),gold,.003)
    # Storage shelves to frame screen-right; labelled boxes are visible even in close-ups.
    for tier in range(3):
        yy=1.55+tier*.32
        B('shelf',(2.25,yy,-2.17),(1.57,.045,.33),'#796e57',.006)
        for j in range(6):
            xx=1.58+j*.23; hh=RNG.uniform(.17,.25)
            B('archive case',(xx,yy+hh/2+.026,-2.14),(.156,hh,.18),RNG.choice(['#9c9178','#616f70','#a39574','#68625e']),.006)
            B('archive spine',(xx,yy+.095,-2.041),(.12,.026,.004),'#d6c9b0')
    B('rack',(2.47,.68,-1.50),(.87,1.32,.61),'#343b3d',.035)
    for j in range(8):
        yy=.19+j*.135; B('rack unit',(2.47,yy,-1.18),(.77,.118,.024),'#555d5b')
        for n in [-.29,.29]: B('rack handle',(2.47+n,yy,-1.14),(.023,.080,.06),'#a5a49a',.004)
        B('rack index',(2.38,yy,-1.157),(.21,.022,.009),'#aaa38c')
        B('rack LED',(2.64,yy,-1.157),(.02,.021,.008),'#d5a057')
    if regional:
        L('station name','W P A X',(1.45,2.84,-2.31),.22,'#dacead')
        L('station subtitle','REGIONAL  BROADCAST  SERVICE',(1.45,2.60,-2.31),.053,'#dacead')
        B('set lamp plaque',(-2.52,2.55,-2.25),(.77,.28,.11),'#263136',.02)
        B('set lamp',(-2.52,2.55,-2.17),(.69,.2,.04),'#a85043',.012)
        L('lamp lettering','STUDIO',(-2.52,2.55,-2.144),.098,'#fae5b0')
    else:
        L('booth plaque','R I A L T O',(1.26,2.82,-2.31),.19,'#d5caaa')
        L('booth plaque line','PROJECTION ROOM',(1.26,2.63,-2.31),.064,'#c4c5af')


def booth():
    setroot('booth')
    workroom(0,False); workroom(12,True)
    # Rialto's dual reel projector and guide path.
    block('Projector base',(-1.55,1.045,-1.06),(.68,.13,.46),iron,.018)
    block('Projector casting',(-1.53,1.38,-1.1),(.46,.59,.36),'#586461',.045)
    beam('Projector lens',(-1.36,1.45,-1.14),(-1.05,1.45,-1.14),.093,iron)
    for i,x in enumerate([-1.82,-1.275]):
        beam('Reel fork',(-1.55,1.49,-1.08),(x,1.86,-1.08),.034,'#838d84')
        reel('FilmReel'+str(i),(x,1.91,-1.03),.228)
    block('Analog deck',(0,1.13,-1.02),(.75,.3,.40),'#515957',.019)
    block('Deck face',(0,1.13,-.811),(.71,.26,.018),'#a4a298',.009)
    block('Deck well',(-.15,1.15,-.79),(.30,.119,.012),bakelite,.005)
    for i in range(5): block('Transport key',(-.26+i*.055,1.03,-.77),(.044,.033,.027),'#c8c0a7',.004)
    for i in range(2): oval('Deck level',(.13+i*.115,1.11,-.77),(.071,.071,.032),darkwood)
    block('Cue paper',(.8,1.0,-.88),(.38,.012,.25),'#d9ceb5',.003)
    for j in range(5): block('Cue printed line',(.8,1.008,-.96+j*.033),(.23-(j%3)*.03,.001,.006),'#716c5f')
    castape=cassette('LarryCassette',(.025,1.15,-.44));turn(castape,x=-.35)
    al=actor('BoothLarry',(-.49,0,-.27),'larry','stand');turn(al,y=.77)
    ar=actor('BoothRita',(.66,0,-.29),'rita','stand');turn(ar,y=-1.47)
    # Lamp on Rita's side.
    oval('Desk lamp base',(1.17,1.012,-1.15),(.29,.07,.26),darkwood)
    beam('desk lamp stem',(1.17,1.04,-1.15),(1.17,1.53,-1.15),.019,gold)
    oval('desk lamp hood',(1.13,1.58,-1.15),(.36,.19,.30),'#c7a77f')
    oval('desk lamp bulb',(1.14,1.50,-1.13),(.18,.07,.18),'#ffdd95')
    # The regional station desk is a separate room, 12 m east of the projector.
    x=12
    block('Wire Console',(x,1.07,-.98),(1.93,.22,.68),'#333c3e',.025)
    block('Console plate',(x,1.187,-.97),(1.82,.018,.59),'#65706a',.006)
    for i in range(9):
        xx=x-.80+i*.104
        block('channel divide',(xx+.046,1.20,-.93),(.003,.005,.47),'#a0a69b')
        block('channel slot',(xx,1.207,-.84),(.011,.007,.18),'#292e30')
        block('sliding fader',(xx,1.222,-.90+.12*RNG.random()),(.058,.035,.053),'#ddd5b9',.005)
        for j in range(2): oval('rotary knob',(xx,1.22,-1.01-j*.092),(.052,.048,.052),['#b19463','#797c70'][j])
        block('track label',(xx,1.20,-.72),(.077,.006,.032),'#c8c0a9')
    # Finger finds the dark red key and the paired backlit VU needles respond.
    for i in range(2):
        xx=x+.35+i*.28
        block('meter bezel',(xx,1.287,-1.21),(.269,.154,.171),'#283131',.011)
        block('meter dial',(xx,1.287,-1.116),(.229,.109,.01),'#e1c68e',.005)
        for j in range(9):
            a=(-.98+j*.24); dx=.089*math.sin(a); dy=.086*math.cos(a)
            beam('meter tick',(xx+dx,1.257+dy,-1.107),(xx+dx*.90,1.257+dy*.91,-1.107),.0023,'#4c4941')
        needle=group('VuNeedle'+str(i),(xx,1.25,-1.102))
        beam('pointer',(0,0,0),(0,.089,0),.0027,'#743a29',needle)
    block('Wire switch surround',(x+.47,1.215,-.82),(.231,.03,.187),bakelite,.007)
    block('WireSwitch',(x+.47,1.246,-.82),(.176,.045,.129),'#b55743',.008)
    lamp=block('TransmissionLamp',(x+.65,1.23,-.82),(.046,.041,.049),'#e2a54c',.006)
    block('wire indicator panel',(x+.49,1.22,-.705),(.53,.02,.06),'#2e3737',.004)
    # Vertical faceplate visible to the over-shoulder camera.
    text('switch legend','REGIONAL   LINE',(x+.45,1.106,-.628),.043,'#e7dcba')
    block('source riser',(x-.30,1.13,-1.54),(.69,.26,.49),'#5a625a',.018)
    block('source deck',(x-.30,1.38,-1.54),(.56,.28,.45),'#555e5c',.023)
    block('source deck front',(x-.30,1.39,-1.303),(.51,.226,.015),'#a9a798',.006)
    block('cassette source well',(x-.30,1.43,-1.29),(.31,.132,.014),'#303738',.005)
    cassette('AlmaSource',(x-.30,1.43,-1.27))
    for j in range(5): block('source key',(x-.48+j*.068,1.308,-1.274),(.058,.028,.025),'#c1b8a3',.003)
    act=actor('StationRita',(x-.10,0,-.23),'rita','stand');turn(act,y=math.pi)
    # Independent articulated right arm, matched to Rita's coat, extends over desk.
    g=group('WireHand',(x+.47,1.31,-.82))
    beam('Rita coat sleeve',(-.17,.044,.47),(-.04,.079,.121),.069,'#405a50',g)
    oval('Rita hand',(-.025,.056,.065),(.12,.065,.142),skinlight,g)
    for j in range(4):
        dx=(j-1.5)*.023; ext=.108 if j==1 else .062
        beam('switch finger',(dx,.057,.054),(dx*.79,.048,-ext*.45),.0115,skinlight,g)
        beam('switch tip',(dx*.79,.048,-ext*.45),(dx*.78,.01 if j==1 else .037,-ext*.65),.0107,skinlight,g)
    beam('switch thumb',(-.06,.052,.071),(-.082,.043,.019),.014,skinlight,g)


if __name__=='__main__':
    ballroom(); booth(); finish('music')
