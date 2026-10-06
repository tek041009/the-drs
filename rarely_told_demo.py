import os, math, urllib.request, subprocess, random
import numpy as np
import cv2
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
from kokoro_onnx import Kokoro

W,H,FPS,DUR=1280,720,24,30
OUT="Rarely_Told_First_30s_Free.mp4"
ROOT=os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

def download(url, fn):
    req=urllib.request.Request(url,headers={"User-Agent":"RarelyTold/1.0 (+https://github.com/tek041009/the-drs)"})
    with urllib.request.urlopen(req,timeout=120) as r, open(fn,"wb") as w:
        while True:
            chunk=r.read(1024*1024)
            if not chunk: break
            w.write(chunk)

URLS={
"tower":"https://commons.wikimedia.org/wiki/Special:Redirect/file/Tour_Eiffel_publicit%C3%A9_Citro%C3%ABn_1925.jpg",
"lustig":"https://commons.wikimedia.org/wiki/Special:Redirect/file/Victor_Lustig_Mugshot.jpeg",
"paris":"https://commons.wikimedia.org/wiki/Special:Redirect/file/Seeing_Paris_Part_One.webm",
}
for name,url in URLS.items():
    ext=".webm" if name=="paris" else ".jpg"
    fn=name+ext
    if not os.path.exists(fn):
        print("downloading",name,flush=True)
        download(url,fn)

# ---------- narration: free/open-source Kokoro ----------
model="kokoro-v1.0.int8.onnx"
voices="voices-v1.0.bin"
if not os.path.exists(model):
    download("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx",model)
if not os.path.exists(voices):
    download("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",voices)

script=("In 1925, one man managed to sell the Eiffel Tower. Not a souvenir. The actual tower. "
        "His name was Victor Lustig, and he had a talent for making impossible lies sound completely reasonable. "
        "Then, one morning in Paris, he noticed a newspaper story complaining about how expensive the Eiffel Tower was becoming to maintain. "
        "Most people would have read it and moved on. Lustig saw something else: an opportunity.")

tts=Kokoro(model,voices)
voice,sr=tts.create(script,voice="bm_george",speed=1.06,lang="en-gb")
dur=len(voice)/sr
if dur>29.2:
    # pitch-preserving global speed-up will happen in ffmpeg later
    sf.write("voice_raw.wav",voice,sr)
    factor=dur/29.2
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i","voice_raw.wav","-filter:a",f"atempo={factor:.6f}","voice.wav"],check=True)
else:
    sf.write("voice.wav",voice,sr)

# ---------- procedural soundtrack / foley ----------
voice_data,vsr=sf.read("voice.wav",dtype="float32")
N=int(DUR*vsr); t=np.arange(N)/vsr
rng=np.random.default_rng(2026)
# warm low pad
bed=(0.010*np.sin(2*np.pi*49*t)+0.006*np.sin(2*np.pi*73.5*t)+0.003*np.sin(2*np.pi*98*t))
bed*=0.6+0.4*np.sin(2*np.pi*0.055*t+0.9)**2
# subtle projector/room texture
noise=rng.normal(0,1,N)
kernel=np.ones(180)/180
noise=np.convolve(noise,kernel,mode="same")*0.0022
mix=(bed+noise).astype(np.float32)
# quiet tonal pulses, not melody-heavy
for sec,note in [(0.0,110),(6.5,123.47),(11.2,98),(19.3,82.4),(27.6,110)]:
    i=int(sec*vsr); L=min(int(1.0*vsr),N-i); tt=np.arange(L)/vsr
    mix[i:i+L]+=0.025*np.sin(2*np.pi*note*tt)*np.exp(-2.6*tt)
# transition whooshes
for sec in [6.3,11.0,19.0,27.3]:
    i=max(0,int((sec-.22)*vsr)); L=min(int(.45*vsr),N-i); tt=np.arange(L)/vsr
    z=rng.normal(0,1,L)
    env=np.sin(np.pi*np.clip(tt/.45,0,1))**2
    mix[i:i+L]+=0.018*z*env
mix[:len(voice_data)]+=voice_data*0.96
mx=np.max(np.abs(mix))
if mx>0.97: mix*=0.97/mx
sf.write("mix.wav",mix,vsr)

# ---------- assets ----------
tower=Image.open("tower.jpg").convert("RGB")
lustig=Image.open("lustig.jpg").convert("RGB")
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
COND="/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"
def F(sz,b=False,c=False):
    return ImageFont.truetype(COND if c else (BOLD if b else FONT),sz)
