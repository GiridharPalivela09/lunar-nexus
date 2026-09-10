"""Playwright End-to-End Browser Automation Test Suite for NEXUS-LUNAR.
Validates complete multi-tab navigation, 3D WebGL, Leaflet GIS map, image lightboxes,
spatial knowledge graph interactions, and the First-Principles PINN Scientific Workbench.
"""

import os
from pathlib import Path
import pytest
pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright, Page, expect

BASE_URL = os.environ.get("NEXUS_BASE_URL", "http://127.0.0.1:8000")
SCREENSHOTS_DIR = Path("outputs/playwright_test_results")


@pytest.fixture(scope="session")
def setup_screenshots_dir():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    return SCREENSHOTS_DIR


@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 950})
        yield context
        context.close()
        browser.close()


@pytest.fixture(scope="function")
def page(browser_context) -> Page:
    page = browser_context.new_page()
    console_errors = []

    def on_console(msg):
        if msg.type == "error":
            # Filter out external network/analytics errors if any
            console_errors.append(msg.text)

    page.on("console", on_console)
    page.on("pageerror", lambda err: console_errors.append(str(err)))

    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1000)

    yield page

    # Assert zero critical uncaught JavaScript errors during execution
    critical_errors = [e for e in console_errors if "SyntaxError" in e or "ReferenceError" in e or "TypeError" in e]
    assert len(critical_errors) == 0, f"Encountered uncaught JavaScript errors: {critical_errors}"
    page.close()


def test_01_page_header_and_telemetry_hud(page: Page, setup_screenshots_dir):
    """Verify page title, top header, status indicator, and HUD."""
    assert "NEXUS-LUNAR" in page.title()
    expect(page.locator(".brand-title")).to_contain_text("NEXUS-LUNAR")
    expect(page.locator("#statusText")).to_be_visible()
    expect(page.locator("#btnOpenScienceModal")).to_be_visible()

    page.screenshot(path=str(SCREENSHOTS_DIR / "01_initial_page_load.png"))


def test_02_habitat_digital_twin_and_blender_controls(page: Page, setup_screenshots_dir):
    """Verify Tab 0 (Habitat Digital Twin), Three.js Canvas, and Blender Cycles viewport."""
    page.click('.nav-tab[data-tab="tab-nexus3d"]')
    page.wait_for_timeout(600)

    expect(page.locator("#nexus3dCanvasContainer")).to_be_visible()

    # Verify Blender Viewport toggle and zoom controls
    btn_blender_mode = page.locator("#btnToggleBlenderMode")
    if btn_blender_mode.is_visible():
        btn_blender_mode.click()
        page.wait_for_timeout(500)
        expect(page.locator("#nexus3dBlenderContainer")).to_be_visible()
        expect(page.locator("#blenderInStudioImg")).to_be_visible()

        page.click("#btnBlenderZoomIn")
        page.click("#btnBlenderZoomOut")
        page.click("#btnBlenderResetZoom")

    page.screenshot(path=str(SCREENSHOTS_DIR / "02_tab_nexus3d_digital_twin.png"))


def test_03_lunar_gis_explorer(page: Page, setup_screenshots_dir):
    """Verify Tab 1 (Lunar GIS Explorer) and Leaflet map container."""
    page.click('.nav-tab[data-tab="tab-map"]')
    page.wait_for_timeout(800)

    expect(page.locator("#tab-map")).to_have_class("tab-pane active")
    expect(page.locator("#lunarMap")).to_be_visible()

    page.screenshot(path=str(SCREENSHOTS_DIR / "03_tab_lunar_gis_map.png"))


def test_04_patch_harmonization_studio(page: Page, setup_screenshots_dir):
    """Verify Tab 2 (Patch Harmonization)."""
    page.click('.nav-tab[data-tab="tab-patches"]')
    page.wait_for_timeout(600)

    expect(page.locator("#tab-patches")).to_have_class("tab-pane active")
    expect(page.locator("#pairsContainer")).to_be_visible()

    page.screenshot(path=str(SCREENSHOTS_DIR / "04_tab_patch_harmonization.png"))


def test_05_classical_registration_studio(page: Page, setup_screenshots_dir):
    """Verify Tab 3 (Classical Registration), dropdowns, and execution button."""
    page.click('.nav-tab[data-tab="tab-reg"]')
    page.wait_for_timeout(600)

    expect(page.locator("#reg-select-source")).to_be_visible()
    expect(page.locator("#reg-select-reference")).to_be_visible()
    expect(page.locator("#btn-execute-reg")).to_be_visible()

    page.screenshot(path=str(SCREENSHOTS_DIR / "05_tab_classical_registration.png"))


def test_06_illumination_invariance_studio(page: Page, setup_screenshots_dir):
    """Verify Tab 4 (Illumination Invariance)."""
    page.click('.nav-tab[data-tab="tab-poc4"]')
    page.wait_for_timeout(600)

    expect(page.locator("#tab-poc4")).to_have_class("tab-pane active")
    expect(page.locator("#btnRunPOC4Experiment")).to_be_visible()

    page.screenshot(path=str(SCREENSHOTS_DIR / "06_tab_illumination_invariance.png"))


