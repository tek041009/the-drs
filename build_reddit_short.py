import os, math, subprocess, urllib.request, random, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import soundfile as sf
from kokoro_onnx import Kokoro

W,H = 540,960
FPS = 30
SCRIPT = ("My sister told me I'd ruin her wedding photos because of my face. "
          "I have a birthmark and burn scars from an accident when I was little, and I've spent years learning to be comfortable with them. "
          "I'm also her maid of honor. But a month before the wedding, she told me I needed professional stage makeup to cover everything because she wanted every photo flawless. "
          "When I refused, she cried, called our mum, and threatened to replace me with our cousin. "
          "Mum said I should just do this one thing for my sister. I said no. "
          "Now she's telling everyone I'm ruining her wedding. Would you still go?")

# ---------- TTS ----------
def dl(url, fn):
    if os.path.exists(fn): return
    req = urllib.request.Request(url, headers={"User-Agent":"RedditShortPilot/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(fn,"wb") as w:
        while True:
            b=r.read(1024*1024)
            if not b: break
            w.write(b)

model="kokoro-v1.0.int8.onnx"
voices="voices-v1.0.bin"
dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx",model)
dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",voices)
k=Kokoro(model,voices)
voice,sr=k.create(SCRIPT,voice="bm_george",speed=1.09,lang="en-gb")
sf.write("voice.wav",voice,sr)
duration=len(voice)/sr
DUR=max(28.0,min(55.0,duration+0.7))
print("voice duration",duration,"video duration",DUR)

# ---------- subtle original background bed ----------
N=int(sr*DUR)
t=np.arange(N)/sr
bed=np.zeros(N,dtype=np.float32)
# warm pad
bed += 0.010*np.sin(2*np.pi*55*t)
bed += 0.006*np.sin(2*np.pi*82.5*t)
bed *= (0.65+0.35*np.sin(2*np.pi*0.045*t+1.1)**2)
# soft kick every 0.8 s
for sec in np.arange(0.15,DUR,0.8):
    i=int(sec*sr); L=min(int(0.17*sr),N-i)
    if L>0:
        q=np.arange(L)/sr
        bed[i:i+L]+=0.022*np.sin(2*np.pi*(68-25*q)*q)*np.exp(-17*q)
# soft tick/snare on offbeat
rng=np.random.default_rng(7)
for sec in np.arange(0.55,DUR,0.8):
    i=int(sec*sr); L=min(int(0.055*sr),N-i)
    if L>0:
        q=np.arange(L)/sr
        bed[i:i+L]+=rng.normal(0,1,L).astype(np.float32)*np.exp(-45*q)*0.007
mix=bed.copy()
mix[:len(voice)] += voice[:N]*0.98
mx=np.max(np.abs(mix))
if mx>0.97: mix*=0.97/mx
sf.write("mix.wav",mix,sr)

# ---------- gameplay ----------
font_small="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font_num="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
f_score=ImageFont.truetype(font_small,17)
f_mini=ImageFont.truetype(font_num,14)

def lerp(a,b,x): return a+(b-a)*x
def glow_circle(draw,xy,r,fill):
    x,y=xy
    for rr,alpha in [(r*2.0,35),(r*1.55,55),(r*1.2,80)]:
        c=tuple(int(v) for v in fill[:3])+(alpha,)
        draw.ellipse((x-rr,y-rr,x+rr,y+rr),fill=c)
    draw.ellipse((x-r,y-r,x+r,y+r),fill=fill)

# deterministic obstacles
random.seed(42)
obstacles=[]
for n in range(70):
    lane=random.choice([-1,0,1])
    start=0.7+n*0.63+random.random()*0.18
    typ=random.choice(["barrier","coin","coin","barrier","gate"])
    obstacles.append((start,lane,typ))

def frame_at(sec):
    # render RGBA for glows, then flatten
    img=Image.new("RGBA",(W,H),(8,7,22,255))
    d=ImageDraw.Draw(img,"RGBA")
    # sky gradient
    for y in range(H):
        p=y/H
        r=int(10+28*(1-p))
        g=int(8+12*(1-p))
        b=int(25+45*(1-p))
        d.line((0,y,W,y),fill=(r,g,b,255))
    horizon=205
    # skyline
    city_shift=(sec*22)%80
    rng2=random.Random(123)
    for i in range(18):
        bw=rng2.randint(28,55)
        bx=int(i*35 - city_shift)% (W+90)-45
        bh=rng2.randint(60,180)
        by=horizon-bh
        shade=rng2.randint(18,32)
        d.rectangle((bx,by,bx+bw,horizon),fill=(shade,shade,55,255))
        # windows
        for wx in range(bx+7,bx+bw-4,10):
            for wy in range(by+8,horizon-6,16):
                if rng2.random()<0.72:
                    c=(255,86,185,120) if (i+wy//16)%2 else (67,208,255,115)
                    d.rectangle((wx,wy,wx+3,wy+6),fill=c)
    # road trapezoid
    road_top_l, road_top_r = W*0.43, W*0.57
    road_bot_l, road_bot_r = W*0.04, W*0.96
    d.polygon([(road_top_l,horizon),(road_top_r,horizon),(road_bot_r,H),(road_bot_l,H)],fill=(17,20,33,255))
    # side neon rails
    d.line((road_top_l,horizon,road_bot_l,H),fill=(0,225,255,210),width=4)
    d.line((road_top_r,horizon,road_bot_r,H),fill=(255,61,177,210),width=4)
    # perspective lane separators
    for frac in (1/3,2/3):
        xt=lerp(road_top_l,road_top_r,frac)
        xb=lerp(road_bot_l,road_bot_r,frac)
        d.line((xt,horizon,xb,H),fill=(130,145,180,90),width=2)
    # moving road stripes
    phase=(sec*1.8)%1
    for k in range(14):
        z=((k/14)+phase)%1
        # nonlinear perspective
        p=z*z
        y=horizon+(H-horizon)*p
        half=lerp((road_top_r-road_top_l)/2,(road_bot_r-road_bot_l)/2,p)
        cx=W/2
        d.line((cx-half,y,cx+half,y),fill=(110,130,160,int(18+55*p)),width=max(1,int(1+4*p)))
    # coins + obstacles moving toward camera
    for start,lane,typ in obstacles:
        rel=(sec-start)/3.7
        if 0<=rel<=1:
            p=rel**1.9
            y=horizon+18+(H-horizon-120)*p
            road_half=lerp((road_top_r-road_top_l)/2,(road_bot_r-road_bot_l)/2,p)
            x=W/2+lane*road_half*0.56
            scale=0.2+1.2*p
            if typ=="coin":
                r=5+12*p
                glow_circle(d,(x,y),r,(255,218,65,235))
                d.ellipse((x-r*0.45,y-r*0.8,x+r*0.45,y+r*0.8),outline=(255,250,180,230),width=max(1,int(2*scale)))
            elif typ=="barrier":
                ww=(20+75*p); hh=(14+55*p)
                d.rounded_rectangle((x-ww/2,y-hh,x+ww/2,y),radius=5+8*p,fill=(231,60,89,235),outline=(255,205,212,220),width=max(1,int(2+2*p)))
                d.line((x-ww/2+4,y-hh+4,x+ww/2-4,y-4),fill=(255,235,240,180),width=max(1,int(2+2*p)))
            else:
                ww=(32+90*p); hh=(42+105*p)
                d.rounded_rectangle((x-ww/2,y-hh,x+ww/2,y),radius=6+8*p,fill=(38,170,235,215),outline=(150,238,255,220),width=max(1,int(2+2*p)))
    # runner lane motion
    lane_float=0.72*math.sin(sec*1.55)+0.18*math.sin(sec*3.1)
    p=0.95
    road_half=(road_bot_r-road_bot_l)/2
    px=W/2 + lane_float*road_half*0.42
    py=H-145 - 12*max(0,math.sin(sec*2.7))
    # runner shadow
    d.ellipse((px-34,py+48,px+34,py+62),fill=(0,0,0,90))
    # body and head, stylised
    d.rounded_rectangle((px-25,py-4,px+25,py+56),radius=16,fill=(86,100,255,255),outline=(170,185,255,230),width=3)
    d.ellipse((px-18,py-38,px+18,py-2),fill=(245,195,155,255),outline=(255,225,200,230),width=2)
    # legs with gait
    gait=math.sin(sec*9)
    d.line((px-10,py+50,px-20-9*gait,py+87),fill=(30,35,62,255),width=9)
    d.line((px+10,py+50,px+20+9*gait,py+87),fill=(30,35,62,255),width=9)
    # arms
    d.line((px-22,py+12,px-38+8*gait,py+43),fill=(245,195,155,255),width=7)
    d.line((px+22,py+12,px+38-8*gait,py+43),fill=(245,195,155,255),width=7)
    # top HUD, but subtle because captions overlay later
    d.rounded_rectangle((18,18,132,56),radius=14,fill=(5,7,20,160),outline=(255,255,255,32),width=1)
    d.text((32,28),f"{int(sec*148+730):,}",font=f_score,fill=(255,255,255,235))
    d.rounded_rectangle((W-118,18,W-18,56),radius=14,fill=(5,7,20,160),outline=(255,255,255,32),width=1)
    d.ellipse((W-101,30,W-89,42),fill=(255,216,64,255))
    d.text((W-80,28),f"{12+int(sec)%31}",font=f_score,fill=(255,255,255,235))
    return img.convert("RGB")

# Prefer real royalty-free stock gameplay when acquired by the workflow.
# The procedural endless-runner remains only as a fail-safe so production never stalls.
if os.path.exists("stock.mp4") and os.path.getsize("stock.mp4") > 100000:
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-stream_loop","-1","-i","stock.mp4",
        "-t",f"{DUR:.3f}",
        "-vf","crop='min(iw,ih*9/16)':ih:(iw-min(iw,ih*9/16))/2:0,scale=540:960:flags=lanczos,fps=30",
        "-an","-c:v","libx264","-preset","veryfast","-crf","17","-pix_fmt","yuv420p","gameplay.mp4"
    ],check=True)
else:
    frames=int(math.ceil(DUR*FPS))
    cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
         "-c:v","libx264","-preset","veryfast","-crf","17","-pix_fmt","yuv420p","gameplay.mp4"]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    for i in range(frames):
        fr=frame_at(i/FPS)
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    if p.wait()!=0: raise RuntimeError("gameplay encode failed")

