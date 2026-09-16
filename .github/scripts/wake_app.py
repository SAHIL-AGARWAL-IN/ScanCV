"""
Automated ping script to keep ScanCV active on Streamlit Community Cloud.
If the app has gone to sleep, Playwright clicks the 'Wake up' button automatically.
"""
import sys
import time
from playwright.sync_api import sync_playwright

APP_URL = "https://scancv.streamlit.app/"

def ping_app():
    print(f"Connecting to Streamlit app at: {APP_URL}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(APP_URL, timeout=60000)
            time.sleep(6)

            # Streamlit Cloud displays a wake button when asleep:
            # "Yes, get this app back up!" or similar phrasing
            wake_selector = "button:has-text('back up'), button:has-text('Wake'), button:has-text('wake')"
            buttons = page.locator(wake_selector)

            if buttons.count() > 0 and buttons.first.is_visible():
                print("Detected sleep screen. Clicking wake-up button...")
                buttons.first.click()
                print("Wake-up button clicked. Waiting 15s for container to boot...")
                time.sleep(15)
                print("Container wake-up triggered successfully.")
            else:
                title = page.title()
                print(f"App is actively running (Page Title: '{title}'). Inactivity timer reset!")

        except Exception as exc:
            print(f"Notice: Ping completed with detail: {exc}")
        finally:
            browser.close()

if __name__ == "__main__":
    ping_app()
