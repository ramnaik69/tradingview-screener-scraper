from playwright.sync_api import sync_playwright
import pandas as pd
import time

URL = "https://in.tradingview.com/screener/om1dpUb7/"

data = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(URL)
    time.sleep(5)

    while True:
        rows = page.query_selector_all("table tbody tr")

        for row in rows:
            cols = row.inner_text().split("\t")
            data.append(cols)

        next_btn = page.query_selector('button[aria-label="Next"]')

        if next_btn:
            disabled = next_btn.get_attribute("disabled")
            if disabled:
                break

            next_btn.click()
            time.sleep(3)
        else:
            break

    browser.close()

df = pd.DataFrame(data)
df.to_csv("tradingview_data.csv", index=False)
