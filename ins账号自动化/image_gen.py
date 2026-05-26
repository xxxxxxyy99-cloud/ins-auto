import requests
import hashlib
import time
from pathlib import Path
from urllib.parse import quote
from .config import OPENROUTER_API_KEY, IMAGE_DIR

CAPTION_URL = "https://openrouter.ai/api/v1/chat/completions"
CAPTION_HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

def _save_image(data: bytes, prompt: str) -> str:
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
    filename = f"{prompt_hash}_{int(time.time())}.jpg"
    filepath = IMAGE_DIR / filename
    with open(filepath, "wb") as f:
        f.write(data)
    print(f"Image saved: {filepath}")
    return str(filepath)

def generate_image(prompt: str, aspect_ratio: str = "4:5", size: str = "1080x1350") -> str | None:
    w, h = size.split("x") if "x" in size else ("1080", "1350")
    url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width={w}&height={h}"
    resp = requests.get(url, timeout=60)
    if resp.status_code != 200:
        print(f"API error {resp.status_code}: {resp.text[:200]}")
        return None
    return _save_image(resp.content, prompt)

def generate_caption(product_type: str, style: str = "casual") -> str:
    prompt = (
        f"Write a short Instagram caption (under 150 chars) for a {product_type} "
        f"kitchenware post. Style: {style}, friendly, include 2-3 relevant emojis. "
        f"Do NOT include hashtags. Just the caption text."
    )
    payload = {
        "model": "openai/gpt-5-mini",
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post(CAPTION_URL, headers=CAPTION_HEADERS, json=payload)
    if resp.status_code != 200:
        return "Check out our latest kitchenware! #kitchenlife"
    try:
        return resp.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        return "New kitchenware alert! Upgrade your cooking game."
