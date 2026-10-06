import os, math, subprocess, urllib.request
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from kokoro_onnx import Kokoro

W,H,FPS,DUR=1280,720,24,30
NFR=FPS*DUR
OUT="Rarely_Told_Animated_First_30s_V2.mp4"

# ---------- free voice ----------
def dl(url,fn):
    req=urllib.request.Request(url,headers={"User-Agent":"RarelyTold/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r, open(fn,"wb") as w:
        while True:
            c=r.read(1024*1024)
            if not c: break
            w.write(c)

model="kokoro-v1.0.int8.onnx"; voices="voices-v1.0.bin"
if not os.path.exists(model): dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx",model)
if not os.path.exists(voices): dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",voices)

script=("In 1925, one man managed to sell the Eiffel Tower. Not a souvenir. The actual tower. "
        "His name was Victor Lustig, and he had a talent for making impossible lies sound completely reasonable. "
        "Then, one morning in Paris, he noticed a newspaper story complaining about how expensive the Eiffel Tower was becoming to maintain. "
        "Most people would have read it and moved on. Lustig saw something else: an opportunity.")

k=Kokoro(model,voices)
voice,sr=k.create(script,voice="bm_george",speed=1.03,lang="en-gb")
sf.write("voice_raw.wav",voice,sr)
vd=len(voice)/sr
if vd>29.25:
    factor=vd/29.25
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i","voice_raw.wav","-filter:a",f"atempo={factor:.6f}","voice.wav"],check=True)
else:
    os.replace("voice_raw.wav","voice.wav")

voice,sr=sf.read("voice.wav",dtype="float32")
A=int(DUR*sr); tt=np.arange(A)/sr
rng=np.random.default_rng(27)
# original procedural soundtrack
bed=(.008*np.sin(2*np.pi*49*tt)+.0045*np.sin(2*np.pi*73.5*tt)+.0028*np.sin(2*np.pi*98*tt)).astype(np.float32)
bed*=.62+.38*np.sin(2*np.pi*.048*tt+.7)**2
mix=bed
# impact, whoosh, type clicks
for sec in [0.05,5.3,8.7,17.1,23.1,28.4]:
    i=int(sec*sr); L=min(int(.5*sr),A-i); q=np.arange(L)/sr
    mix[i:i+L]+=.05*np.sin(2*np.pi*43*q)*np.exp(-7*q)
for sec in [4.9,9.0,16.8,22.8]:
    i=int(sec*sr); L=min(int(.32*sr),A-i); q=np.arange(L)/sr
    mix[i:i+L]+=rng.normal(0,1,L)*np.sin(np.pi*np.clip(q/.32,0,1))**2*.013
for sec in np.arange(20.2,23.0,.22):
    i=int(sec*sr); L=min(int(.025*sr),A-i)
    mix[i:i+L]+=rng.normal(0,1,L)*.010
mix[:min(A,len(voice))]+=voice[:A]*.96
mx=np.max(np.abs(mix))
if mx>.97: mix*=.97/mx
sf.write("mix.wav",mix,sr)

# ---------- visual helpers ----------
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def F(sz,b=False): return ImageFont.truetype(BOLD if b else FONT,sz)

INK=(23,27,33); NAVY=(21,30,42); SKY1=(238,197,127); SKY2=(114,155,177)
CREAM=(242,228,197); PAPER=(239,224,190); RED=(196,49,42); GOLD=(215,166,70)
STONE=(74,76,77); DARK=(34,38,43); SKIN=(173,119,79); COAT=(43,47,52)
WHITE=(247,244,237); GREEN=(67,94,72); SHADOW=(18,21,25)

def lerp(a,b,p): return a+(b-a)*p
def clamp(x,a=0,b=1): return max(a,min(b,x))
def ease(p): p=clamp(p); return 3*p*p-2*p*p*p
def ease_out(p): p=clamp(p); return 1-(1-p)**3

def paste_rot(base, layer, center, angle, scale=1.0):
    if scale!=1:
        layer=layer.resize((max(1,int(layer.width*scale)),max(1,int(layer.height*scale))),Image.Resampling.LANCZOS)
    layer=layer.rotate(angle,expand=True,resample=Image.Resampling.BICUBIC)
    x=int(center[0]-layer.width/2); y=int(center[1]-layer.height/2)
    base.alpha_composite(layer,(x,y))

def gradient_sky(img, top, bot, horizon=0.72):
    a=np.zeros((H,W,3),dtype=np.uint8)
    for y in range(H):
        p=min(1,y/(H*horizon))
        a[y,:,0]=int(lerp(top[0],bot[0],p)); a[y,:,1]=int(lerp(top[1],bot[1],p)); a[y,:,2]=int(lerp(top[2],bot[2],p))
    img.alpha_composite(Image.fromarray(a,'RGB').convert('RGBA'))

def draw_cloud(d,x,y,s,alpha=100):
    c=(250,240,221,alpha)
    for dx,dy,r in [(0,10,25),(28,0,34),(66,9,28),(95,15,22)]:
        d.ellipse((x+dx-r*s,y+dy-r*s,x+dx+r*s,y+dy+r*s),fill=c)

def world_x(x,cam,par=1): return (x-cam)*par+W/2

def draw_city(base,t,cam=0,zoom=1.0):
    d=ImageDraw.Draw(base,'RGBA')
    # distant skyline
    for i in range(-10,14):
        x=world_x(i*90,cam,.28)
        h=115+(i*i*17)%105
        col=(48+(i%3)*7,53+(i%4)*5,58+(i%2)*5,255)
        d.rectangle((x-45,H-270-h,x+45,H-270),fill=col)
        for yy in range(int(H-255-h),int(H-285),26):
            for xx in (x-25,x+7):
                d.rectangle((xx,yy,xx+12,yy+8),fill=(211,173,93,120))
    # mid buildings
    for i in range(-9,11):
        x=world_x(i*135,cam,.56)
        h=190+(i*73)%120
        col=(58+(i%3)*5,59+(i%4)*6,61+(i%2)*4,255)
        d.rectangle((x-64,H-170-h,x+64,H-170),fill=col)
        d.polygon([(x-70,H-170-h),(x,H-205-h),(x+70,H-170-h)],fill=(50,49,48,255))
        for r in range(4):
            for c in range(3):
                xx=x-42+c*34; yy=H-145-h+r*40
                d.rounded_rectangle((xx,yy,xx+18,yy+25),3,fill=(226,188,104,115))
    # street ground
    d.polygon([(0,H-185),(W,H-185),(W,H),(0,H)],fill=(52,54,54,255))
    # road perspective guides
    d.polygon([(W*.43,H-185),(W*.57,H-185),(W*.76,H),(W*.24,H)],fill=(41,43,45,255))
    for n in range(5):
        y=H-120+n*85
        d.polygon([(W*.49,y),(W*.51,y),(W*.53,y+45),(W*.47,y+45)],fill=(211,199,162,100))

def draw_eiffel(d,cx,base_y,scale,color,progress=1):
    # animated draw-on
    pts=[
        ((cx-150*scale,base_y),(cx-48*scale,base_y-250*scale)),
        ((cx+150*scale,base_y),(cx+48*scale,base_y-250*scale)),
        ((cx-48*scale,base_y-250*scale),(cx-20*scale,base_y-430*scale)),
        ((cx+48*scale,base_y-250*scale),(cx+20*scale,base_y-430*scale)),
        ((cx-20*scale,base_y-430*scale),(cx,base_y-515*scale)),
        ((cx+20*scale,base_y-430*scale),(cx,base_y-515*scale)),
    ]
    # deck and braces
    for y,w in [(base_y-245*scale,105),(base_y-425*scale,42),(base_y-490*scale,16)]:
        pts.append(((cx-w*scale,y),(cx+w*scale,y)))
    for yy,ww in [(base_y-105*scale,120),(base_y-165*scale,95),(base_y-320*scale,43),(base_y-370*scale,34)]:
        pts.append(((cx-ww*scale,yy),(cx+ww*scale,yy)))
    total=len(pts); show=progress*total
    for j,(a,b) in enumerate(pts):
        f=clamp(show-j)
        if f<=0: continue
        ex=lerp(a[0],b[0],f); ey=lerp(a[1],b[1],f)
        d.line((a[0],a[1],ex,ey),fill=color,width=max(2,int(8*scale)))
    # spire
    if progress>.82:
        f=clamp((progress-.82)/.18)
        y0=base_y-515*scale; y1=base_y-570*scale
        d.line((cx,y0,cx,lerp(y0,y1,f)),fill=color,width=max(2,int(5*scale)))

def draw_car(d,x,y,s,col):
    d.rounded_rectangle((x-42*s,y-18*s,x+43*s,y+18*s),radius=int(10*s),fill=col)
    d.rectangle((x-24*s,y-33*s,x+23*s,y-10*s),fill=col)
    d.ellipse((x-30*s,y+11*s,x-12*s,y+29*s),fill=(20,22,24))
    d.ellipse((x+14*s,y+11*s,x+32*s,y+29*s),fill=(20,22,24))

def banknote_layer():
    L=Image.new('RGBA',(110,58),(0,0,0,0)); d=ImageDraw.Draw(L,'RGBA')
    d.rounded_rectangle((2,2,108,56),6,fill=(166,185,137,255),outline=(39,73,46,255),width=3)
    d.ellipse((40,12,70,46),outline=(48,83,49),width=3); d.text((55,29),"£",font=F(18,True),fill=(48,83,49),anchor='mm')
    return L

def limb_layer(length,width,color):
    L=Image.new('RGBA',(width*4,length+width*2),(0,0,0,0)); d=ImageDraw.Draw(L,'RGBA')
    d.rounded_rectangle((width,0,width*3,length),radius=width,fill=color)
    return L

def draw_victor(base,x,y,s,phase=0,walk=True,side=False):
    # shadow
    d=ImageDraw.Draw(base,'RGBA')
    d.ellipse((x-42*s,y+77*s,x+45*s,y+94*s),fill=(8,10,12,80))
    bob=math.sin(phase*2*math.pi)*5*s if walk else 0
    hip=(x,y+bob)
    # legs
    swing=math.sin(phase*2*math.pi)*28 if walk else 0
    leg=limb_layer(int(92*s),int(13*s),COAT+(255,))
    paste_rot(base,leg,(x-15*s,y+63*s+bob),-swing,1)
    paste_rot(base,leg,(x+15*s,y+63*s+bob),swing,1)
    # body coat
    d=ImageDraw.Draw(base,'RGBA')
    d.polygon([(x-42*s,y-35*s+bob),(x+42*s,y-35*s+bob),(x+52*s,y+52*s+bob),(x-52*s,y+52*s+bob)],fill=COAT+(255,))
    d.polygon([(x-5*s,y-30*s+bob),(x+6*s,y-30*s+bob),(x+17*s,y+47*s+bob),(x-18*s,y+47*s+bob)],fill=(71,73,72,255))
    # arms
    arm=limb_layer(int(86*s),int(12*s),COAT+(255,))
    paste_rot(base,arm,(x-51*s,y+4*s+bob),swing*.8,1)
    paste_rot(base,arm,(x+51*s,y+4*s+bob),-swing*.8,1)
    # head
    d.ellipse((x-28*s,y-92*s+bob,x+29*s,y-35*s+bob),fill=SKIN+(255,),outline=(90,55,37,255),width=max(1,int(2*s)))
    # nose / eye
    d.ellipse((x+10*s,y-71*s+bob,x+14*s,y-67*s+bob),fill=(34,28,24,255))
    # hat
    d.rectangle((x-35*s,y-104*s+bob,x+36*s,y-88*s+bob),fill=DARK+(255,))
    d.rectangle((x-49*s,y-91*s+bob,x+50*s,y-84*s+bob),fill=DARK+(255,))
    return

def paper_layer(w=390,h=250):
    L=Image.new('RGBA',(w,h),(0,0,0,0)); d=ImageDraw.Draw(L,'RGBA')
    d.rounded_rectangle((1,1,w-2,h-2),8,fill=PAPER+(255,),outline=(87,76,62,255),width=2)
    d.text((26,18),"LE MATIN",font=F(34,True),fill=INK)
    d.line((25,62,w-25,62),fill=(77,67,56),width=2)
    d.text((26,78),"EIFFEL TOWER",font=F(25,True),fill=INK)
    d.text((26,109),"COSTS KEEP RISING",font=F(25,True),fill=INK)
    for c in range(3):
        x=26+c*115
        for r in range(5):
            d.rectangle((x,156+r*15,x+94-(r%2)*20,161+r*15),fill=(88,78,66,100))
    return L

def add_grain(im,seed):
    arr=np.array(im.convert('RGB')).astype(np.int16)
    r=np.random.default_rng(seed)
    g=r.normal(0,2.2,(H,W,1))
    arr=np.clip(arr+g,0,255).astype(np.uint8)
    return Image.fromarray(arr).convert('RGBA')

money=banknote_layer()
paper=paper_layer()

# ---------- scenes ----------
def scene1(t):
    im=Image.new('RGBA',(W,H),(0,0,0,255)); gradient_sky(im,SKY1,SKY2)
    d=ImageDraw.Draw(im,'RGBA')
    # moving clouds
    for i,(yy,s) in enumerate([(80,.85),(150,.6),(55,.45)]):
        draw_cloud(d,((i*430 + t*32)%(W+300))-180,yy,s,70)
    # camera glides down boulevard
    cam=-420+ease(t/6.2)*440
    draw_city(im,t,cam)
    d=ImageDraw.Draw(im,'RGBA')
    # Eiffel grows/draws on
    cx=W*.57
    prog=ease_out(t/2.6)
    draw_eiffel(d,cx,H-188,1.05,CREAM+(255,),prog)
    # traffic and pedestrians
    draw_car(d,160+(t*100)%1500,H-112,1.0,(122,42,34,255))
    draw_car(d,1050-(t*74)%1450,H-75,.78,(32,70,79,255))
    # Paris 1925 embedded, subtle
    a=int(255*clamp((t-.4)/.8))
    d.text((58,58),"PARIS · 1925",font=F(24,True),fill=(WHITE[0],WHITE[1],WHITE[2],a))
    # sale tag animates, with impact and string
    if t>3.7:
        p=ease_out((t-3.7)/1.0)
        tx=lerp(W+220,cx+32,p); ty=lerp(80,H-397,p)
        # string
        d.line((cx,H-470,tx-85,ty-5),fill=(83,58,45,220),width=4)
        tag=Image.new('RGBA',(225,120),(0,0,0,0)); td=ImageDraw.Draw(tag,'RGBA')
        td.polygon([(12,18),(180,18),(218,60),(180,103),(12,103)],fill=RED+(255,))
        td.ellipse((171,48,190,67),fill=CREAM+(255,))
        td.text((104,61),"SOLD",font=F(46,True),fill=WHITE+(255,),anchor='mm')
        paste_rot(im,tag,(tx,ty),-8+4*math.sin(t*3),1)
    # money bursts after tag lands
    if t>4.55:
        p=(t-4.55)/1.8
        for j in range(8):
            ang=j*0.78
            x=cx+math.cos(ang)*(60+190*p); y=H-370+math.sin(ang)*(35+130*p)+80*p*p
            paste_rot(im,money,(x,y),math.degrees(ang)+t*50,.55*(1-clamp((p-.65)/.35)))
    return im

def scene2(t):
    im=Image.new('RGBA',(W,H),(0,0,0,255))
    gradient_sky(im,(214,174,111),(88,128,151))
    d=ImageDraw.Draw(im,'RGBA')
    # deep parallax street
    for i in range(-2,9):
        x=i*195-(t*45)%195
        h=285+(i*43)%85
        d.rectangle((x,H-210-h,x+170,H-210),fill=(47,49,51,255))
        d.polygon([(x-8,H-210-h),(x+85,H-255-h),(x+178,H-210-h)],fill=(38,38,39,255))
        for r in range(4):
            for c in range(3):
                d.rectangle((x+25+c*45,H-185-h+r*45,x+45+c*45,H-160-h+r*45),fill=(225,183,95,120))
    d.rectangle((0,H-210,W,H),fill=(61,61,58,255))
    # street lamps scroll
    for j in range(6):
        x=(j*270-t*80)%1650-120
        d.rectangle((x,H-410,x+10,H-165),fill=(32,34,36,255))
        d.ellipse((x-18,H-434,x+28,H-388),fill=(218,169,75,220))
    # Victor walks, camera tracks him
    phase=(t*1.8)%1
    draw_victor(im,W*.49,H-214,1.28,phase,True)
    # coat-tail motion
    d=ImageDraw.Draw(im,'RGBA')
    # paper gusts around him - actual continuous motion
    for j in range(5):
        p=(t*.28+j*.19)%1
        x=lerp(-100,W+100,p)
        y=310+85*math.sin(p*math.pi*2+j)
        sc=.35+.18*math.sin(p*math.pi)
        paste_rot(im,money,(x,y),t*85+j*60,sc)
    # minimal environmental caption
    if t>1.3:
        a=int(230*clamp((t-1.3)/.6))
        d.rounded_rectangle((55,55,330,105),10,fill=(17,20,24,150))
        d.text((78,79),"VICTOR LUSTIG",font=F(25,True),fill=(WHITE[0],WHITE[1],WHITE[2],a),anchor='lm')
    # foreground car swipe for transition near end
    if t>6.7:
        x=lerp(-500,W+500,ease((t-6.7)/1.0))
        draw_car(d,x,H-82,2.2,(112,32,28,255))
    return im

def scene3(t):
    im=Image.new('RGBA',(W,H),(0,0,0,255))
    d=ImageDraw.Draw(im,'RGBA')
    # cafe wall
    d.rectangle((0,0,W,H),fill=(42,39,35,255))
    # giant window with animated Paris beyond
    d.rectangle((40,40,700,430),fill=(117,154,169,255))
    # skyline through glass
    for i in range(8):
        x=70+i*85-(t*12)%85; bh=90+(i*37)%100
        d.rectangle((x,430-bh,x+70,430),fill=(64,69,70,220))
    draw_eiffel(d,570,425,.43,(48,50,50,235),1)
    # window mullions
    for x in (40,370,700): d.rectangle((x-6,40,x+6,430),fill=(35,33,30,255))
    d.rectangle((40,220,700,230),fill=(35,33,30,255))
    # table
    d.polygon([(0,500),(W,500),(W,H),(0,H)],fill=(86,61,43,255))
    # coffee cup / steam
    d.rounded_rectangle((910,430,1015,510),18,fill=CREAM+(255,))
    d.arc((995,445,1050,500),270,90,fill=CREAM+(255,),width=10)
    for j in range(3):
        x=940+j*18; off=math.sin(t*2+j)*10
        d.arc((x+off,350-j*12,x+35+off,440-j*12),80,260,fill=(240,233,218,95),width=4)
    # Victor seated, animated head/hand
    draw_victor(im,830,400,1.16,0,False)
    # arm reaches for paper
    arm=limb_layer(105,14,COAT+(255,))
    ang=lerp(-55,-20,ease(clamp((t-1.5)/2.2)))
    paste_rot(im,arm,(760,447),ang,1)
    # newspaper flies in then unfolds
    if t<1.8:
        p=ease_out(t/1.8); x=lerp(-260,610,p); y=lerp(220,480,p)
        paste_rot(im,paper,(x,y),lerp(-35,6,p),.66)
    else:
        # two halves open outward with real motion
        p=ease_out((t-1.8)/1.4)
        halfL=paper.crop((0,0,paper.width//2,paper.height))
        halfR=paper.crop((paper.width//2,0,paper.width,paper.height))
        cx,cy=615,493
        # fold angle goes from closed to open
        paste_rot(im,halfL,(cx-lerp(0,105,p),cy),lerp(78,2,p),.85)
        paste_rot(im,halfR,(cx+lerp(0,105,p),cy),lerp(-78,-2,p),.85)
    # camera "push-in" faked by increasingly large headline overlay after 4s, integrated on paper
    if t>4.0:
        p=ease((t-4)/4.2)
        # translucent focus frame
        a=int(180*p)
        d.rounded_rectangle((250-int(90*p),155-int(45*p),1055+int(80*p),620+int(35*p)),28,outline=(RED[0],RED[1],RED[2],a),width=max(2,int(5*p)))
        # maintenance bars animate from article
        base_x=440; base_y=555
        heights=[30,58,91,132,175]
        for j,h in enumerate(heights):
            q=ease(clamp((t-4.5-j*.22)/.7))
            d.rounded_rectangle((base_x+j*55,base_y-h*q,base_x+32+j*55,base_y),6,fill=(RED[0],RED[1],RED[2],int(230*q)))
        # animated arrow line
        if t>5.2:
            q=ease(clamp((t-5.2)/1.2))
            pts=[(430,560),(520,515),(610,485),(700,405),(800,350)]
            total=(len(pts)-1)*q
            for k2 in range(len(pts)-1):
                f=clamp(total-k2)
                if f<=0: continue
                a0=pts[k2]; b0=pts[k2+1]
                e=(lerp(a0[0],b0[0],f),lerp(a0[1],b0[1],f))
                d.line((a0[0],a0[1],e[0],e[1]),fill=RED+(230,),width=7)
    # thought tower emerges, animated not card
    if t>8.2:
        q=ease_out((t-8.2)/2.5)
        cx=1050; by=390
        draw_eiffel(d,cx,by,.34,(RED[0],RED[1],RED[2],int(255*q)),q)
        for r in range(3):
            rr=(35+r*35)*q
            d.ellipse((cx-rr,by-185-rr,cx+rr,by-185+rr),outline=(RED[0],RED[1],RED[2],int((120-r*25)*q)),width=3)
    return im

# ---------- render ----------
proc=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgba",
                       "-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264",
                       "-preset","fast","-crf","18","-pix_fmt","yuv420p","visual.mp4"],stdin=subprocess.PIPE)

for i in range(NFR):
    t=i/FPS
    if t<6.3:
        im=scene1(t)
    elif t<14.1:
        im=scene2(t-6.3)
    else:
        im=scene3(t-14.1)
    # tasteful film texture + tiny camera shake on impacts
    im=add_grain(im,i)
    if any(abs(t-s)<.10 for s in (5.2,8.9,17.2,23.0)):
        dx=int(3*math.sin(i*2.1)); dy=int(2*math.cos(i*1.7))
        shaken=Image.new('RGBA',(W,H),(15,18,22,255)); shaken.alpha_composite(im,(dx,dy)); im=shaken
    proc.stdin.write(im.tobytes())
proc.stdin.close()
if proc.wait()!=0: raise RuntimeError("visual render failed")

subprocess.run(["ffmpeg","-y","-loglevel","error","-i","visual.mp4","-i","mix.wav","-t","30",
                "-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",OUT],check=True)
print(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration,size",
                               "-of","default=nw=1",OUT]).decode())