# ---------- captions ----------
segments=[
("MY SISTER SAID MY FACE",0),
("WOULD RUIN HER WEDDING PHOTOS.",1),
("I HAVE A BIRTHMARK AND BURN SCARS",0),
("FROM AN ACCIDENT WHEN I WAS LITTLE.",0),
("I'VE SPENT YEARS LEARNING",0),
("TO BE COMFORTABLE WITH THEM.",1),
("I'M ALSO HER MAID OF HONOR.",0),
("BUT A MONTH BEFORE THE WEDDING,",0),
("SHE SAID I NEEDED STAGE MAKEUP",1),
("TO COVER EVERYTHING.",0),
("SHE WANTED EVERY PHOTO FLAWLESS.",1),
("WHEN I REFUSED,",0),
("SHE CRIED, CALLED OUR MUM,",0),
("AND THREATENED TO REPLACE ME",1),
("WITH OUR COUSIN.",0),
("MUM SAID I SHOULD JUST DO",0),
("THIS ONE THING FOR MY SISTER.",0),
("I SAID NO.",1),
("NOW SHE'S TELLING EVERYONE",0),
("I'M RUINING HER WEDDING.",1),
("WOULD YOU STILL GO?",1),
]
weights=[max(2,len(s.replace(" ",""))/9.4) for s,_ in segments]
total=sum(weights)
start=0.02
usable=max(1.0,duration-0.25)
times=[]
cur=start
for (seg,hot),w in zip(segments,weights):
    dt=usable*w/total
    times.append((cur,min(duration+0.15,cur+dt),seg,hot))
    cur+=dt

