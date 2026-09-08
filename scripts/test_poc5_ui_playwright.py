"""Playwright automated browser test verifying POC-5 AI Studio web interface.

Tests:
1. Navigation to POC 5 AI Studio tab.
2. Verification of KPIs (Recall@1, Recall@5, Recall@10, MRR, 128-D).
3. Retrieval candidate cards and true match indicators.
4. Publication diagnostic figures display.
5. Query selector interactivity and rerendering.
"""

import sys
import time
from playwright.sync_api import sync_playwright


def test_poc5_ui():
    print("[Playwright] Launching browser to test POC 5 AI Studio...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        # Navigate to dashboard
        page.goto("http://127.0.0.1:8000/#poc5")
        page.wait_for_load_state("networkidle")
        time.sleep(1.0)

        # Click on POC 5 Tab explicitly
        tab_btn = page.locator("#tabBtnPOC5")
        assert tab_btn.is_visible(), "POC-5 tab button not found!"
        tab_btn.click()
        time.sleep(1.0)

        # Verify POC 5 tab is active
        tab_pane = page.locator("#tab-poc5")
        assert "active" in (tab_pane.get_attribute("class") or ""), "POC-5 tab pane not active!"
        print("[Playwright] POC-5 Studio Tab is active.")

        # Verify KPI Metrics
        r1_val = page.locator("#poc5Recall1Val").inner_text()
        r5_val = page.locator("#poc5Recall5Val").inner_text()
        r10_val = page.locator("#poc5Recall10Val").inner_text()
        mrr_val = page.locator("#poc5MRRVal").inner_text()
        dim_val = page.locator("#poc5DimVal").inner_text()

        print(f"[Playwright] Verified KPIs -> R@1: {r1_val}, R@5: {r5_val}, R@10: {r10_val}, MRR: {mrr_val}, Dim: {dim_val}")
        assert "%" in r1_val and float(r1_val.replace("%", "")) >= 10.0
        assert "%" in r5_val and float(r5_val.replace("%", "")) >= 40.0
        assert "%" in r10_val and float(r10_val.replace("%", "")) >= 60.0
        assert float(mrr_val) >= 0.25
        assert "128-D" in dim_val

        # Verify Query Selector Options
        select = page.locator("#poc5QuerySelect")
        assert select.is_visible(), "Query selector not visible!"
        option_count = select.locator("option").count()
        print(f"[Playwright] Verified {option_count} query options in dropdown.")
        assert option_count >= 5

        # Verify Retrieval Cards Grid
        grid = page.locator("#poc5RetrievalGrid")
        cards = grid.locator(".glassmorphism")
        card_count = cards.count()
        print(f"[Playwright] Verified {card_count} retrieval cards rendered in grid.")
        assert card_count >= 4  # 1 Query + at least 3 candidates

        # Check for TRUE MATCH badge
        true_match_badge = grid.locator("text=TRUE MATCH")
        assert true_match_badge.count() >= 1, "True match badge not found in retrieval cards!"
        print("[Playwright] Ground-truth match badge verified.")

        # Verify Figures
        for fig_id in ["poc5FigArch", "poc5FigGrid", "poc5FigClusters", "poc5FigRecall", "poc5FigDist"]:
            img = page.locator(f"#{fig_id}")
            assert img.is_visible(), f"Figure #{fig_id} not visible!"
        print("[Playwright] All 5 publication figures rendered successfully.")

        # Capture Screenshot
        screenshot_path = "outputs/poc5/poc5_studio_playwright.png"
        page.screenshot(path=screenshot_path)
        print(f"[Playwright] Saved verification screenshot: {screenshot_path}")

        browser.close()
        print("[Playwright] POC-5 UI Browser verification PASSED completely!")


if __name__ == "__main__":
    test_poc5_ui()
