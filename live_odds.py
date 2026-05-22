from playwright.sync_api import sync_playwright
import pandas as pd

URL = "https://www.punters.com.au/form-guide/"

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]
    )

    page = browser.new_page()

    print("Opening page...")

    page.goto(URL, timeout=60000)

    print("Page loaded!")

    content = page.content()

    df = pd.DataFrame({
        "data": [content[:1000]]
    })

    df.to_csv("live_odds.csv", index=False)

    print("CSV created!")

    browser.close()