def ass_time(x):
    h=int(x//3600); x-=h*3600
    m=int(x//60); x-=m*60
    s=int(x); cs=int(round((x-s)*100))
    if cs>=100: s+=1; cs-=100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

with open("captions.ass","w",encoding="utf-8") as f:
    f.write("""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Main,DejaVu Sans,74,&H00FFFFFF,&H0000CFFF,&H00101018,&H90000000,-1,0,0,0,100,100,0,0,1,6,3,8,75,75,235,1
Style: Tag,DejaVu Sans,34,&H00FFFFFF,&H00000000,&H00000000,&H7A000000,-1,0,0,0,100,100,0,0,3,1,0,8,80,80,95,1
Style: CTA,DejaVu Sans,84,&H00FFFFFF,&H0000CFFF,&H00101018,&H90000000,-1,0,0,0,100,100,0,0,1,7,3,8,70,70,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
    # persistent top tag
    f.write(f"Dialogue: 2,{ass_time(0)},{ass_time(DUR)},Tag,,0,0,0,,{{\\pos(540,112)}}REDDIT STORY • r/AITAH\\N{{\\fs26\\c&HBBBBBB&}}retold in our own words\n")
    for st,en,seg,hot in times:
        style="CTA" if seg in ("MY SISTER SAID MY FACE","WOULD RUIN HER WEDDING PHOTOS.","WOULD YOU STILL GO?") else "Main"
        if hot:
            # last key phrase in warm yellow
            words=seg.split()
            if len(words)>=3:
                cut=max(1,len(words)-2)
                a=" ".join(words[:cut]); b=" ".join(words[cut:])
                text=f"{{\\pos(540,410)}}{a} {{\\c&H00CFFF&}}{b}"
            else:
                text=f"{{\\pos(540,410)\\c&H00CFFF&}}{seg}"
        else:
            text=f"{{\\pos(540,410)}}{seg}"
        f.write(f"Dialogue: 3,{ass_time(st)},{ass_time(en)},{style},,0,0,0,,{text}\n")

# ---------- final composite ----------
# Darken top half and add subtle reddit-orange accent divider; captions above gameplay.
vf = ("scale=1080:1920:flags=lanczos,"
      "drawbox=x=0:y=0:w=1080:h=760:color=0x090A12@0.82:t=fill,"
      "drawbox=x=0:y=758:w=1080:h=6:color=0xFF5A36@0.95:t=fill,"
      "ass=captions.ass")
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","gameplay.mp4","-i","mix.wav",
    "-vf",vf,"-t",f"{DUR:.3f}",
    "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
    "-c:a","aac","-b:a","192k","-movflags","+faststart",
    "Reddit_Story_Short_Pilot.mp4"
],check=True)

# contact sheet for QA
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","Reddit_Story_Short_Pilot.mp4",
    "-vf","fps=1/5,scale=270:-2,tile=3x3","-frames:v","1","qa_sheet.jpg"
],check=True)

print(subprocess.check_output([
    "ffprobe","-v","error","-show_entries","format=duration,size","-of","default=nw=1",
    "Reddit_Story_Short_Pilot.mp4"
]).decode())