WHITE=(245,241,232); RED=(211,54,47); INK=(27,25,22); CREAM=(226,216,193)

def cover(im,size=(W,H),scale=1.0,dx=0,dy=0):
    x=ImageOps.fit(im,size,Image.Resampling.LANCZOS)
    if scale!=1:
        nw,nh=int(size[0]*scale),int(size[1]*scale)
        z=x.resize((nw,nh),Image.Resampling.LANCZOS)
        l=(nw-size[0])//2+int(dx); top=(nh-size[1])//2+int(dy)
        x=z.crop((l,top,l+size[0],top+size[1]))
    return x

def grade(im,bright=.82,contrast=1.12,warm=.07):
    im=ImageEnhance.Contrast(im).enhance(contrast)
    im=ImageEnhance.Brightness(im).enhance(bright)
    return Image.blend(im,Image.new("RGB",im.size,(55,35,17)),warm)

# tower alpha: dark structure against lighter surrounding
tw=np.array(cover(tower,(760,1000),1.0))
g=cv2.cvtColor(tw,cv2.COLOR_RGB2GRAY)
mask=(g<135).astype(np.uint8)*255
mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8),iterations=1)
mask=cv2.GaussianBlur(mask,(0,0),1.2)
tower_fg=Image.fromarray(tw).convert("RGBA"); tower_fg.putalpha(Image.fromarray(mask))
tower_bg=Image.fromarray(tw).filter(ImageFilter.GaussianBlur(8))

# Lustig cutout via grabcut
lm=np.array(lustig)
lm=cv2.resize(lm,(760,500))
gc=np.zeros(lm.shape[:2],np.uint8)
bgd=np.zeros((1,65),np.float64); fgd=np.zeros((1,65),np.float64)
rect=(80,20,lm.shape[1]-160,lm.shape[0]-40)
cv2.grabCut(lm,gc,rect,bgd,fgd,5,cv2.GC_INIT_WITH_RECT)
la=np.where((gc==2)|(gc==0),0,255).astype(np.uint8)
la=cv2.GaussianBlur(la,(0,0),1.0)
lustig_fg=Image.fromarray(lm).convert("RGBA"); lustig_fg.putalpha(Image.fromarray(la))

# Pick a lively stretch of archival Paris automatically
cap=cv2.VideoCapture("paris.webm")
fps=cap.get(cv2.CAP_PROP_FPS) or 24
length=cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps
candidates=[]
for s in np.arange(20,min(length-8,420),12):
    cap.set(cv2.CAP_PROP_POS_MSEC,float(s*1000))
    ok,a=cap.read()
    cap.set(cv2.CAP_PROP_POS_MSEC,float((s+1.2)*1000))
    ok2,b=cap.read()
    if not(ok and ok2): continue
    ga=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY); gb=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY)
    brightness=float(np.mean(ga)); motion=float(np.mean(cv2.absdiff(ga,gb)))
    edge=float(np.mean(cv2.Canny(ga,80,160)>0))
    if 45<brightness<220 and edge>.025:
        candidates.append((motion+edge*45,s))
candidates.sort(reverse=True)
chosen=[]
for _,s in candidates:
    if all(abs(s-x)>35 for x in chosen):
        chosen.append(float(s))
    if len(chosen)>=3: break
if len(chosen)<3: chosen=[45,150,280]
print("chosen archival windows",chosen,flush=True)

def load_archive_window(start,duration):
    c=cv2.VideoCapture("paris.webm")
    c.set(cv2.CAP_PROP_POS_MSEC,start*1000)
    frames=[]
    need=int(math.ceil(duration*FPS*1.10))+4
    srcfps=c.get(cv2.CAP_PROP_FPS) or FPS
    step=max(1,int(round(srcfps/FPS)))
    n=0
    while len(frames)<need:
        ok,fr=c.read()
        if not ok: break
        if n%step==0:
            frames.append(cv2.cvtColor(fr,cv2.COLOR_BGR2RGB))
        n+=1
    c.release()
    return frames

archive_windows=[
    load_archive_window(chosen[0],5.3),
    load_archive_window(chosen[1],11.5),
]
print("cached archival frames", [len(x) for x in archive_windows], flush=True)

