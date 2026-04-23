import pandas as pd
from playwright.sync_api import sync_playwright
import re


def is_company(name: str) -> bool:
    if not name:
        return False

    name = name.strip()

    if len(name) < 3 or len(name) > 60:
        return False

    blacklist = [
        "about", "show", "media", "program", "summit",
        "speaker", "agenda", "register", "login",
        "privacy", "cookie", "contact", "visit",
        "home", "menu", "search", "hours",
        "industry", "solutions", "technology",
        "system", "event", "read more", "click",
        "learn", "explore", "why", "book", "info",
        "partner", "sponsor", "exhibit"
    ]

    if any(b in name.lower() for b in blacklist):
        return False

    if "@" in name or re.search(r"\d{5,}", name):
        return False

    if re.match(r"^[A-Z]{1,3}\d{1,3}", name):
        return False

    words = name.split()

    if len(words) > 5:
        return False

    if not re.search(r"[A-Za-z]", name):
        return False

    if words[0].islower():
        return False

    strong_keywords = ["ltd", "pvt", "inc", "llc", "llp", "corporation", "co", "limited"]

    if any(k in name.lower() for k in strong_keywords):
        return True

    if name.isupper() and len(words) <= 4:
        return True

    if len(words) >= 2:
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


def extract_from_images_with_context(page):
    results = []
    seen = set()

    images = page.locator("img")

    for i in range(images.count()):
        try:
            img = images.nth(i)

            src = img.get_attribute("src") or ""
            if not src:
                continue

            if src.startswith("//"):
                src = "https:" + src

            if src.startswith("/"):
                src = page.url.rstrip("/") + src

            if not src.startswith("http"):
                continue

            alt = (img.get_attribute("alt") or "").strip()

            name = alt

            if not is_company(name):
                parent = img.locator("xpath=ancestor::*[self::div or self::li][1]")
                text = (parent.inner_text() or "").strip()
                name = text.split("\n")[0]

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


def extract_text_fallback(page):
    results = []
    seen = set()

    elements = page.locator("h1, h2, h3, h4, a")

    for i in range(elements.count()):
        try:
            text = elements.nth(i).inner_text().strip()

            if not is_company(text):
                continue

            key = text.lower()

            if key in seen:
                continue

            seen.add(key)

            results.append({
                "Company Name": text,
                "Logo": ""
            })

        except:
            continue

    return results


def run_scraper(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Opening: {url}")
        page.goto(url, timeout=90000, wait_until="domcontentloaded")

        page.wait_for_timeout(5000)
        auto_scroll(page)

        data = []

        print("Extracting from images with context...")
        data.extend(extract_from_images_with_context(page))

        if len(data) < 20:
            print("Fallback: extracting from text...")
            data.extend(extract_text_fallback(page))

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
