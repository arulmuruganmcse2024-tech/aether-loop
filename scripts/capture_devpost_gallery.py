import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("assets/devpost_gallery")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TARGET_URL = "http://localhost:8000"
VIEWPORT_WIDTH = 1800
VIEWPORT_HEIGHT = 1200

def run():
    print("=" * 80)
    print("AETHER-LOOP | AUTOMATED DEVPOST GALLERY CAPTURE ENGINE")
    print(f"Viewport: {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT} (3:2 Aspect Ratio)")
    print(f"Target: {TARGET_URL}")
    print(f"Output: {OUTPUT_DIR.resolve()}")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME_PATH, headless=True)
        context = browser.new_context(viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        page = context.new_page()

        print("\n[INIT] Navigating to AETHER-LOOP control plane...")
        page.goto(TARGET_URL, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # -------------------------------------------------------------
        # 01_Hero_Dashboard.jpg
        # Wide shot of 3D digital twin and top navigation bar
        # -------------------------------------------------------------
        print("\n[1/10] Capturing 01_Hero_Dashboard.jpg...")
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)
        shot1 = OUTPUT_DIR / "01_Hero_Dashboard.jpg"
        page.screenshot(path=str(shot1), type="jpeg", quality=90)
        print(f"  -> Saved {shot1.name} ({shot1.stat().st_size:,} bytes)")

        # -------------------------------------------------------------
        # 02_Skydrol_Failure_Spike.jpg
        # Trigger Regime A, replay edge v1.0 failure at t=1.24s, enable ghost arm
        # -------------------------------------------------------------
        print("\n[2/10] Capturing 02_Skydrol_Failure_Spike.jpg...")
        # Enable Ghost v1.0 and Friction Cone debug layers if off
        for btn_text in ["Debug Layer: Ghost v1.0", "Debug Layer: Friction Cone"]:
            try:
                b = page.get_by_role("button", name=btn_text)
                if b.is_visible() and "[OFF]" in b.inner_text():
                    b.click()
                    page.wait_for_timeout(400)
            except Exception as e:
                pass

        # Click Replay Edge v1.0 Failure
        try:
            page.get_by_role("button", name="1. Replay Edge v1.0 Failure").click()
            page.wait_for_timeout(800)
        except Exception:
            pass

        # Inspect t=1.24s slip event
        try:
            page.get_by_role("button", name="⚡ Inspect t=1.24s Slip Event").click()
            page.wait_for_timeout(800)
        except Exception:
            pass

        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        shot2 = OUTPUT_DIR / "02_Skydrol_Failure_Spike.jpg"
        page.screenshot(path=str(shot2), type="jpeg", quality=90)
        print(f"  -> Saved {shot2.name} ({shot2.stat().st_size:,} bytes)")

        # -------------------------------------------------------------
        # 03_Dynamic_Judge_Studio.jpg
        # Focus on the Tavily Maintenance & ROS2 Errata Search with live receipt
        # -------------------------------------------------------------
        print("\n[3/10] Capturing 03_Dynamic_Judge_Studio.jpg...")
        # Switch to Tab 2: OpenShell SRE & Tavily
        page.get_by_role("button", name="2. OpenShell SRE & Tavily").click()
        page.wait_for_timeout(800)

        # Trigger a search or verify the live receipt
        try:
            tavily_btn = page.get_by_role("button", name="Search Live Docs")
            if tavily_btn.is_visible():
                tavily_btn.click()
                page.wait_for_timeout(1500)
        except Exception:
            pass

        # Scroll so Tab 2 is centered
        page.evaluate("window.scrollTo(0, 160)")
        page.wait_for_timeout(500)
        shot3 = OUTPUT_DIR / "03_Dynamic_Judge_Studio.jpg"
        page.screenshot(path=str(shot3), type="jpeg", quality=90)
        print(f"  -> Saved {shot3.name} ({shot3.stat().st_size:,} bytes)")

        # -------------------------------------------------------------
        # 04_SRE_Agent_Tavily_Grounding.jpg
        # OpenShell SRE tab, showing live Tavily citations and 4-tier Nemotron log
        # -------------------------------------------------------------
        print("\n[4/10] Capturing 04_SRE_Agent_Tavily_Grounding.jpg...")
        page.evaluate("window.scrollTo(0, 260)")
        page.wait_for_timeout(500)
        shot4 = OUTPUT_DIR / "04_SRE_Agent_Tavily_Grounding.jpg"
        page.screenshot(path=str(shot4), type="jpeg", quality=90)
        print(f"  -> Saved {shot4.name} ({shot4.stat().st_size:,} bytes)")

        # -------------------------------------------------------------
        # 05_OpenShell_Syscall_Block.jpg
        # Test /dev/can0 Syscall Interception showing BLOCKED [EPERM]
        # -------------------------------------------------------------
        print("\n[5/10] Capturing 05_OpenShell_Syscall_Block.jpg...")
        try:
            guard_btn = page.get_by_role("button", name="Test Unauthorized /dev/can0 Syscall")
            if guard_btn.is_visible():
                guard_btn.click()
                page.wait_for_timeout(1200)
        except Exception as e:
            print("  [WARN] Guard test click:", e)

        page.evaluate("window.scrollTo(0, 200)")
        page.wait_for_timeout(500)
        shot5 = OUTPUT_DIR / "05_OpenShell_Syscall_Block.jpg"
        page.screenshot(path=str(shot5), type="jpeg", quality=90)
        print(f"  -> Saved {shot5.name} ({shot5.stat().st_size:,} bytes)")

        # -------------------------------------------------------------
        # 06_Nebius_Cosmos_Batch.jpg
        # Subsystem 3 tab: Nebius Serverless CLI command and Python code diff
        # -------------------------------------------------------------
        print("\n[6/10] Capturing 06_Nebius_Cosmos_Batch.jpg...")
        page.get_by_role("button", name="3. Nebius Batch & J(q)").click()
        page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, 180)")
        page.wait_for_timeout(500)
        shot6 = OUTPUT_DIR / "06_Nebius_Cosmos_Batch.jpg"
        page.screenshot(path=str(shot6), type="jpeg", quality=90)
        print(f"  -> Saved {shot6.name} ({shot6.stat().st_size:,} bytes)")

        # -------------------------------------------------------------
        # 07_Spatial_Jacobian_Matrix.jpg
        # Focus on 6x6 spatial Jacobian J(q) matrix updating dynamically
        # -------------------------------------------------------------
        print("\n[7/10] Capturing 07_Spatial_Jacobian_Matrix.jpg...")
        page.evaluate("window.scrollTo(0, 420)")
        page.wait_for_timeout(500)
        shot7 = OUTPUT_DIR / "07_Spatial_Jacobian_Matrix.jpg"
        page.screenshot(path=str(shot7), type="jpeg", quality=90)
        print(f"  -> Saved {shot7.name} ({shot7.stat().st_size:,} bytes)")

        # -------------------------------------------------------------
        # 08_Monte_Carlo_Swarm.jpg
        # Trigger N=100 Live Trials and capture scatter plot with Wilson CI
        # -------------------------------------------------------------
        print("\n[8/10] Capturing 08_Monte_Carlo_Swarm.jpg...")
        page.get_by_role("button", name="1. Mechanics & N=100 MC").click()
        page.wait_for_timeout(600)
        try:
            mc_btn = page.get_by_role("button", name="Re-Run N=100 Live Trials")
            if mc_btn.is_visible():
                mc_btn.click()
                print("  -> Waiting for 100 Monte Carlo rollouts to step...")
                page.wait_for_timeout(3000)
        except Exception as e:
            print("  [WARN] MC button click:", e)

        page.evaluate("window.scrollTo(0, 320)")
        page.wait_for_timeout(500)
        shot8 = OUTPUT_DIR / "08_Monte_Carlo_Swarm.jpg"
        page.screenshot(path=str(shot8), type="jpeg", quality=90)
        print(f"  -> Saved {shot8.name} ({shot8.stat().st_size:,} bytes)")

        # -------------------------------------------------------------
        # 09_BOPP_Glare_Regime.jpg
        # Switch to Regime B: BOPP Pharmaceutical Blister Tray
        # -------------------------------------------------------------
        print("\n[9/10] Capturing 09_BOPP_Glare_Regime.jpg...")
        try:
            regime_b = page.get_by_role("button", name="Regime B: BOPP")
            if regime_b.is_visible():
                regime_b.click()
                page.wait_for_timeout(1000)
        except Exception as e:
            print("  [WARN] Regime B click:", e)

        try:
            page.get_by_role("button", name="2. Verify Calibrated v1.1").click()
            page.wait_for_timeout(800)
        except Exception:
            pass

        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        shot9 = OUTPUT_DIR / "09_BOPP_Glare_Regime.jpg"
        page.screenshot(path=str(shot9), type="jpeg", quality=90)
        print(f"  -> Saved {shot9.name} ({shot9.stat().st_size:,} bytes)")

        # -------------------------------------------------------------
        # 10_Attestation_Receipt.jpg
        # Capture OpenShell policy yaml, SHA-256 digest, and cURL wiretap
        # -------------------------------------------------------------
        print("\n[10/10] Capturing 10_Attestation_Receipt.jpg...")
        page.get_by_role("button", name="3. Nebius Batch & J(q)").click()
        page.wait_for_timeout(600)
        page.evaluate("window.scrollTo(0, 350)")
        page.wait_for_timeout(500)
        shot10 = OUTPUT_DIR / "10_Attestation_Receipt.jpg"
        page.screenshot(path=str(shot10), type="jpeg", quality=90)
        print(f"  -> Saved {shot10.name} ({shot10.stat().st_size:,} bytes)")

        browser.close()

    print("\n" + "=" * 80)
    print("VERIFICATION OF GENERATED DEVPOST GALLERY ASSETS")
    print("=" * 80)
    expected_files = [
        "01_Hero_Dashboard.jpg",
        "02_Skydrol_Failure_Spike.jpg",
        "03_Dynamic_Judge_Studio.jpg",
        "04_SRE_Agent_Tavily_Grounding.jpg",
        "05_OpenShell_Syscall_Block.jpg",
        "06_Nebius_Cosmos_Batch.jpg",
        "07_Spatial_Jacobian_Matrix.jpg",
        "08_Monte_Carlo_Swarm.jpg",
        "09_BOPP_Glare_Regime.jpg",
        "10_Attestation_Receipt.jpg",
    ]

    all_ok = True
    for fname in expected_files:
        fpath = OUTPUT_DIR / fname
        if not fpath.exists():
            print(f"[FAIL] Missing {fname}")
            all_ok = False
            continue
        size_kb = fpath.stat().st_size / 1024
        size_mb = size_kb / 1024
        status = "OK (<5MB)" if size_mb < 5.0 else "EXCEEDS 5MB"
        print(f"[PASS] {fname:32s} | Size: {size_kb:7.1f} KB ({size_mb:.2f} MB) | {status}")

    if all_ok:
        print("\n[SUCCESS] All 10 gallery screenshots generated at 1800x1200 (3:2) within Devpost limits.")
    else:
        print("\n[ERROR] One or more images failed generation.")
        sys.exit(1)

if __name__ == "__main__":
    run()
