from PIL import Image, ImageDraw, ImageFont
import subprocess, textwrap, os, re

W,H = 1080,1920
DUR = 31.190204
TITLE = "AITA for telling my son and his fiance I won't pay for the wedding if I can't invite some family members"

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Reddit-style headline card, using only real story info — no invented votes/comments/usernames.
card = Image.new("RGBA",(960,560),(0,0,0,0))
d = ImageDraw.Draw(card)
d.rounded_rectangle((14,18,946,548),radius=42,fill=(18,18,20,245))
d.rounded_rectangle((14,18,946,548),radius=42,outline=(255,255,255,40),width=2)
d.ellipse((56,52,116,112),fill=(255,69,0,255))
icon = ImageFont.truetype(FONT_BOLD,34)
d.text((74,57),"r",font=icon,fill="white")
meta = ImageFont.truetype(FONT_BOLD,30)
small = ImageFont.truetype(FONT_REG,24)
title_font = ImageFont.truetype(FONT_BOLD,48)
d.text((136,54),"r/BORUpdates",font=meta,fill=(245,245,245,255))
d.text((136,92),"AITA",font=small,fill=(176,176,182,255))
d.rounded_rectangle((56,140,182,186),radius=16,fill=(255,69,0,255))
tag = ImageFont.truetype(FONT_BOLD,23)
d.text((78,149),"AITA",font=tag,fill="white")

def wrap_px(text, font, maxw):
    words=text.split()
    lines=[]; cur=""
    for w in words:
        test=(cur+" "+w).strip()
        if d.textbbox((0,0),test,font=font)[2] <= maxw:
            cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

lines=wrap_px(TITLE,title_font,830)
y=218
for line in lines[:5]:
    d.text((58,y),line,font=title_font,fill=(252,252,252,255))
    y += 61
d.text((58,500),"Original headline • story retold",font=small,fill=(170,170,176,255))
card.save("headline_card.png")

chunks = [
("My 26-year-old son",0),
("and his fiancée",0),
("just got engaged,",0),
("and I offered to pay",0),
("for the wedding.",0),
("I only had TWO CONDITIONS:",1),
("use a wedding planner,",0),
("and let me invite",0),
("EIGHT OLDER RELATIVES",1),
("I'm close to.",0),
("They agreed to the planner...",0),
("but his fiancée says",0),
("I SHOULDN'T GET TO INVITE ANYONE.",1),
("So I told them,",0),
("if I'm paying",0),
("for the whole wedding,",0),
("those EIGHT GUESTS",1),
("are part of the deal.",0),
("Now they're saying",0),
("I'm CONTROLLING",1),
("and threatening to reject",0),
("the money entirely.",0),
("BE HONEST:",1),
("am I wrong",0),
("for attaching guest-list conditions",0),
("to paying for the wedding?",1),
]

def weight(text):
    n=len(text.split())
    p=0
    if "..." in text: p+=1.2
    elif text.endswith((".", "?", ":")): p+=0.62
    elif text.endswith(","): p+=0.28
    return n+p

weights=[weight(t) for t,_ in chunks]
usable=DUR-0.18
scale=usable/sum(weights)
times=[]
cur=0.06
for (txt,hot),wt in zip(chunks,weights):
    dt=wt*scale
    times.append((cur,min(DUR-0.03,cur+dt),txt,hot))
    cur+=dt

def at(t):
    h=int(t//3600); t-=h*3600
    m=int(t//60); t-=m*60
    s=int(t); cs=int(round((t-s)*100))
    if cs>=100: s+=1; cs-=100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

with open("captions.ass","w",encoding="utf-8") as f:
    f.write("""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Main,DejaVu Sans,76,&H00FFFFFF,&H00FFFFFF,&H00101012,&H00000000,-1,0,0,0,100,100,0,0,1,6,2,5,70,70,0,1
Style: Hot,DejaVu Sans,82,&H0000D7FF,&H0000D7FF,&H00101012,&H00000000,-1,0,0,0,100,100,0,0,1,7,2,5,65,65,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
    for st,en,txt,hot in times:
        style="Hot" if hot else "Main"
        safe=txt.replace("{","").replace("}","")
        f.write(f"Dialogue: 3,{at(st)},{at(en)},{style},,0,0,0,,{{\\pos(540,1125)}}{safe}\n")

# Final composite. Background audio is discarded: approved narration is the ONLY audio.
filter_complex = (
    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
    "crop=1080:1920,fps=30[bg];"
    "[2:v]format=rgba,fade=t=in:st=0:d=0.15:alpha=1,"
    "fade=t=out:st=5.15:d=0.25:alpha=1[card];"
    "[bg][card]overlay=(W-w)/2:135:enable='between(t,0,5.4)'[hook];"
    "[hook]ass=captions.ass[v]"
)
subprocess.run([
    "ffmpeg","-y","-loglevel","error",
    "-ss","20","-stream_loop","-1","-i","gameplay.mp4",
    "-i","approved_voice.mp3",
    "-loop","1","-framerate","30","-i","headline_card.png",
    "-filter_complex",filter_complex,
    "-map","[v]","-map","1:a:0",
    "-t",f"{DUR:.3f}",
    "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
    "-c:a","aac","-b:a","192k","-ar","48000",
    "-movflags","+faststart",
    "Reddit_Story_V2_POSTABLE.mp4"
],check=True)

# QA sheet: 8 frames across the full short.
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","Reddit_Story_V2_POSTABLE.mp4",
    "-vf","fps=1/4,scale=270:480,tile=4x2",
    "-frames:v","1","qa_sheet.jpg"
],check=True)

# Audio/video technical checks.
subprocess.run([
    "ffprobe","-v","error","-show_entries",
    "format=duration,size:stream=index,codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
    "-of","json","Reddit_Story_V2_POSTABLE.mp4"
],check=True)
