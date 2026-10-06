from pathlib import Path
import sys
from pytubefix import YouTube

if len(sys.argv) != 2:
    raise SystemExit("usage: download_fallback.py <url>")

url = sys.argv[1].strip()
out = Path("output")
out.mkdir(exist_ok=True)

yt = YouTube(url)
stream = (
    yt.streams
    .filter(progressive=True, file_extension="mp4")
    .order_by("resolution")
    .desc()
    .first()
)
if stream is None:
    raise RuntimeError("No progressive MP4 stream found")

path = stream.download(output_path=str(out), filename="downloaded.mp4")
print(path)
