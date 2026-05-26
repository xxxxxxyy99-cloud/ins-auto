import cloudscraper
from bs4 import BeautifulSoup
import csv
import json
import random
import time
import re
from urllib.parse import urljoin, quote
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


class ECommerceSpider:
    """电商爬虫基类 - 支持 Cloudflare 反爬、随机延迟、重试、多格式导出"""

    def __init__(self, base_url, delay=(2, 4)):
        self.base_url = base_url
        self.scraper = cloudscraper.create_scraper()
        self.delay = delay
        self.session_cookies = {}
        self._warmup()

    def _warmup(self):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            resp = self.scraper.get(self.base_url, headers=headers, timeout=15)
            self.session_cookies = dict(resp.cookies)
            self._random_delay()
        except Exception:
            pass

    def _random_delay(self, extra=0):
        time.sleep(random.uniform(*self.delay) + extra)

    def _headers(self, referer=None):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Referer": referer or self.base_url,
            "DNT": "1",
            "Connection": "keep-alive",
        }

    def _fetch(self, url, params=None, retries=3, referer=None):
        for attempt in range(retries):
            try:
                resp = self.scraper.get(
                    url, params=params, headers=self._headers(referer),
                    cookies=self.session_cookies, timeout=20
                )
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding
                return resp
            except Exception as e:
                print(f"  [重试 {attempt + 1}/{retries}] 请求失败: {e}")
                self._random_delay(extra=1)
        return None

    def _parse_price(self, text):
        if not text:
            return None
        cleaned = re.sub(r'[^\d.,]', '', text)
        cleaned = cleaned.replace(',', '')
        try:
            return round(float(cleaned), 2)
        except ValueError:
            return None

    def search_products(self, keyword, max_pages=1):
        raise NotImplementedError

    def parse_product(self, url):
        raise NotImplementedError

    def crawl(self, keyword, max_pages=1, output_file=None):
        if not output_file:
            safe_name = re.sub(r'[^\w]', '_', keyword)[:20]
            output_file = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        print(f"[开始] 平台: {self.__class__.__name__}")
        print(f"[开始] 关键词: {keyword}, 页数: {max_pages}")

        urls = self.search_products(keyword, max_pages)
        print(f"[结果] 搜索到 {len(urls)} 个商品")

        products = []
        for i, url in enumerate(urls, 1):
            print(f"[进度] {i}/{len(urls)} 解析中...")
            product = self.parse_product(url)
            if product:
                products.append(product)
                print(f"  -> {product.get('title', 'N/A')[:40]} | {product.get('currency', '')}{product.get('price', 'N/A')}")
            self._random_delay()

        if products:
            self._save_csv(products, output_file)
            self._save_json(products, output_file.replace(".csv", ".json"))
            if pd:
                self._save_excel(products, output_file.replace(".csv", ".xlsx"))
            print(f"\n[完成] 成功导出 {len(products)} 条数据")
            print(f"       CSV:  {output_file}")
            print(f"       JSON: {output_file.replace('.csv', '.json')}")
            if pd:
                print(f"       XLSX: {output_file.replace('.csv', '.xlsx')}")
        else:
            print("[警告] 未获取到任何商品数据")

        return products

    def _save_csv(self, data, filename):
        keys = data[0].keys()
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)

    def _save_json(self, data, filename):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_excel(self, data, filename):
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False, engine="openpyxl")


# ═══════════════════════════════════════════
#  Amazon Spider
# ═══════════════════════════════════════════

