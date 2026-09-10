#!/usr/bin/env python3
"""Automated Playwright UI test for POC-6 Geometric Verification + XAI Dashboard."""

import os
import sys
import time
from pathlib import Path
import pytest
pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCREENSHOT_PATH = Path("/Users/abhishekadari/.gemini/antigravity-ide/brain/998b9eb2-09a4-42e3-b8f3-8b090e7909a1/poc6_studio_playwright.png")


def test_poc6_dashboard_ui():
    print(">>> Starting Playwright automation for POC-6 Studio...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Navigate to dashboard
        print("Navigating to http://127.0.0.1:8000 ...")
        response = page.goto("http://127.0.0.1:8000", wait_until="networkidle", timeout=15000)
        assert response.status == 200, f"Dashboard failed to load: status {response.status}"
        print("Dashboard loaded successfully.")

        # 2. Click POC-6 Tab
        print("Clicking POC 6 Geometric XAI Tab...")
        tab_btn = page.locator("#tabBtnPOC6")
        assert tab_btn.is_visible(), "POC-6 tab button not visible"
        tab_btn.click()

        # Wait for tab pane to become active
        page.wait_for_selector("#tab-poc6.active", timeout=5000)
        print("POC-6 pane is active.")

        # 3. Wait for candidates to load in the carousel
        page.wait_for_selector("#poc6CandidateCarousel button", timeout=8000)
        cards = page.locator("#poc6CandidateCarousel button")
        card_count = cards.count()
        print(f"Loaded {card_count} candidate chips in POC-6 carousel.")
        assert card_count > 0, "No candidate chips found in carousel"

        # 4. Verify candidate counts in header badges
        total_badge = page.locator("#poc6TotalCountBadge").inner_text()
        accepted_badge = page.locator("#poc6AcceptedCountBadge").inner_text()
        rejected_badge = page.locator("#poc6RejectedCountBadge").inner_text()
        print(f"Header Badges: {total_badge} | {accepted_badge} | {rejected_badge}")
        assert "Evaluated" in total_badge
        assert "Accepted" in accepted_badge
        assert "Rejected" in rejected_badge

        # 5. Find and click an ACCEPTED candidate
        accepted_chip = page.locator("#poc6CandidateCarousel button:has-text('✓')").first
        assert accepted_chip.is_visible(), "No accepted candidate chip visible"
        accepted_chip.click()
        time.sleep(0.5)

        decision_text = page.locator("#poc6DecisionBadgeContainer").inner_text()
        print(f"Selected Accepted Card Decision: '{decision_text}'")
        assert "ACCEPTED" in decision_text

        # Verify Accepted Inspection Metrics
        metric_inliers = page.locator("#poc6MetricInliers").inner_text()
        metric_ratio = page.locator("#poc6MetricInlierRatio").inner_text()
        metric_rmse = page.locator("#poc6MetricRMSE").inner_text()
        metric_stab = page.locator("#poc6MetricStability").inner_text()
        why_title = page.locator("#poc6WhyTitle").inner_text()
        why_items = page.locator("#poc6WhyList li").all_inner_texts()

        print(f"Accepted Metrics: Inliers={metric_inliers}, Ratio={metric_ratio}, RMSE={metric_rmse}, Stability={metric_stab}")
        print(f"XAI Header: '{why_title}', Evidence count: {len(why_items)}")
        assert "ACCEPTED" in why_title.upper()
        assert len(why_items) >= 4, f"Expected >= 4 evidence reasons, got {len(why_items)}"

        # 6. Find and click a REJECTED candidate
        rejected_chip = page.locator("#poc6CandidateCarousel button:has-text('✗')").first
        assert rejected_chip.is_visible(), "No rejected candidate chip visible"
        rejected_chip.click()
        time.sleep(0.5)

        rej_decision_text = page.locator("#poc6DecisionBadgeContainer").inner_text()
        print(f"Selected Rejected Card Decision: '{rej_decision_text}'")
        assert "REJECTED" in rej_decision_text

        rej_why_title = page.locator("#poc6WhyTitle").inner_text()
        rej_why_items = page.locator("#poc6WhyList li").all_inner_texts()
        print(f"XAI Rejection Header: '{rej_why_title}', Failure codes count: {len(rej_why_items)}")
        assert "REJECTED" in rej_why_title.upper()
        assert len(rej_why_items) >= 1, "Expected at least one rejection reason"

        # 7. Verify diagnostic publication figures
        gallery_images = page.locator("#tab-poc6 .gallery-img-box img")
        img_count = gallery_images.count()
        print(f"Found {img_count} diagnostic figures in gallery.")
        assert img_count >= 6, f"Expected 6 figures, got {img_count}"

        # 8. Test RUN POC-6 VERIFICATION interactive execution
        print("Testing 'RUN POC-6 VERIFICATION' button triggering...")
        run_btn = page.locator("#btnRunPOC6")
        assert run_btn.is_visible(), "Run POC-6 button not visible"
        run_btn.click()

        # Check progress bar appears
        page.wait_for_selector("#poc6ProgressCard", timeout=3000)
        print("Progress card appeared, waiting for verification completion...")

        # Wait for progress card to disappear after run finishes
        page.wait_for_selector("#poc6ProgressCard", state="hidden", timeout=20000)
        print("Verification completed and UI refreshed!")

        # 9. Capture screenshot after run
        SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SCREENSHOT_PATH), full_page=False)
        print(f"Captured updated screenshot to: {SCREENSHOT_PATH}")

        browser.close()
        print(">>> All Playwright UI tests passed successfully!")


if __name__ == "__main__":
    test_poc6_dashboard_ui()
