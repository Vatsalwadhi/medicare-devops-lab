"""End-to-end UI walkthrough of MediCare+ with screenshots (headless Chromium on the EC2 host).
Usage: python ui_walkthrough.py <base_url> <out_dir>
Test accounts: a fresh patient is registered; doctor/admin passwords are read from the K8s Secret."""
import base64, json, os, secrets, subprocess, sys
from datetime import date, timedelta
from playwright.sync_api import sync_playwright

BASE, OUT = sys.argv[1].rstrip("/"), sys.argv[2]
os.makedirs(OUT, exist_ok=True)
if os.environ.get("DOCTOR_PASSWORD"):
    DOC_PW, ADMIN_PW = os.environ["DOCTOR_PASSWORD"], os.environ["ADMIN_PASSWORD"]
else:
    sec = json.loads(subprocess.check_output(["sudo", "k3s", "kubectl", "-n", "medicare", "get", "secret",
                                              "medicare-secrets", "-o", "json"]))["data"]
    dec = lambda k: base64.b64decode(sec[k]).decode()
    DOC_PW, ADMIN_PW = dec("DOCTOR_PASSWORD"), dec("ADMIN_PASSWORD")
P_EMAIL = f"riya.sharma.{secrets.token_hex(3)}@example.com"
P_PW = "Pt-" + secrets.token_hex(5) + "!A"
DAY = (date.today() + timedelta(days=1)).isoformat()


def shot(page, name, full=False):
    page.screenshot(path=f"{OUT}/{name}.png", full_page=full)
    print("saved", name)


def login(page, email, pw):
    page.goto(f"{BASE}/login")
    page.fill("input[name=email]", email)
    page.fill("input[name=password]", pw)
    page.click("button.btn-block")


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1440, "height": 900})
    # 1. Patient registration
    page.goto(f"{BASE}/register")
    page.fill("input[name=name]", "Riya Sharma")
    page.fill("input[name=email]", P_EMAIL)
    page.fill("input[name=phone]", "+91 98400 12345")
    page.fill("input[name=dob]", "1998-04-12")
    page.select_option("select[name=gender]", "Female")
    page.select_option("select[name=blood_group]", "B+")
    page.fill("input[name=address]", "24 Lake View Road, Chennai")
    page.fill("input[name=password]", P_PW)
    page.fill("input[name=confirm]", P_PW)
    shot(page, "a1_register")
    page.click("form button.btn")
    # 2. Login and book
    login(page, P_EMAIL, P_PW)
    page.goto(f"{BASE}/patient/book?doctor=1")
    page.fill("input[name=date]", DAY)
    page.select_option("select[name=slot]", "10:30")
    page.fill("textarea[name=reason]", "Chest discomfort while climbing stairs, mild breathlessness")
    shot(page, "a2_book")
    page.click("form button.btn")
    page.goto(f"{BASE}/patient/book?doctor=6")
    page.fill("input[name=date]", DAY)
    page.select_option("select[name=slot]", "15:00")
    page.fill("textarea[name=reason]", "Annual health check-up")
    page.click("form button.btn")
    shot(page, "a3_patient_dashboard")
    page.goto(f"{BASE}/logout")
    # 3. Doctor consultation
    login(page, "ananya.rao@medicare.local", DOC_PW)
    shot(page, "a4_doctor_dashboard")
    page.click("text=Start consultation")
    page.fill("input[name=bp]", "138/88")
    page.fill("input[name=pulse]", "84")
    page.fill("input[name=temp]", "98.4")
    page.fill("input[name=diagnosis]", "Stable angina - advised TMT and lipid profile")
    page.fill("textarea[name=notes]", "Low-salt diet, 30 min walk daily, review after 2 weeks with reports.")
    rows = page.locator(".rx-row")
    rows.nth(0).locator("input[name=medicine]").fill("Aspirin")
    rows.nth(0).locator("input[name=dosage]").fill("75 mg")
    rows.nth(0).locator("input[name=frequency]").fill("0-0-1")
    rows.nth(0).locator("input[name=duration]").fill("30 days")
    page.click("#addRx")
    rows.nth(1).locator("input[name=medicine]").fill("Atorvastatin")
    rows.nth(1).locator("input[name=dosage]").fill("10 mg")
    rows.nth(1).locator("input[name=frequency]").fill("0-0-1")
    rows.nth(1).locator("input[name=duration]").fill("30 days")
    shot(page, "a5_consultation")
    page.click("form button.btn.span-2")
    page.goto(f"{BASE}/logout")
    # 4. Patient sees encrypted-at-rest record + pays bill
    login(page, P_EMAIL, P_PW)
    page.goto(f"{BASE}/patient/records")
    shot(page, "a6_patient_records")
    page.goto(f"{BASE}/patient/billing")
    page.locator("text=Pay now").first.click()
    shot(page, "a7_billing")
    page.goto(f"{BASE}/admin/")
    shot(page, "a8_rbac_forbidden")
    page.goto(f"{BASE}/logout")
    # 5. Admin
    login(page, "admin@medicare.local", ADMIN_PW)
    shot(page, "a9_admin_dashboard")
    page.goto(f"{BASE}/admin/audit")
    shot(page, "a10_audit_log")
    b.close()
print("WALKTHROUGH_DONE")
