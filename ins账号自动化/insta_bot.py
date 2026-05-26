from instagrapi import Client
from .config import IG_USERNAME, IG_PASSWORD, BASE_DIR
from pathlib import Path
import json

SESSION_FILE = BASE_DIR / "ig_session.json"
cl = Client()

def _create_client() -> Client:
    c = Client()
    c.set_user_agent(
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro Build/UQ1A.240205.004; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/122.0.6261.64 Mobile Safari/537.36"
    )
    c.set_device({
        "manufacturer": "Google",
        "model": "Pixel 8 Pro",
        "android_version": 28,
        "android_release": "9.0",
        "dpi": "420dpi",
        "resolution": "1080x1920",
        "chipset": "qcom",
    })
    return c

def login() -> Client:
    global cl

    if SESSION_FILE.exists():
        try:
            c = _create_client()
            c.load_settings(str(SESSION_FILE))
            c.login(IG_USERNAME, IG_PASSWORD)
            c.get_timeline_feed()
            cl = c
            print(f"Logged in with saved session: @{IG_USERNAME}")
            return cl
        except Exception as e:
            print(f"Session expired: {e}, re-logging...")
            SESSION_FILE.unlink(missing_ok=True)

    c = _create_client()

    print("\n尝试账号密码登录...")
    try:
        c.login(IG_USERNAME, IG_PASSWORD)
        c.get_timeline_feed()
        c.dump_settings(str(SESSION_FILE))
        cl = c
        print(f"Logged in as @{IG_USERNAME}")
        return cl
    except Exception as e:
        print(f"账号密码登录失败: {e}")

    print("\n改用 sessionid 方式")
    print("1. 用电脑浏览器 (Chrome/Edge) 打开 instagram.com")
    print("2. 登录你的账号")
    print("3. 按 F12 → Application → Cookies → instagram.com")
    print("4. 找到 sessionid 那一行，复制它的 Value\n")
    session_id = input("粘贴 sessionid 到这里: ").strip()

    if not session_id:
        print("未输入 sessionid，退出")
        raise Exception("Login cancelled")

    try:
        c.login_by_sessionid(session_id)
        c.get_timeline_feed()
        c.dump_settings(str(SESSION_FILE))
        cl = c
        print(f"Logged in as @{IG_USERNAME}")
        return cl
    except Exception as e:
        print(f"Session login failed: {e}")
        raise

def post_photo(image_path: str, caption: str) -> bool:
    for attempt in range(2):
        try:
            result = cl.photo_upload(image_path, caption)
            print(f"Posted: {image_path}")
            return bool(result)
        except Exception as e:
            err = str(e)
            if "login_required" in err and attempt == 0:
                print("Session invalid, re-logging...")
                SESSION_FILE.unlink(missing_ok=True)
                login()
            else:
                print(f"Post failed: {e}")
                return False
    return False

def post_carousel(image_paths: list[str], caption: str) -> bool:
    try:
        result = cl.album_upload(image_paths, caption)
        print(f"Carousel posted with {len(image_paths)} images")
        return bool(result)
    except Exception as e:
        print(f"Carousel failed: {e}")
        return False
