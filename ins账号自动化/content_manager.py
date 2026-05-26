import json
import random
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from .config import BASE_DIR, HASHTAGS, POST_INTERVAL_DAYS, POST_WINDOW_START, POST_WINDOW_END

QUEUE_FILE = BASE_DIR / "post_queue.json"
SCHEDULE_FILE = BASE_DIR / "next_post.json"

PRODUCT_TYPES = [
    "frying pan", "cast iron pot", "kitchen knife", "cutting board",
    "non-stick pan", "saucepan", "casserole dish", "whisk",
    "spatula", "measuring cup", "colander", "peeler"
]

SCENE_TEMPLATES = [
    "Photorealistic Instagram flat lay of a {product} on a marble countertop, soft natural window light, top-down angle, shallow depth of field, warm cozy aesthetic, 4K",
    "DSLR photo of a {product} on a wooden kitchen table, morning sunlight streaming in, film grain, candid lifestyle shot, aesthetic kitchen vibe",
    "Realistic close-up of a {product} with fresh ingredients, soft diffused lighting, cream tones, minimalist composition, Instagram food photography style",
    "Steam rising from {food} cooking in a {product}, golden hour lighting, cozy home kitchen atmosphere, photorealistic, warm tones, shallow dof",
    "Minimalist kitchen corner with a {product}, muted earth tones, natural texture, soft shadows, hygge aesthetic, high quality photography",
    "Farmhouse style kitchen with a {product} on the counter, fresh flowers nearby, bright airy room, authentic lifestyle photo, warm sunlight",
    "{food} being prepared with a {product}, hands in frame, action shot, warm kitchen lighting, candid moment, realistic texture, IG aesthetic",
    "A {product} arranged with fresh herbs and ingredients, wooden board, natural green tones, soft window light, culinary photography, deep shadows",
]

FOOD_PAIRS = {
    "frying pan": "fried eggs and vegetables",
    "cast iron pot": "stew with herbs",
    "kitchen knife": "freshly chopped herbs and tomatoes",
    "cutting board": "arranged fruits and cheese",
    "non-stick pan": "golden pancakes",
    "saucepan": "creamy soup with garnish",
    "casserole dish": "baked pasta with cheese",
    "whisk": "fluffy pancake batter",
    "spatula": "flipping pancakes",
    "measuring cup": "measured flour and sugar",
    "colander": "freshly washed berries",
    "peeler": "curly carrot ribbons",
}

def get_post_queue() -> list[dict]:
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE) as f:
            return json.load(f)
    return []

def save_queue(queue: list[dict]):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

def generate_prompt(product: str | None = None) -> tuple[str, str]:
    product = product or random.choice(PRODUCT_TYPES)
    food = FOOD_PAIRS.get(product, "delicious home-cooked meal")
    template = random.choice(SCENE_TEMPLATES)
    if "{food}" in template:
        prompt = template.format(product=product, food=food)
    else:
        prompt = template.format(product=product)
    return prompt, product

def build_caption(text: str, product: str) -> str:
    tags = " ".join(random.sample(HASHTAGS, min(5, len(HASHTAGS))))
    return f"{text}\n.\n.\n{tags}"

def queue_next_post(caption_text: str, product: str, image_path: str):
    queue = get_post_queue()
    entry = {
        "image_path": image_path,
        "caption": build_caption(caption_text, product),
        "product": product,
        "created": datetime.now().isoformat(),
    }
    queue.append(entry)
    save_queue(queue)
    print(f"Queued: {product} -> {image_path}")

def pop_next_post() -> dict | None:
    queue = get_post_queue()
    if not queue:
        return None
    post = queue.pop(0)
    save_queue(queue)
    return post

def random_post_time() -> datetime:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE) as f:
            data = json.load(f)
        last_post = datetime.fromisoformat(data["last_post"])
        target_day = last_post + timedelta(days=POST_INTERVAL_DAYS)
    else:
        target_day = today

    hour = secrets.randbelow(POST_WINDOW_END - POST_WINDOW_START + 1) + POST_WINDOW_START
    minute = secrets.randbelow(60)
    target = target_day.replace(hour=hour, minute=minute)

    if target < datetime.now():
        target_day = target_day + timedelta(days=POST_INTERVAL_DAYS)
        hour = secrets.randbelow(POST_WINDOW_END - POST_WINDOW_START + 1) + POST_WINDOW_START
        minute = secrets.randbelow(60)
        target = target_day.replace(hour=hour, minute=minute)

    return target

def save_last_post():
    with open(SCHEDULE_FILE, "w") as f:
        json.dump({"last_post": datetime.now().isoformat()}, f)

def next_post_delay() -> float:
    target = random_post_time()
    delta = (target - datetime.now()).total_seconds()
    print(f"Next post at {target.strftime('%Y-%m-%d %H:%M')} (in {delta/3600:.1f}h)")
    return max(delta, 0)
