"""Cut each register spread into four overlapping crops (left/right page, top/bottom) for reading.
usage: crops.py <pages dir> <crops dir> <first> <last>"""
import os, sys
from PIL import Image
src, dst, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
os.makedirs(dst, exist_ok=True)
for n in range(a, b + 1):
    p = f"{src}/{n:04d}.jpg"
    if not os.path.exists(p): continue
    im = Image.open(p).convert("L")
    W, H = im.size
    mid = W // 2
    for side, (x0, x1) in (("L", (0, mid + 60)), ("R", (mid - 60, W))):
        for part, (y0, y1) in (("1", (0, int(H * 0.56))), ("2", (int(H * 0.44), H))):
            im.crop((x0, y0, x1, y1)).save(f"{dst}/{n:04d}_{side}{part}.jpg", quality=88)
print("done")
