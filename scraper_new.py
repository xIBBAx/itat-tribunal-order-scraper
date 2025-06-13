import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from PIL import Image
from PIL import ImageFilter
from io import BytesIO
from urllib.parse import urljoin
import easyocr

# Step 1: Set up
URL = "https://itat.gov.in/judicial/tribunalorders"
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
})

reader = easyocr.Reader(["en"])

os.makedirs("pdfs", exist_ok=True)

# Step 2: Get CSRF and captcha
def get_form_state():
    r = session.get(URL)
    soup = BeautifulSoup(r.text, "html.parser")

    csrf_input = soup.find("input", {"name": "csrftkn"})
    csrf_token = csrf_input["value"] if csrf_input else None

    captcha_img_tag = soup.find("img", src=lambda s: s and "captcha" in s.lower())
    if not captcha_img_tag:
        print("Captcha image not found. Debug written to debug.html")
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        exit(1)

    captcha_url = urljoin(URL, captcha_img_tag["src"])
    captcha_response = session.get(captcha_url)
    img = Image.open(BytesIO(captcha_response.content)).convert("L")

    threshold = 150
    img = img.point(lambda x: 0 if x < threshold else 255)
    img = img.resize((img.width * 2, img.height * 2))
    
    img_path = "captcha.png"
    img.save(img_path)

    captcha_texts = reader.readtext(img_path, detail=0)
    captcha_text = "".join(captcha_texts).replace(" ", "").strip()

    print(f"OCR-detected CAPTCHA: {captcha_text}")

    if not captcha_text or len(captcha_text) < 4 or not captcha_text.isalnum():
        print(f"\nOCR may have failed. Please open and check the CAPTCHA image at: {os.path.abspath(img_path)}")
        captcha_text = input("Please enter the CAPTCHA manually: ").strip()

    return csrf_token, captcha_text

# Step 3: Submit request with hardcoded test data
def scrape_tribunal_orders():
    csrf_token, captcha_text = get_form_state()

    payload = {
        "csrftkn": csrf_token,
        "bench_name_2": "211",  # Bangalore
        "app_type_2": "ITA",    # ITA Income Tax Appeal
        "order_date": "03/06/2025",
        "bt2": "true"
    }

    payload["c2"] = captcha_text

    response = session.post(URL, data=payload)
    with open("debug_response.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    if "Please enter correct captcha" in response.text:
        print("Wrong captcha. Try again.")
        return
    if "No Records Found" in response.text:
        print("No records found.")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="table table-striped table-bordered")
    if not table:
        print("Table not found in response.")
        return

    results = []
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        lines = [line.strip() for line in cols[0].stripped_strings]
        appeal_number = lines[0] if len(lines) > 0 else ""
        assessment_year = lines[1] if len(lines) > 1 else ""
        case_status = lines[2] if len(lines) > 2 else ""
        parties = cols[1].text.strip()
        alpha_bench = cols[2].text.strip()
        order_link_tag = cols[3].find("a")
        order_link = order_link_tag["href"] if order_link_tag else ""

        results.append({
            "Appeal Number": appeal_number,
            "Assessment Year": assessment_year,
            "Case Status": case_status,
            "Parties": parties,
            "Alpha Bench": alpha_bench,
            "Order Link": order_link
        })

        # Download the PDF
        if order_link:
            pdf_url = urljoin("https://itat.gov.in", order_link)
            pdf_resp = session.get(pdf_url)
            filename = f"pdfs/{appeal_number[:50].replace('/', '_')}.pdf"
            with open(filename, "wb") as f:
                f.write(pdf_resp.content)

    if results:
        pd.DataFrame(results).to_csv("itat_orders.csv", index=False)
        print("Done, Saved to itat_orders.csv")

# Step 4: Run
scrape_tribunal_orders()
