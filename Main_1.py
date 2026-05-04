import pandas as pd
from playwright.sync_api import sync_playwright
import re


def normalize(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def is_booth(text):
    return bool(re.fullmatch(r"[A-Z]{1,4}\d{1,4}", text))


def is_valid_company(name):
    if not name:
        return False

    name = normalize(name)

    if len(name) < 3 or len(name) > 80:
        return False

    if not re.search(r"[A-Za-z]", name):
        return False

    blacklist = {
        "visit", "exhibit", "home", "search",
        "industries", "government", "education",
        "hospitality", "enterprise", "healthcare",
        "retail", "travel", "grid", "list", "all",
        "privacy policy", "quick links"
    }

    if name.lower() in blacklist:
        return False

    if len(name.split()) == 1 and not name.isupper():
        return False

    return True


def extract_companies(page):
    text = page.inner_text("body")
    lines = [normalize(x) for x in text.split("\n") if normalize(x)]

    results = []
    seen = set()

    i = 0
    while i < len(lines) - 1:
        current = lines[i]
        nxt = lines[i + 1]

        # still use booth pattern for detection, but DO NOT store booth
        if is_booth(current) and is_valid_company(nxt):
            name = nxt

            key = name.lower()
            if key not in seen:
                seen.add(key)
                results.append({
                    "Company Name": name
                })

            i += 2
            continue

        i += 1

    return results


def run_scraper(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Loading page...")
        page.goto(url, timeout=90000)
        page.wait_for_timeout(5000)

        print("Extracting company names...")
        data = extract_companies(page)

        browser.close()

    print(f"Companies found: {len(data)}")

    df = pd.DataFrame(data)
    df.to_excel("output.xlsx", index=False)

    print("Saved: output.xlsx")


if __name__ == "__main__":
    run_scraper("https://www.infocomm-india.com/discover-solutions/")
