from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import pandas as pd

URL = "https://in.tradingview.com/screener/om1dpUb7/"
OUTPUT_FILE = "tradingview_data.csv"


def clean_row(values):
    return [v.strip() for v in values if v is not None]


def main():
    all_rows = []
    seen_rows = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 900})

        page.goto(URL, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(5000)

        page.screenshot(path="debug_page.png", full_page=True)

        page_count = 1

        while True:
            try:
                page.wait_for_selector("table tbody tr", timeout=30000)
            except PlaywrightTimeoutError:
                print("Could not find table rows. Saving screenshot and exiting.")
                page.screenshot(path=f"error_page_{page_count}.png", full_page=True)
                break

            rows = page.query_selector_all("table tbody tr")
            print(f"Page {page_count}: found {len(rows)} rows")

            before_count = len(all_rows)

            for row in rows:
                text = row.inner_text().strip()
                if not text:
                    continue

                cols = clean_row(text.split("\t"))
                row_key = tuple(cols)

                if row_key not in seen_rows:
                    seen_rows.add(row_key)
                    all_rows.append(cols)

            print(f"Added {len(all_rows) - before_count} new rows from page {page_count}")

            next_btn = None
            selectors = [
                'button[aria-label="Next page"]',
                'button[aria-label="Next"]',
                'button[data-overflow-tooltip-text="Next"]'
            ]

            for selector in selectors:
                btn = page.query_selector(selector)
                if btn:
                    next_btn = btn
                    break

            if not next_btn:
                print("Next button not found. Reached last page or UI changed.")
                break

            disabled = next_btn.get_attribute("disabled")
            aria_disabled = next_btn.get_attribute("aria-disabled")

            if disabled is not None or aria_disabled == "true":
                print("Next button is disabled. Reached last page.")
                break

            old_first_row = rows[0].inner_text().strip() if rows else ""

            try:
                next_btn.click()
                page.wait_for_timeout(3000)

                for _ in range(10):
                    new_rows = page.query_selector_all("table tbody tr")
                    if new_rows:
                        new_first_row = new_rows[0].inner_text().strip()
                        if new_first_row != old_first_row:
                            break
                    page.wait_for_timeout(1000)

                page_count += 1

            except Exception as e:
                print(f"Could not click next button: {e}")
                break

        browser.close()

    if not all_rows:
        raise RuntimeError("No rows were captured. Check the page layout, login status, or anti-bot protection.")

    max_len = max(len(r) for r in all_rows)
    normalized = [r + [""] * (max_len - len(r)) for r in all_rows]

    df = pd.DataFrame(normalized)
    df.to_csv(OUTPUT_FILE, index=False, header=False, encoding="utf-8-sig")

    print(f"Saved {len(df)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