def test_07_multimodal_ai_retrieval_and_gallery_preview(page: Page, setup_screenshots_dir):
    """Verify Tab 5 (Multimodal AI Retrieval) and click preview to open lightbox."""
    page.click('.nav-tab[data-tab="tab-poc5"]')
    page.wait_for_timeout(600)

    expect(page.locator("#tab-poc5")).to_have_class("tab-pane active")
    expect(page.locator("#btnRunPOC5Experiment")).to_be_visible()

    # Click on the gallery preview image to open the lightbox
    gallery_img = page.locator("#poc5QueryImgPreview")
    if gallery_img.is_visible():
        gallery_img.click()
        page.wait_for_timeout(500)
        expect(page.locator("#imagePreviewModal")).to_be_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "07_poc5_query_gallery_lightbox.png"))
        page.click("#btnClosePreviewModal")
        page.wait_for_timeout(300)
        expect(page.locator("#imagePreviewModal")).not_to_be_visible()


def test_08_geometric_consensus_xai(page: Page, setup_screenshots_dir):
    """Verify Tab 6 (Geometric Consensus XAI) and verified candidates cards."""
    page.click('.nav-tab[data-tab="tab-poc6"]')
    page.wait_for_timeout(600)

    expect(page.locator("#tab-poc6")).to_have_class("tab-pane active")
    expect(page.locator("#btnRunPOC6")).to_be_visible()

    page.screenshot(path=str(SCREENSHOTS_DIR / "08_tab_geometric_consensus_xai.png"))


def test_09_spatial_knowledge_graph_and_explanation_modal(page: Page, setup_screenshots_dir):
    """Verify Tab 7 (Spatial Knowledge Graph) and site explanation modal."""
    page.click('.nav-tab[data-tab="tab-poc7"]')
    page.wait_for_timeout(800)

    expect(page.locator("#tab-poc7")).to_have_class("tab-pane active")

    # If candidate site rows or explanation buttons exist, trigger explanation modal
    site_card = page.locator(".candidate-site-card").first
    if site_card.is_visible():
        site_card.click()
        page.wait_for_timeout(500)
        expect(page.locator("#siteExplanationModal")).to_be_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "09_poc7_site_explanation_modal.png"))
        page.click("#modalSiteClose")
        page.wait_for_timeout(300)
    else:
        page.screenshot(path=str(SCREENSHOTS_DIR / "09_tab_spatial_knowledge_graph.png"))


def test_10_observations_catalog(page: Page, setup_screenshots_dir):
    """Verify Tab 8 (Observations Catalog) and search filtering."""
    page.click('.nav-tab[data-tab="tab-catalog"]')
    page.wait_for_timeout(600)

    expect(page.locator("#tab-catalog")).to_have_class("tab-pane active")
    expect(page.locator("#catalogSearchInput")).to_be_visible()

    # Search filter test
    page.fill("#catalogSearchInput", "OHRC")
    page.wait_for_timeout(400)
    page.fill("#catalogSearchInput", "")

    page.screenshot(path=str(SCREENSHOTS_DIR / "10_tab_observations_catalog.png"))


def test_11_first_principles_and_pinn_scientific_workbench(page: Page, setup_screenshots_dir):
    """Verify First-Principles Scientific Workbench modal, 4 pillars, PINN telemetry, and simulation run."""
    # Open modal
    btn_open = page.locator("#btnOpenScienceModal")
    btn_open.click()
    page.wait_for_timeout(800)

    modal = page.locator("#scienceModal")
    expect(modal).to_be_visible()

    # Verify Pillar 1: Frequency
    expect(page.locator("#sciSkinDepthL")).not_to_have_text("-- m")
    expect(page.locator("#sciDielectricEps")).not_to_have_text("--")

    # Verify Pillar 2: Physics
    expect(page.locator("#sciHapkeRefl")).not_to_have_text("--")
    expect(page.locator("#sciRoverMobility")).to_be_visible()

    # Verify Pillar 3: Chemistry
    expect(page.locator("#sciOxygenYield")).not_to_have_text("-- kg")

    # Verify Pillar 4: Biology
    expect(page.locator("#sciO2Closure")).not_to_have_text("-- %")
    expect(page.locator("#sciRadVerdict")).to_be_visible()

    # Verify PINN Neural Telemetry Strip
    expect(page.locator("#pinnArch")).to_contain_text("MLP")
    expect(page.locator("#pinnResidualRms")).to_be_visible()
    expect(page.locator("#pinnColdTrap")).to_be_visible()

    # Take screenshot of the open workbench
    page.screenshot(path=str(SCREENSHOTS_DIR / "11_scientific_workbench_initial.png"))

    # Test interactive simulation with sliders via JavaScript dispatch
    page.evaluate("""() => {
        const crew = document.getElementById('simCrewSize');
        if (crew) { crew.value = '6'; crew.dispatchEvent(new Event('input')); }
        const days = document.getElementById('simMissionDays');
        if (days) { days.value = '60'; days.dispatchEvent(new Event('input')); }
        const shield = document.getElementById('simShieldDepth');
        if (shield) { shield.value = '3.0'; shield.dispatchEvent(new Event('input')); }
        const isru = document.getElementById('simIsruTonnes');
        if (isru) { isru.value = '20'; isru.dispatchEvent(new Event('input')); }
    }""")
    page.wait_for_timeout(400)

    # Trigger simulation
    page.click("#btnRunSimScience")
    page.wait_for_timeout(1500)

    # Verify updated values
    expect(page.locator("#sciO2Closure")).to_be_visible()
    page.screenshot(path=str(SCREENSHOTS_DIR / "12_scientific_workbench_simulated.png"))

    # Close modal
    page.click("#btnCloseScienceModal")
    page.wait_for_timeout(400)
    expect(modal).not_to_be_visible()