def archive_frame(local_t,slot):
    frames=archive_windows[slot%len(archive_windows)]
    idx=min(len(frames)-1,max(0,int(local_t*FPS*1.05)))
    im=Image.fromarray(frames[idx])
    im=cover(im,(W,H),1.08,dx=12*math.sin(local_t*.7),dy=5*math.cos(local_t*.5))
    im=ImageOps.grayscale(im).convert("RGB")
    return grade(im,.82,1.18,.06)

def film(im,i):
    arr=np.array(im).astype(np.int16)
    r=np.random.default_rng(i+900)
    grain=r.normal(0,3.1,arr.shape[:2])[:,:,None]
    arr=np.clip(arr+grain,0,255).astype(np.uint8)
    im=Image.fromarray(arr)
    d=ImageDraw.Draw(im,"RGBA")
    # gate vignette
    d.rectangle((0,0,W,H),outline=(0,0,0,55),width=22)
    # occasional dust and hair
    if i%17==0:
        x=int((i*97)%W); d.ellipse((x,90,x+4,94),fill=(255,248,222,80))
    return im

def label(d,text,x=54,y=46):
    box=d.textbbox((0,0),text,font=F(18,True))
    d.rounded_rectangle((x,y,x+box[2]+28,y+34),5,fill=(10,10,10,180),outline=(255,255,255,35))
    d.text((x+14,y+17),text,font=F(18,True),fill=WHITE,anchor="lm")

def tower_scene(t):
    p=t/6.4
    bg=cover(tower_bg,(W,H),1.10+.035*p,dx=-22*p)
    bg=grade(bg,.52,1.18,.09)
    # moving cloud/light haze
    d=ImageDraw.Draw(bg,"RGBA")
    for k in range(5):
        cx=((k*310 + int(t*34))%1700)-210
        d.ellipse((cx,70+k*35,cx+360,210+k*35),fill=(220,220,210,10))
    # word behind tower
    sold="SOLD"
    fs=F(168,True,True)
    bb=d.textbbox((0,0),sold,font=fs)
    d.text(((W-bb[2])/2,250),sold,font=fs,fill=(*RED,220))
    # tower foreground moves slightly faster
    fg=tower_fg.copy()
    sc=0.77+0.045*p
    fg=fg.resize((int(fg.width*sc),int(fg.height*sc)),Image.Resampling.LANCZOS)
    x=W//2-fg.width//2+int(14*p); y=-115-int(14*p)
    bg.paste(fg,(x,y),fg)
    d=ImageDraw.Draw(bg,"RGBA")
    label(d,"PARIS · 1925")
    if t>3.0:
        a=min(255,int((t-3.0)*240))
        d.text((W-70,H-84),"THE ACTUAL TOWER.",font=F(27,True),fill=(245,241,232,a),anchor="ra")
    return bg

def street_scene(t):
    im=archive_frame(t,0)
    d=ImageDraw.Draw(im,"RGBA")
    # clean match-cut marker, not subtitles
    d.line((54,590,54,655),fill=RED,width=5)
    d.text((76,590),"PARIS",font=F(28,True),fill=WHITE)
    d.text((76,628),"THE CITY HE WAS ABOUT TO CON",font=F(18,True),fill=(212,207,198))
    return im

def lustig_scene(t):
    p=t/7.8
    im=Image.new("RGB",(W,H),(25,23,20))
    d=ImageDraw.Draw(im,"RGBA")
    # dossier background
    for x in range(-100,W+200,90):
        d.line((x+int(t*8),0,x-170+int(t*8),H),fill=(120,100,70,13),width=2)
    d.text((705,115),"LUSTIG",font=F(150,True,True),fill=(75,67,57,150),anchor="mm")
    # moving photo shadow / dossier card
    card=Image.new("RGBA",(760,560),(231,222,201,255))
    cd=ImageDraw.Draw(card,"RGBA")
    cd.rectangle((0,0,759,559),outline=(76,66,52,190),width=3)
    cd.text((40,32),"CASE FILE  /  1925",font=F(20,True),fill=INK)
    cd.line((40,76,720,76),fill=(90,78,60,120),width=2)
    card=card.rotate(-1.8+1.5*p,resample=Image.Resampling.BICUBIC,expand=1,fillcolor=(0,0,0,0))
    im.paste(card,(-125+int(12*p),115),card)
    # giant name behind subject
    d=ImageDraw.Draw(im,"RGBA")
    d.text((735,360),"VICTOR",font=F(92,True,True),fill=(239,231,213,175),anchor="lm")
    d.text((735,455),"LUSTIG",font=F(92,True,True),fill=RED,anchor="lm")
    d.text((741,535),"CAREER CON MAN",font=F(21,True),fill=(190,181,164),anchor="lm")
    # subject foreground
    fg=lustig_fg.copy()
    sc=1.13+0.025*math.sin(p*math.pi)
    fg=fg.resize((int(fg.width*sc),int(fg.height*sc)),Image.Resampling.LANCZOS)
    x=40+int(28*p); y=135-int(8*p)
    im.paste(fg,(x,y),fg)
    # red scan line at intro
    d=ImageDraw.Draw(im,"RGBA")
    if t<1.2:
        yy=int(120+(H-180)*(t/1.2)); d.rectangle((0,yy,W,yy+3),fill=(*RED,190))
    label(d,"THE MAN")
    return im

