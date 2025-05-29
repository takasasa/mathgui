from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import base64
import os
from io import BytesIO
from PIL import Image
import openai
from dotenv import load_dotenv
import os
from pathlib import Path

# .env ファイルがある場合は読み込む（なければ無視）
env_path = Path("/app/.env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# 環境変数の取得（.env から or Render の設定から）
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set in environment or .env file")

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
                                    "Carefully determine whether each letter in the formula represents a scalar, vector, or matrix, based on the meaning of the formula."
                                    "For example:"
                                    "– A matrix multiplied by a vector should result in a vector."
                                    "– A matrix multiplied by a matrix should result in a matrix."
                                    "– A vector added to a vector should result in a vector."
                                    "– A matrix added to a matrix should result in a matrix."
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
