"""
colour_engine.py — Colour science engine for Flask app
Handles dominant colour extraction, Pantone matching, CMYK, HEX,
colour harmonies + smart recommendations
"""

import math
import io
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

# ── Pantone Database ───────────────────────────────────────────
PANTONE_DB = [
    {"name": "Pantone 2727 C", "hex": "#4066E0", "r": 64, "g": 102, "b": 224},
    {"name": "Pantone 072 C", "hex": "#0A1FCE", "r": 10, "g": 31, "b": 206},
    {"name": "Pantone Reflex Blue C", "hex": "#001489", "r": 0, "g": 20, "b": 137},
    {"name": "Pantone 279 C", "hex": "#4B9CD3", "r": 75, "g": 156, "b": 211},
    {"name": "Pantone 285 C", "hex": "#0065BD", "r": 0, "g": 101, "b": 189},
    {"name": "Pantone Black C", "hex": "#2C2A29", "r": 44, "g": 42, "b": 41},
    {"name": "Pantone White", "hex": "#F4F5F0", "r": 244, "g": 245, "b": 240},
]

# ── 1. Extract dominant colours (Improved) ─────────────────────
def extract_dominant_colors(image_bytes: bytes, count: int = 6) -> list:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((150, 150), Image.LANCZOS)

    pixels = np.array(img).reshape(-1, 3)

    # ❗ Remove near white & black (important fix)
    filtered = []
    for p in pixels:
        if not (all(p > 240) or all(p < 15)):  # ignore white & black
            filtered.append(p)

    if len(filtered) == 0:
        filtered = pixels

    pixels = np.array(filtered).astype(float)

    k = min(count, len(pixels))
    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    km.fit(pixels)

    labels, counts = np.unique(km.labels_, return_counts=True)
    order = np.argsort(-counts)

    result = []
    for idx in order:
        c = km.cluster_centers_[idx]
        r, g, b = int(c[0]), int(c[1]), int(c[2])
        result.append({"r": r, "g": g, "b": b, "hex": rgb_to_hex(r, g, b)})

    return result

# ── 2. Pantone Match ───────────────────────────────────────────
def find_closest_pantone(r, g, b):
    best, best_d = PANTONE_DB[0], float("inf")
    for p in PANTONE_DB:
        d = math.sqrt((r-p["r"])**2 + (g-p["g"])**2 + (b-p["b"])**2)
        if d < best_d:
            best_d, best = d, p
    return {
        "name": best["name"],
        "hex": best["hex"],
        "cmyk": rgb_to_cmyk(best["r"], best["g"], best["b"])
    }

# ── 3. RGB → CMYK ─────────────────────────────────────────────
def rgb_to_cmyk(r, g, b):
    R, G, B = r/255, g/255, b/255
    k = 1 - max(R, G, B)
    if k == 1:
        return {"c":0,"m":0,"y":0,"k":100}
    return {
        "c": round(((1-R-k)/(1-k))*100),
        "m": round(((1-G-k)/(1-k))*100),
        "y": round(((1-B-k)/(1-k))*100),
        "k": round(k*100)
    }

# ── 4. RGB → HEX ─────────────────────────────────────────────
def rgb_to_hex(r,g,b):
    return "#{:02X}{:02X}{:02X}".format(r,g,b)

# ── 5. RGB ↔ HSL ─────────────────────────────────────────────
def rgb_to_hsl(r,g,b):
    R,G,B = r/255,g/255,b/255
    hi,lo = max(R,G,B), min(R,G,B)
    l = (hi+lo)/2
    if hi==lo:
        return 0,0,l
    d = hi-lo
    s = d/(2-hi-lo) if l>0.5 else d/(hi+lo)
    if hi==R:
        h = ((G-B)/d + (6 if G<B else 0))/6
    elif hi==G:
        h = ((B-R)/d + 2)/6
    else:
        h = ((R-G)/d + 4)/6
    return h*360,s,l

def hsl_to_rgb(h,s,l):
    def f(n):
        k=(n+h/30)%12
        a=s*min(l,1-l)
        return l - a*max(min(k-3,9-k,1),-1)
    return int(f(0)*255), int(f(8)*255), int(f(4)*255)

# ── 6. Harmony ───────────────────────────────────────────────
def generate_harmony(r,g,b):
    h,s,l = rgb_to_hsl(r,g,b)
    variants=[
        ("Complementary",(h+180)%360,s,l),
        ("Analogous+30",(h+30)%360,s,l),
        ("Analogous-30",(h-30)%360,s,l)
    ]
    out=[]
    for label,hh,ss,ll in variants:
        cr,cg,cb = hsl_to_rgb(hh,ss,ll)
        out.append({"label":label,"hex":rgb_to_hex(cr,cg,cb)})
    return out

# ── 7. ⭐ Recommendations ─────────────────────────────────────
def recommend_palettes(r,g,b):
    h,s,l = rgb_to_hsl(r,g,b)

    recs=[]

    # Vibrant
    vr,vg,vb = hsl_to_rgb(h, min(s+0.2,1), l)
    recs.append({
        "type":"Vibrant",
        "hex":rgb_to_hex(vr,vg,vb),
        "reason":"More eye-catching"
    })

    # Soft
    sr,sg,sb = hsl_to_rgb(h, max(s-0.2,0), min(l+0.1,1))
    recs.append({
        "type":"Professional",
        "hex":rgb_to_hex(sr,sg,sb),
        "reason":"Clean corporate feel"
    })

    # Contrast
    cr,cg,cb = hsl_to_rgb((h+180)%360, s, l)
    recs.append({
        "type":"Contrast",
        "hex":rgb_to_hex(cr,cg,cb),
        "reason":"High visibility"
    })

    return recs

# ── 8. Full Bundle ───────────────────────────────────────────
def full_match(r,g,b):
    return {
        "hex": rgb_to_hex(r,g,b),
        "rgb": {"r":r,"g":g,"b":b},
        "pantone": find_closest_pantone(r,g,b),
        "cmyk": rgb_to_cmyk(r,g,b),
        "harmony": generate_harmony(r,g,b),
        "recommendations": recommend_palettes(r,g,b)
    }