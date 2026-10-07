import os, subprocess, urllib.request, shutil
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

SCRIPT=("My sister told me I'd ruin her wedding photos because of my face. "
"I have a birthmark and burn scars from an accident when I was little, and I've spent years learning to be comfortable with them. "
"I'm also her maid of honor. But a month before the wedding, she told me I needed professional stage makeup to cover everything because she wanted every photo flawless. "
"When I refused, she cried, called our mum, and threatened to replace me with our cousin. "
"Mum said I should just do this one thing for my sister. I said no. "
"Now she's telling everyone I'm ruining her wedding. Would you still go?")

def dl(url,fn):
    if os.path.exists(fn): return
    req=urllib.request.Request(url,headers={"User-Agent":"RedditShortPilot/1.0"})
    with urllib.request.urlopen(req,timeout=180) as r, open(fn,"wb") as w:
        while True:
            b=r.read(1024*1024)
            if not b: break
            w.write(b)

model="kokoro-v1.0.int8.onnx"; voices="voices-v1.0.bin"
dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx",model)
dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",voices)
k=Kokoro(model,voices)
voice,sr=k.create(SCRIPT,voice="bm_george",speed=1.10,lang="en-gb")
sf.write("voice_raw.wav",voice,sr)

# De-muffle chain: cut sub/bass mud, scoop low-mids, add presence/air,
# gentle compression and broadcast loudness. No music bed competing with speech.
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","voice_raw.wav",
    "-af",
    "highpass=f=95,"
    "equalizer=f=220:t=q:w=1.1:g=-4.5,"
    "equalizer=f=380:t=q:w=1.2:g=-2.2,"
    "equalizer=f=2800:t=q:w=1.0:g=2.8,"
    "equalizer=f=4800:t=q:w=1.0:g=2.2,"
    "equalizer=f=8500:t=q:w=0.8:g=1.3,"
    "acompressor=threshold=0.16:ratio=2.6:attack=8:release=70:makeup=1.65,"
    "loudnorm=I=-14.0:TP=-1.0:LRA=4",
    "voice_clean.wav"
],check=True)
v,sr=sf.read("voice_clean.wav",dtype="float32")
DUR=len(v)/sr+0.35
print("duration",DUR)

segments=[
("MY SISTER SAID MY FACE",1),
("WOULD RUIN HER WEDDING PHOTOS.",1),
("I HAVE A BIRTHMARK AND BURN SCARS",0),
("FROM AN ACCIDENT WHEN I WAS LITTLE.",0),
("I'VE SPENT YEARS LEARNING",0),
("TO BE COMFORTABLE WITH THEM.",1),
("I'M ALSO HER MAID OF HONOR.",1),
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
weights=[max(1.5,len(s.replace(" ",""))/10.2) for s,_ in segments]
usable=max(1.0,(len(v)/sr)-0.04)
cur=0.01
timed=[]
for (seg,hot),w in zip(segments,weights):
    dt=usable*w/sum(weights)
    timed.append((cur,min(cur+dt,DUR),seg,hot))
    cur+=dt

def ast(x):
    h=int(x//3600); x-=h*3600; m=int(x//60); x-=m*60
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
Style: Main,DejaVu Sans,70,&H00FFFFFF,&H0000CFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,8,72,72,1040,1
Style: Hook,DejaVu Sans,82,&H00FFFFFF,&H0000CFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,8,64,64,1030,1
Style: Small,DejaVu Sans,29,&H00D6D6D6,&H00000000,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,8,60,60,1195,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
    for idx,(st,en,seg,hot) in enumerate(timed):
        style="Hook" if idx<2 or seg=="WOULD YOU STILL GO?" else "Main"
        if hot:
            words=seg.split()
            cut=max(1,len(words)-2)
            a=" ".join(words[:cut]); b=" ".join(words[cut:])
            txt=f"{{\\c&HFFFFFF&}}{a} {{\\c&H00D7FF&}}{b}"
        else:
            txt=seg
        # Captions live in the clean upper field; gameplay is entirely below.
        f.write(f"Dialogue: 5,{ast(st)},{ast(en)},{style},,0,0,0,,{{\\pos(540,360)}}{txt}\n")

# Build: top story panel + clean no-hands gameplay below.
# Game is cropped to fill the bottom 1080x1120 without stretching.
fc=(
"[0:v]scale=1080:1920:flags=lanczos,"
"crop=1080:1120:0:400[game];"
"color=c=0x101116:s=1080x1920:r=30:d="+f"{DUR:.3f}"+"[bg];"
"[bg][game]overlay=0:800[tmp];"
"[tmp]drawbox=x=0:y=795:w=1080:h=5:color=0xFF5A36@0.95:t=fill,"
"ass=captions.ass[outv]"
)
subprocess.run([
    "ffmpeg","-y","-loglevel","error",
    "-stream_loop","-1","-i","runner.mp4","-i","voice_clean.wav",
    "-filter_complex",fc,
    "-map","[outv]","-map","1:a:0","-t",f"{DUR:.3f}",
    "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
    "-c:a","aac","-b:a","192k","-movflags","+faststart",
    "Reddit_Story_Short_Clean_Gameplay.mp4"
],check=True)

subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","Reddit_Story_Short_Clean_Gameplay.mp4",
    "-vf","fps=1/5,scale=270:-2,tile=3x3","-frames:v","1","qa_sheet_v3.jpg"
],check=True)
print(subprocess.check_output([
    "ffprobe","-v","error","-show_entries","format=duration,size","-of","default=nw=1",
    "Reddit_Story_Short_Clean_Gameplay.mp4"
]).decode())