def newspaper_scene(t):
    # moving city under paper
    im=archive_frame(t,1)
    dark=Image.new("RGBA",(W,H),(0,0,0,100)); im=im.convert("RGBA"); im.alpha_composite(dark)
    paper=Image.new("RGBA",(920,610),(235,226,204,252))
    d=ImageDraw.Draw(paper,"RGBA")
    d.text((55,42),"LE MATIN",font=F(58,True,True),fill=INK)
    d.text((855,55),"PARIS · 1925",font=F(18,True),fill=(78,70,60),anchor="ra")
    d.line((55,118,865,118),fill=(70,62,52),width=3)
    d.text((55,150),"THE EIFFEL TOWER:",font=F(42,True),fill=INK)
    d.text((55,202),"A GROWING COST TO PARIS",font=F(42,True),fill=INK)
    # article columns
    for c in range(3):
        x=55+c*280
        for r in range(9):
            w=235-(r%3)*20
            d.rectangle((x,300+r*27,x+w,306+r*27),fill=(83,76,65,105))
    d.text((55,266),"Maintenance and repair costs continue to rise...",font=F(22,False),fill=(68,62,54))
    d.text((760,574),"RE-CREATED PRESS LAYOUT",font=F(14,True),fill=(95,86,72),anchor="ra")
    # animated marker
    hp=max(0,min(1,(t-3.0)/2.0))
    if hp>0:
        d.rounded_rectangle((48,255,48+int(690*hp),294),6,fill=(211,54,47,55))
    # rotate and drift for proper camera feel
    angle=-3.0+1.25*(t/10.8)
    paper=paper.rotate(angle,resample=Image.Resampling.BICUBIC,expand=1,fillcolor=(0,0,0,0))
    sc=1.0+0.055*(t/10.8)
    paper=paper.resize((int(paper.width*sc),int(paper.height*sc)),Image.Resampling.LANCZOS)
    px=215-int(90*(t/10.8)); py=64-int(38*(t/10.8))
    # shadow
    alpha=paper.getchannel("A").filter(ImageFilter.GaussianBlur(18))
    sh=Image.new("RGBA",paper.size,(0,0,0,0)); sh.putalpha(alpha.point(lambda x:int(x*.42)))
    im.alpha_composite(sh,(px+22,py+24)); im.alpha_composite(paper,(px,py))
    d=ImageDraw.Draw(im,"RGBA")
    label(d,"THE CLUE")
    if t>8.1:
        q=min(1,(t-8.1)/2.0)
        d.rounded_rectangle((820,590,1190,657),12,fill=(18,17,15,int(205*q)))
        d.text((1005,624),"AN OPPORTUNITY.",font=F(26,True),fill=(*WHITE,int(255*q)),anchor="mm")
    return im.convert("RGB")

# ---------- render ----------
proc=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
    "-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","fast","-crf","18",
    "-pix_fmt","yuv420p","visual.mp4"],stdin=subprocess.PIPE)
for i in range(FPS*DUR):
    t=i/FPS
    if t<6.4: im=tower_scene(t)
    elif t<11.2: im=street_scene(t-6.4)
    elif t<19.2: im=lustig_scene(t-11.2)
    else: im=newspaper_scene(t-19.2)
    # micro punch-in on cuts + film texture
    im=film(im,i)
    proc.stdin.write(np.asarray(im,dtype=np.uint8).tobytes())
proc.stdin.close()
if proc.wait()!=0: raise RuntimeError("video render failed")
cap.release()

subprocess.run(["ffmpeg","-y","-loglevel","error","-i","visual.mp4","-i","mix.wav","-t","30",
               "-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",OUT],check=True)
print(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration,size",
                               "-of","default=nw=1",OUT]).decode())
