"""Synthetic local-browser smoke coverage for ChangeRipple. Not a validated QA protocol."""
import sys

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv)>1 else "http://127.0.0.1:8765"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        failures = []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.goto(BASE, wait_until="networkidle")
        assert "See the ripples" in page.locator("main h1").inner_text(), "Overview is not rendered"
        assert "DEMO" in page.locator(".demo-pill").inner_text()
        page.locator('[data-route="assessments"]').first.click()
        assert "All assessments" in page.locator("main").inner_text()
        assert page.locator('button[data-open="CR-001"]').count() >= 1
        page.locator('button[data-open="CR-002"]').first.click()
        assert "Revise incoming inspection" in page.locator("h1").inner_text()
        assert page.locator("article.impact").count() >= 3
        page.locator('select[data-decision]').first.select_option("Included")
        assert page.locator('select[data-decision]').first.input_value() == "Included"
        page.locator('button[data-tab="reviews"]').click()
        assert "Cross-functional action register" in page.locator("main").inner_text()
        required=page.locator('select[data-action]').first
        asset=required.get_attribute("data-action")
        required.select_option("Done")
        note=page.locator('textarea[data-note="'+asset+'"]')
        note.fill("Synthetic evidence and reviewer verification note")
        note.press("Tab")
        assert page.locator(
            'textarea[data-note="' + asset + '"]'
        ).input_value().startswith("Synthetic evidence")
        page.locator('[data-route="library"]').first.click()
        assert "Dependency library" in page.locator("h1").inner_text()
        page.locator("#from").select_option("SOP-401")
        page.locator("#to").select_option("EQ-1202")
        page.locator("#relationType").select_option(label="governs")
        page.get_by_role("button",name="Add mapping & recompute →").click()
        assert "relationship added" in page.locator('main').inner_text()
        page.locator('[data-route="assessments"]').first.click()
        page.locator('button[data-open="CR-002"]').first.click()
        assert "EQ-1202" in page.locator('main').inner_text()
        page.locator('[data-route="new"]').first.click()
        page.locator("#type").select_option("NC / CAPA")
        page.locator("#title").fill("Synthetic omitted receipt check review")
        page.locator("#summary").fill(
            "Investigate a fictional missing receiving step and possible departments to notify."
        )
        page.locator("#root").select_option("NC-1301")
        page.get_by_role("button",name="Analyze dependencies →").click()
        assert "Synthetic omitted receipt check review" in page.locator("h1").inner_text()
        page.locator('button[data-tab="capa"]').click()
        assert page.locator("div.checklist-row").count()==9
        assert page.locator('button[data-close]').is_disabled()
        assert not failures, "JavaScript errors: " + "; ".join(failures)
        print(
            "PASS: overview, assessments, dispositions, action evidence, "
            "mapping/recompute, NC/CAPA wizard and closure gate."
        )
        browser.close()

if __name__ == "__main__":
    run()
