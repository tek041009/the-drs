from playwright.sync_api import sync_playwright
import shutil, os, time, random, subprocess

URL="http://127.0.0.1:8000/"
with sync_playwright() as p:
    browser=p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--use-gl=swiftshader",
            "--enable-webgl",
            "--ignore-gpu-blocklist",
            "--enable-unsafe-swiftshader",
        ],
    )
    ctx=browser.new_context(
        viewport={"width":720,"height":1280},
        record_video_dir="recordings",
        record_video_size={"width":720,"height":1280},
    )
    page=ctx.new_page()
    page.goto(URL,wait_until="networkidle",timeout=60000)
    page.add_style_tag(content="""
      html,body{margin:0!important;overflow:hidden!important}
      button,#center-panel,.mobile-controls{display:none!important}
    """)
    page.wait_for_timeout(1800)
    # Start the run, then keep it moving with lane changes, jumps and slides.
    page.keyboard.press("r")
    page.wait_for_timeout(900)
    seq=["ArrowLeft","ArrowUp","ArrowRight","ArrowDown","ArrowRight","ArrowUp","ArrowLeft","ArrowDown"]
    for i in range(52):
        page.keyboard.press(seq[i%len(seq)])
        page.wait_for_timeout(700)
    page.wait_for_timeout(1200)
    vid=page.video
    ctx.close()
    raw=vid.path()
    browser.close()

shutil.copy2(raw,"runner_raw.webm")
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","runner_raw.webm",
    "-vf","fps=30,scale=720:1280:flags=lanczos",
    "-t","38","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
    "-an","runner.mp4"
],check=True)
print("runner bytes",os.path.getsize("runner.mp4"))
