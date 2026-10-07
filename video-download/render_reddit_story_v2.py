from PIL import Image
import subprocess, os

W,H = 1080,1920
DUR = 31.19

# Use the REAL Reddit screenshot captured by the workflow.
raw = Image.open("reddit_post_raw.png").convert("RGB")
# Keep the genuine top of the post (subreddit/title area) rather than recreating it.
top_h = min(raw.height, 700)
shot = raw.crop((0, 0, raw.width, top_h))
ratio = min(960 / shot.width, 500 / shot.height)
shot = shot.resize((int(shot.width*ratio), int(shot.height*ratio)), Image.Resampling.LANCZOS)
shot.save("reddit_post.png", quality=94)

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
scale=(DUR-0.20)/sum(weights)
times=[]
cur=0.07
for (txt,hot),wt in zip(chunks,weights):
    dt=wt*scale
    times.append((cur,min(DUR-0.04,cur+dt),txt,hot))
    cur += dt

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
Style: Main,DejaVu Sans,68,&H00FFFFFF,&H00FFFFFF,&H00101012,&H00000000,-1,0,0,0,100,100,0,0,1,5,2,5,85,85,0,1
Style: Hot,DejaVu Sans,72,&H0000D7FF,&H0000D7FF,&H00101012,&H00000000,-1,0,0,0,100,100,0,0,1,6,2,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
    for st,en,txt,hot in times:
        style="Hot" if hot else "Main"
        safe=txt.replace("{","").replace("}","")
        # Upper-middle: clear of Reddit screenshot above and the Subway character below.
        f.write(f"Dialogue: 3,{at(st)},{at(en)},{style},,0,0,0,,{{\\pos(540,860)}}{safe}\n")

filter_complex = (
    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
    "crop=1080:1920,fps=30[bg];"
    "[2:v]format=rgba,fade=t=in:st=0:d=0.12:alpha=1,"
    "fade=t=out:st=5.35:d=0.22:alpha=1[shot];"
    "[bg][shot]overlay=(W-w)/2:70:enable='between(t,0,5.6)'[hook];"
    "[hook]ass=captions.ass[v]"
)

subprocess.run([
    "ffmpeg","-y","-loglevel","error",
    "-ss","18","-stream_loop","-1","-i","gameplay.mp4",
    "-i","approved_voice.mp3",
    "-loop","1","-framerate","30","-i","reddit_post.png",
    "-filter_complex",filter_complex,
    "-map","[v]","-map","1:a:0",
    "-t",f"{DUR:.3f}",
    "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",
    "-c:a","aac","-b:a","192k","-ar","48000",
    "-movflags","+faststart",
    "Reddit_Story_V2_POSTABLE.mp4"
],check=True)

# Smaller QA copy for quick review/download.
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","Reddit_Story_V2_POSTABLE.mp4",
    "-vf","scale=540:960","-r","24",
    "-c:v","libx264","-preset","medium","-crf","27",
    "-c:a","aac","-b:a","128k","-movflags","+faststart",
    "Reddit_Story_V2_QA.mp4"
],check=True)

subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","Reddit_Story_V2_POSTABLE.mp4",
    "-vf","fps=1/4,scale=270:480,tile=4x2",
    "-frames:v","1","qa_sheet.jpg"
],check=True)

subprocess.run([
    "ffprobe","-v","error","-show_entries",
    "format=duration,size:stream=index,codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
    "-of","json","Reddit_Story_V2_QA.mp4"
],check=True)
