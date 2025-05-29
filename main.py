from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import base64
import os
from io import BytesIO
from PIL import Image
import openai

app = FastAPI()

STATIC_DIR = "static"
TEMPLATES_DIR = "templates"
UPLOAD_DIR = "uploads"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/convert")
async def convert_to_latex(request: Request):
    try:
        data = await request.json()
        image_data = data.get("image_data")
        macros = data.get("macros", "")  # Optional macros from user
        prompt = data.get("prompt", "")  # Optional prompt from user

        if not image_data:
            return JSONResponse(status_code=400, content={"error": "No image data provided"})

        # データURIからbase64部分のみ抽出し、画像読み込み
        header, encoded = image_data.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        img = Image.open(BytesIO(img_bytes)).convert("RGBA")

        # 背景白に合成
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        combined = Image.alpha_composite(background, img).convert("RGB")

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filepath = os.path.join(UPLOAD_DIR, "drawn.png")
        combined.save(filepath)

        # base64に再エンコード
        with open(filepath, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode()

        try:
            # OpenAI Chat Completions API呼び出し
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "This is a hand-drawn mathematical expression. "
                                    "Please extract only the mathematical expression from the image and return it as raw LaTeX code, without any explanations or markdown formatting such as ```latex. "
                                    "Do not include any explanation. If there is noise or unrecognizable parts, omit them. "
                                    "Use standard LaTeX formatting. Assume the image contains only one expression. "
                                    f"If any LaTeX macro definitions are provided separately, you may assume they are pre-defined and can be used as-is in the expression. Here are the defined macros: {macros}"
                                )+prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=512,
            )

            latex_code = response.choices[0].message.content.strip()
            full_latex = macros + "\n" + latex_code
            return {"latex": latex_code, "full_latex": full_latex}

        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