class AmazonSpider(ECommerceSpider):
    """Amazon 商品爬虫 - 搜索 + 详情页解析"""

    def __init__(self, domain="com", delay=(3, 5)):
        base_url = f"https://www.amazon.{domain}"
        super().__init__(base_url, delay)
        self.domain = domain

    def search_products(self, keyword, max_pages=1):
        urls = []
        for page in range(1, max_pages + 1):
            params = {"k": keyword, "page": page}
            url = f"{self.base_url}/s"
            print(f"  搜索第 {page} 页...")
            resp = self._fetch(url, params=params, referer=self.base_url)
            if not resp:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            asin_pattern = re.compile(r'/dp/([A-Z0-9]{10})')
            for link in soup.select("a[href*='/dp/']"):
                href = link.get("href", "")
                m = asin_pattern.search(href)
                if m:
                    asin = m.group(1)
                    product_url = f"https://www.amazon.{self.domain}/dp/{asin}"
                    if product_url not in urls:
                        urls.append(product_url)

        return urls

    def parse_product(self, url):
        resp = self._fetch(url, referer=f"{self.base_url}/s")
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        product = {"url": url, "source": f"Amazon.{self.domain}", "scraped_at": datetime.now().isoformat()}

        title_el = soup.select_one("#productTitle")
        product["title"] = title_el.get_text(strip=True) if title_el else None

        price_el = soup.select_one(".a-price .a-offscreen") or soup.select_one("#corePrice_desktop .a-price .a-offscreen")
        if price_el:
            product["price"] = self._parse_price(price_el.get_text(strip=True))
        if not product.get("price"):
            price_whole = soup.select_one(".a-price-whole")
            price_frac = soup.select_one(".a-price-fraction")
            if price_whole:
                price_text = price_whole.get_text(strip=True)
                if price_frac:
                    price_text += "." + price_frac.get_text(strip=True)
                product["price"] = self._parse_price(price_text)

        currency_el = soup.select_one(".a-price-symbol")
        product["currency"] = currency_el.get_text(strip=True) if currency_el else "$"

        rating_el = soup.select_one("i.a-icon-star") or soup.select_one("i.a-icon-star-small")
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            m = re.search(r'([\d.]+)', rating_text)
            product["rating"] = float(m.group(1)) if m else None
        else:
            product["rating"] = None

        review_el = soup.select_one("#acrCustomerReviewText")
        if review_el:
            m = re.search(r'([\d,]+)', review_el.get_text(strip=True))
            product["review_count"] = int(m.group(1).replace(",", "")) if m else None
        else:
            product["review_count"] = None

        asin_m = re.search(r'/dp/([A-Z0-9]{10})', url)
        product["asin"] = asin_m.group(1) if asin_m else None

        brand_el = soup.select_one("#bylineInfo")
        product["brand"] = brand_el.get_text(strip=True).replace("Brand: ", "") if brand_el else None

        img_el = soup.select_one("#landingImage")
        product["main_image"] = img_el.get("src") if img_el else None

        desc_el = soup.select_one("#productDescription p")
        product["description"] = desc_el.get_text(strip=True)[:300] if desc_el else None

        availability_el = soup.select_one("#availability span")
        product["availability"] = availability_el.get_text(strip=True) if availability_el else None

        return product


# ═══════════════════════════════════════════
#  AliExpress Spider
# ═══════════════════════════════════════════

class AliExpressSpider(ECommerceSpider):
    """速卖通 (AliExpress) 商品爬虫"""

    def __init__(self, delay=(3, 5)):
        super().__init__("https://www.aliexpress.com", delay)

    def search_products(self, keyword, max_pages=1):
        urls = []
        for page in range(1, max_pages + 1):
            params = {
                "SearchText": keyword,
                "page": page,
                "spm": "a2g0o.productlist.search.0",
            }
            url = f"{self.base_url}/wholesale"
            print(f"  搜索第 {page} 页...")
            resp = self._fetch(url, params=params, referer=self.base_url)
            if not resp:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.select("a[href*='/item/']"):
                href = a.get("href", "")
                if "/item/" in href:
                    full_url = href if href.startswith("http") else urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)

            for a in soup.select("a[class*='product']"):
                href = a.get("href", "")
                if href and "/item/" in href:
                    full_url = href if href.startswith("http") else urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)

        return urls

    def parse_product(self, url):
        resp = self._fetch(url, referer=f"{self.base_url}/wholesale")
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        product = {"url": url, "source": "AliExpress", "scraped_at": datetime.now().isoformat()}

        title_el = soup.select_one("h1[class*='product-title']") or soup.select_one("[class*='product-title']") or soup.select_one("title")
        product["title"] = title_el.get_text(strip=True) if title_el else None
        if product["title"] and "aliexpress" in product["title"].lower():
            product["title"] = None

        price_el = soup.select_one("[class*='price']") or soup.select_one("span[class*='Price']")
        if price_el:
            product["price"] = self._parse_price(price_el.get_text(strip=True))
        product["currency"] = "$"

        rating_el = soup.select_one("[class*='rating']") or soup.select_one("[class*='score']")
        if rating_el:
            m = re.search(r'([\d.]+)', rating_el.get_text(strip=True))
            product["rating"] = float(m.group(1)) if m else None
        else:
            product["rating"] = None

        order_el = soup.select_one("[class*='order']") or soup.select_one("[class*='sold']")
        product["total_orders"] = order_el.get_text(strip=True) if order_el else None

        id_m = re.search(r'/item/(\d+)', url)
        product["item_id"] = id_m.group(1) if id_m else None

        img_el = soup.select_one("[class*='image'] img") or soup.select_one(".picture-box img")
        product["main_image"] = img_el.get("src") or img_el.get("data-src") if img_el else None

        desc_el = soup.select_one("[class*='description']") or soup.select_one("[class*='detail']")
        product["description"] = desc_el.get_text(strip=True)[:300] if desc_el else None

        return product


