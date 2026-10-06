import json, sys
p=sys.argv[1] if len(sys.argv)>1 else "workflow.json"
with open(p,"r",encoding="utf-8") as f:
    w=json.load(f)

nodes={n["id"]:n for n in w["nodes"]}

prompt=(
"High-end cinematic stylized 3D animated feature-film shot, 1925 Paris at golden hour. "
"A handsome European con man in his late thirties wearing a tailored dark 1920s suit, cream shirt, tie and fedora walks confidently down a bustling Paris boulevard toward camera. "
"Period cars move naturally behind him, pedestrians cross the pavement, warm shop windows glow, the Eiffel Tower is visible in the hazy distance. "
"Expressive but believable character animation, detailed face and clothing, rich materials, soft global illumination, atmospheric depth, cinematic depth of field. "
"The camera tracks backward smoothly at chest height while he walks; subtle handheld life, natural cloth motion and secondary motion. "
"Premium theatrical 3D animation, sophisticated composition, realistic proportions, vivid but tasteful colour, polished studio lighting, no text."
)
neg=("low quality, cheap game graphics, low poly, blocky, flat shading, plastic toy, slideshow, powerpoint, "
     "static image, jitter, flicker, warped face, deformed hands, extra limbs, bad anatomy, blurry, noisy, text, watermark")

# Prompt nodes
nodes[6]["widgets_values"]=[prompt]
nodes[7]["widgets_values"]=[neg]

# Use quantized text encoder through CLIPLoaderGGUF node 87.
nodes[87]["widgets_values"]=["t5-v1_1-xxl-encoder-Q3_K_S.gguf","ltxv"]
# Main diffusion model: quantized distilled 2B.
nodes[78]["widgets_values"]=["ltxv-2b-0.9.6-distilled-04-25-Q4_K_S.gguf"]
# 512x288, 97 frames (~3.9 sec at 25 fps)
nodes[70]["widgets_values"]=[512,288,97,1]
# 8-step distilled schedule retained
nodes[71]["widgets_values"]=[8,2.05,0.95,True,0.1]
# Save at 25fps
nodes[86]["widgets_values"]=["rarely_told_v4_test","vp9",25.0,24]

# Rewire CLIP links 188/189 from node 81 to node 87.
for link in w["links"]:
    if link[0] in (188,189):
        link[1]=87
        link[2]=0
# Ensure node 87 output advertises links.
nodes[87]["outputs"][0]["links"]=[188,189]
nodes[81]["outputs"][0]["links"]=[]
# Remove the now-unused stock CLIP loader so strict local validation does not reject it.
w["nodes"]=[n for n in w["nodes"] if n["id"] != 81]
w["links"]=[ln for ln in w["links"] if ln[1] != 81 and ln[3] != 81]

with open(p,"w",encoding="utf-8") as f:
    json.dump(w,f,separators=(",",":"))
print("patched",p)
