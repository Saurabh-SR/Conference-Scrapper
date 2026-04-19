import pandas as pd
from playwright.sync_api import sync_playwright
import re


def is_company(name: str) -> bool:
    if not name:
        return False

    name = name.strip()

    if len(name) < 3 or len(name) > 80:
        return False

    blacklist = [
        "about", "show", "media", "program", "summit",
        "speaker", "agenda", "register", "login",
        "privacy", "cookie", "contact", "visit",
        "home", "menu", "search", "hours",
        "industry", "solutions", "technology",
        "system", "event", "read more", "click",
        "learn", "explore"
    ]

    if any(b in name.lower() for b in blacklist):
        return False

    if "@" in name or re.search(r"\d{4,}", name):
        return False

    if re.match(r"^[A-Z]{1,3}\d{1,3}", name):
        return False

    strong_keywords = ["ltd", "pvt", "inc", "llc", "llp", "corporation", "co."]

    if any(k in name.lower() for k in strong_keywords):
        return True

    if name.isupper() and len(name.split()) <= 5:
        return True

    if len(name.split()) >= 2 and name[0].isupper():
        return True

    return False


def auto_scroll(page):
    prev_height = 0
    while True:
        curr_height = page.evaluate("document.body.scrollHeight")
        if curr_height == prev_height:
            break
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1200)
        prev_height = curr_height


def extract_from_cards(page):
    results = []
    seen = set()

    cards = page.locator("div, li, article")

    for i in range(cards.count()):
        try:
            card = cards.nth(i)

            text = card.inner_text().strip()
            if not text:
                continue

            lines = text.split("\n")
            name = lines[0].strip()

            if not is_company(name):
                continue

            img = card.locator("img").first
            logo = ""

            if img.count() > 0:
                src = img.get_attribute("src") or ""
                if src.startswith("//"):
                    src = "https:" + src
                if src.startswith("/"):
                    src = page.url.rstrip("/") + src
                logo = src

            key = name.lower()
            if key in seen:
                continue

            seen.add(key)

            results.append({
                "Company Name": name,
                "Logo": logo
            })

        except:
            continue

    return results


def extract_from_images(page):
    results = []
    seen = set()

    images = page.locator("img")

    for i in range(images.count()):
        try:
            img = images.nth(i)

            alt = (img.get_attribute("alt") or "").strip()
            src = img.get_attribute("src") or ""

            if not src:
                continue

            if src.startswith("//"):
                src = "https:" + src

            if not src.startswith("http"):
                continue

            name = alt

            if not is_company(name):
                continue

            key = name.lower()
            if key in seen:
                continue

            seen.add(key)

            results.append({
                "Company Name": name,
                "Logo": src
            })

        except:
            continue

    return results


def run_scraper(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Opening: {url}")
        page.goto(url, timeout=60000, wait_until="domcontentloaded")

        page.wait_for_timeout(5000)
        auto_scroll(page)

        data = []

        print("Extracting from structured cards...")
        data.extend(extract_from_cards(page))

        print("Extracting from images...")
        data.extend(extract_from_images(page))

        browser.close()

    seen = set()
    final = []

    for item in data:
        key = item["Company Name"].lower()
        if key not in seen:
            seen.add(key)
            final.append(item)

    print(f"Final companies: {len(final)}")

    df = pd.DataFrame(final)
    df.to_excel("output.xlsx", index=False)

    print("Saved: output.xlsx")


if __name__ == "__main__":
    run_scraper("https://www.infocomm-india.com/")