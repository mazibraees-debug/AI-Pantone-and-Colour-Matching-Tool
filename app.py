from flask import Flask, render_template, request
from colour_engine import extract_dominant_colors, full_match
import base64

app = Flask(__name__, template_folder="templates", static_folder="static")

@app.route('/')
def index():
    return render_template('index.html', colors=[], selected=None, match=None, image_url=None, error=None)

@app.route('/extract', methods=['POST'])
def extract():
    if 'image' not in request.files:
        return render_template('index.html', error="No image uploaded", colors=[], selected=None, match=None, image_url=None)

    file = request.files['image']

    if file.filename == '':
        return render_template('index.html', error="No image selected", colors=[], selected=None, match=None, image_url=None)

    try:
        img_bytes = file.read()

        # ✅ Base64 image (Vercel safe)
        encoded = base64.b64encode(img_bytes).decode('utf-8')
        image_url = f"data:image/png;base64,{encoded}"

        dominant_colors = extract_dominant_colors(img_bytes, count=6)
        colors = [full_match(c["r"], c["g"], c["b"]) for c in dominant_colors]

    except Exception as e:
        return render_template('index.html', error=f"Error: {e}", colors=[], selected=None, match=None, image_url=None)

    selected_color = colors[0] if colors else None

    return render_template(
        'index.html',
        colors=colors,
        selected=selected_color,
        match=selected_color,
        image_url=image_url,
        error=None
    )

@app.route('/manual', methods=['POST'])
def manual():
    colour_input = request.form.get('colour_input', '#000000')
    try:
        colour_input = colour_input.lstrip('#')
        r = int(colour_input[0:2], 16)
        g = int(colour_input[2:4], 16)
        b = int(colour_input[4:6], 16)
        selected_color = full_match(r, g, b)
    except:
        selected_color = full_match(0, 0, 0)

    return render_template(
        'index.html',
        colors=[],
        selected=selected_color,
        match=selected_color,
        image_url=None,
        error=None
    )