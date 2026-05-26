import sys
import time

from .config import POST_INTERVAL_DAYS
from .image_gen import generate_image, generate_caption
from .insta_bot import login, post_photo
from .content_manager import generate_prompt, queue_next_post, pop_next_post, next_post_delay, save_last_post

def generate_and_queue(count: int = 5):
    print(f"Generating {count} posts...")
    for i in range(count):
        prompt, product = generate_prompt()
        print(f"[{i+1}/{count}] Generating: {product}")
        path = generate_image(prompt)
        if not path:
            print("  Failed, skipping")
            continue
        caption = generate_caption(product, "casual")
        queue_next_post(caption, product, path)
        time.sleep(3)
    print("Done generating")

def post_from_queue(count: int = 1):
    cl = login()
    for _ in range(count):
        post = pop_next_post()
        if not post:
            print("Queue is empty")
            break
        success = post_photo(post["image_path"], post["caption"])
        if success:
            print(f"Posted: {post['product']}")
        time.sleep(30)
    cl.logout()

def generate_and_post(count: int = 1):
    cl = login()
    for i in range(count):
        prompt, product = generate_prompt()
        print(f"[{i+1}/{count}] Generating + posting: {product}")
        path = generate_image(prompt)
        if not path:
            print("  Failed, skipping")
            continue
        caption = generate_caption(product, "casual")
        success = post_photo(path, caption)
        if success:
            print(f"Posted: {product}")
        time.sleep(10)
    cl.logout()

def run_scheduler():
    print(f"Auto poster started. Posting every {POST_INTERVAL_DAYS} days, random time 16:00-23:59")
    while True:
        delay = next_post_delay()
        time.sleep(delay)
        print(f"Posting now...")
        generate_and_post(1)
        save_last_post()
