import sys
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8585/"
errors = []

with sync_playwright() as p:
    b = p.chromium.launch()
    # desktop
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(2500)
    pg.screenshot(path="/root/youtubarr/config/shot_desktop.png", full_page=True)
    # click Failed tab to see it
    try:
        pg.get_by_text("Failed", exact=False).first.click()
        pg.wait_for_timeout(500)
        pg.screenshot(path="/root/youtubarr/config/shot_failed_tab.png", full_page=True)
    except Exception as e:
        errors.append(f"failed-tab click: {e}")
    pg.close()
    # mobile
    m = b.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
    m.goto(URL, wait_until="networkidle")
    m.wait_for_timeout(2500)
    m.screenshot(path="/root/youtubarr/config/shot_mobile.png", full_page=True)
    m.close()
    b.close()

print("ERRORS:" if errors else "no console errors")
for e in errors[:40]:
    print(" ", e)
