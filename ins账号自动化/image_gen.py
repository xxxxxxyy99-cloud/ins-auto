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

CAPTION_TEMPLATES = {
    "casual": (
        "Write a short Instagram caption for a {product} kitchenware post. "
        "Tone: friendly, casual, warm. Include 2 emojis. "
        "Mention how it makes cooking easier or more enjoyable. "
        "Keep under 150 characters. Do NOT include hashtags."
    ),
    "educational": (
        "Write a short Instagram caption for a {product}. "
        "Tone: helpful, informative. Include 1 tip about using this tool. "
        "Include 2 relevant emojis. Keep under 150 characters. No hashtags."
    ),
    "sale": (
        "Write a short Instagram caption for a {product}. "
        "Tone: exciting, persuasive. Create urgency or highlight a benefit. "
        "Include 2 emojis. Keep under 150 characters. No hashtags."
    ),
}

FALLBACK_CAPTIONS = {
    "frying pan": "Perfectly golden, every time 🍳✨",
    "cast iron pot": "Slow-cooked to perfection 🥘🔥",
    "kitchen knife": "Sharp precision, effortless cuts 🔪✨",
    "cutting board": "The foundation of every great meal 🥗",
    "non-stick pan": "No sticky situations here 🥞✨",
    "saucepan": "Simmer something amazing 🍲",
    "casserole dish": "Baked with love 🧡",
    "whisk": "Whip it good! 🥣",
    "spatula": "Flip with confidence 🥞",
    "measuring cup": "Perfect measurements, perfect results 📏",
    "colander": "Fresh and clean, every time 🫐",
    "peeler": "Peel like a pro 🥕",
    "saucepan": "Simmer something amazing 🍲",
}

def generate_caption(product_type: str, style: str = "casual") -> str:
    prompt_template = CAPTION_TEMPLATES.get(style, CAPTION_TEMPLATES["casual"])
    prompt = prompt_template.format(product=product_type)

    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100,
    }
    try:
        resp = requests.post(CAPTION_URL, headers=CAPTION_HEADERS, json=payload, timeout=15)
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            if text:
                return text
        else:
            print(f"  Caption API error {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"  Caption API failed: {e}")

    return FALLBACK_CAPTIONS.get(product_type, "Upgrade your kitchen game! 🔪✨")