# ═══════════════════════════════════════════
#  TikTok Shop Spider (需要 Playwright)
# ═══════════════════════════════════════════

class TikTokShopSpider:
    """TikTok Shop 爬虫 - 需要 Playwright (JS 渲染)

    注意: TikTok Shop 内容完全由 JavaScript 渲染，
    必须使用浏览器自动化才能获取数据。
    已自动安装 Playwright + Chromium。
    """

    def __init__(self, delay=(3, 5), headless=True):
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("需要安装 Playwright: pip install playwright && playwright install chromium")
        self.delay = delay
        self.headless = headless

    def _random_delay(self):
        time.sleep(random.uniform(*self.delay))

    def _get_page_content(self, url):
        """使用 Playwright 获取 JS 渲染后的页面内容"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            page = context.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                self._random_delay()
                content = page.content()
                return content
            except Exception as e:
                print(f"  Playwright 加载失败: {e}")
                return None
            finally:
                browser.close()

    def search_products(self, keyword, max_pages=1):
        urls = []
        for page_num in range(1, max_pages + 1):
            url = f"https://shop.tiktok.com/search?q={quote(keyword)}"
            if page_num > 1:
                url += f"&page={page_num}"
            print(f"  搜索第 {page_num} 页...")
            html = self._get_page_content(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")

            for a in soup.select("a[href*='/product/']"):
                href = a.get("href", "")
                full_url = href if href.startswith("http") else urljoin("https://shop.tiktok.com", href)
                if full_url not in urls:
                    urls.append(full_url)

        return urls

    def parse_product(self, url):
        print(f"  解析商品详情...")
        html = self._get_page_content(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        product = {"url": url, "source": "TikTokShop", "scraped_at": datetime.now().isoformat()}

        title_el = soup.select_one("h1") or soup.select_one("[class*='title']") or soup.select_one("[class*='name']")
        product["title"] = title_el.get_text(strip=True) if title_el else None

        price_el = soup.select_one("[class*='price']") or soup.select_one("[class*='sale-price']")
        if price_el:
            product["price"] = self._parse_price(price_el.get_text(strip=True))
        product["currency"] = "$"

        product["description"] = None
        for sel in ["[class*='description']", "[class*='detail']", "[class*='info']"]:
            el = soup.select_one(sel)
            if el:
                product["description"] = el.get_text(strip=True)[:300]
                break

        img_el = soup.select_one("img[class*='main']") or soup.select_one("[class*='gallery'] img")
        product["main_image"] = img_el.get("src") if img_el else None

        return product

    def _parse_price(self, text):
        if not text:
            return None
        cleaned = re.sub(r'[^\d.,]', '', text)
        cleaned = cleaned.replace(',', '')
        try:
            return round(float(cleaned), 2)
        except ValueError:
            return None

    def crawl(self, keyword, max_pages=1, output_file=None):
        if not output_file:
            safe_name = re.sub(r'[^\w]', '_', keyword)[:20]
            output_file = f"tiktokshop_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        print(f"[开始] 平台: TikTokShop")
        print(f"[开始] 关键词: {keyword}, 页数: {max_pages}")
        print("[注意] 使用 Playwright 浏览器自动化，速度较慢...")

        urls = self.search_products(keyword, max_pages)
        print(f"[结果] 搜索到 {len(urls)} 个商品")

        products = []
        for i, url in enumerate(urls, 1):
            print(f"[进度] {i}/{len(urls)} 解析中...")
            product = self.parse_product(url)
            if product:
                products.append(product)
                print(f"  -> {product.get('title', 'N/A')[:40]} | ${product.get('price', 'N/A')}")
            self._random_delay()

        if products:
            self._save(products, output_file)
            print(f"\n[完成] 成功导出 {len(products)} 条数据到 {output_file}")
        else:
            print("[警告] 未获取到任何商品数据")

        return products

    def _save(self, data, filename):
        keys = data[0].keys()
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        with open(filename.replace(".csv", ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if pd:
            df = pd.DataFrame(data)
            df.to_excel(filename.replace(".csv", ".xlsx"), index=False, engine="openpyxl")


# ═══════════════════════════════════════════
#  Demo Spider (保留原有教学示例)
# ═══════════════════════════════════════════

class DemoSpider(ECommerceSpider):
    """演示爬虫 - books.toscrape.com（爬虫练习专用站）"""

    def __init__(self):
        super().__init__(base_url="https://books.toscrape.com")
        self._warmup()

    def search_products(self, keyword, max_pages=1):
        urls = []
        for page in range(1, max_pages + 1):
            if page == 1:
                url = f"{self.base_url}/catalogue/page-1.html"
            else:
                url = f"{self.base_url}/catalogue/page-{page}.html"
            print(f"  浏览第 {page} 页...")
            resp = self._fetch(url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for h3 in soup.select("h3 a"):
                href = h3.get("href")
                if href:
                    full_url = urljoin(self.base_url, f"catalogue/{href}")
                    if full_url not in urls:
                        urls.append(full_url)
        return urls

    def parse_product(self, url):
        resp = self._fetch(url)
        if not resp:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        product = {"url": url, "source": "BooksToScrape", "scraped_at": datetime.now().isoformat()}

        title_el = soup.select_one("h1")
        product["title"] = title_el.get_text(strip=True) if title_el else "N/A"

        price_el = soup.select_one(".price_color")
        price_text = price_el.get_text(strip=True) if price_el else None
        product["price"] = self._parse_price(price_text)
        product["currency"] = "£"

        rating_map = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
        rating_el = soup.select_one("p.star-rating")
        product["rating"] = "N/A"
        if rating_el:
            for cls in rating_el.get("class", []):
                if cls in rating_map:
                    product["rating"] = rating_map[cls]
                    break

        breadcrumb = soup.select(".breadcrumb li")
        product["category"] = breadcrumb[2].get_text(strip=True) if len(breadcrumb) >= 3 else "N/A"

        desc_el = soup.select_one("#product_description ~ p")
        product["description"] = desc_el.get_text(strip=True)[:200] if desc_el else ""

        img_el = soup.select_one(".item.active img")
        img_src = img_el.get("src") if img_el else ""
        product["main_image"] = urljoin(self.base_url, img_src) if img_src else ""

        stock_el = soup.select_one(".instock")
        product["stock"] = stock_el.get_text(strip=True) if stock_el else "N/A"

        return product


# ═══════════════════════════════════════════
#  CLI 交互入口
# ═══════════════════════════════════════════

def main():
    print("=" * 55)
    print("  E-Commerce Crawler v2.0 - 电商数据采集工具")
    print("=" * 55)

    spiders = {
        "1": ("Amazon 商品", lambda: AmazonSpider()),
        "2": ("AliExpress 速卖通", lambda: AliExpressSpider()),
        "3": ("TikTok Shop", lambda: TikTokShopSpider()),
        "4": ("Demo 教学站 (books.toscrape.com)", lambda: DemoSpider()),
    }

    while True:
        print("\n选择目标平台:")
        for k, (name, _) in spiders.items():
            print(f"  {k}. {name}")
        print("  q. 退出")

        choice = input("\n请输入编号: ").strip()
        if choice == "q":
            print("已退出")
            break

        if choice not in spiders:
            print("无效选择")
            continue

        if choice == "3" and not HAS_PLAYWRIGHT:
            print("TikTok Shop 需要 Playwright。正在安装...")
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            print("安装完成，请重新运行程序。")
            continue

        keyword = input("搜索关键词: ").strip()
        if not keyword:
            continue

        try:
            pages = int(input("爬取页数 (默认1页): ") or "1")
        except ValueError:
            pages = 1

        spider = spiders[choice][1]()
        spider.crawl(keyword, pages)

        print("\n" + "=" * 55)


if __name__ == "__main__":
    main()
