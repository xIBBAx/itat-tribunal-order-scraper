import re
import numpy as np # type: ignore
import requests
from bs4 import BeautifulSoup
import pandas as pd # type: ignore
import os
from PIL import Image
from PIL import ImageFilter
from io import BytesIO
from urllib.parse import urljoin
import cv2 # type: ignore
import pytesseract # type: ignore
import time
from datetime import datetime, timedelta
import random

# Step 1: Set up
URL = "https://itat.gov.in/judicial/tribunalorders"

session = requests.Session()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 13_6 like Mac OS X)",
]
session.headers.update({
    "User-Agent": random.choice(USER_AGENTS)
})

os.makedirs("pdfs", exist_ok=True)

# Step 2: Get CSRF and captcha
def get_form_state():
    # Retry GET if we hit 403 or similar errors
    for i in range(5):
        r = session.get(URL)
        if r.status_code == 200:
            break
        wait = 2 ** (i + 1)
        print(f"GET {URL} returned {r.status_code}, retrying in {wait}s...")
        time.sleep(wait)
    else:
        print(f"Permanent failure: GET {URL} returned {r.status_code} too many times.")
        return None, None

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
    
    
    # Delay to avoid hitting CAPTCHA endpoint too frequently
    time.sleep(2)  # Wait 2 seconds before downloading CAPTCHA
    
    captcha_response = session.get(captcha_url)

    img_array = np.asarray(bytearray(captcha_response.content), dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)

    # Resize
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_LINEAR)

    # thresholding
    _, img = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY_INV)

    # to remove noise
    img = cv2.medianBlur(img, 3)
    
    img_path = "captcha_processed.png"
    cv2.imwrite(img_path, img)

    # OCR config
    config = "--psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    captcha_text = pytesseract.image_to_string(img, config=config).strip().upper()
    captcha_text = re.sub(r'\W+', '', captcha_text)

    print(f"OCR-detected CAPTCHA: {captcha_text}")

    # if not captcha_text or len(captcha_text) < 4 or not captcha_text.isalnum():
    #     print(f"\nOCR may have failed. Please check the CAPTCHA image at: {os.path.abspath(img_path)}")
    #     captcha_text = input("Please enter the CAPTCHA manually: ").strip()

    return csrf_token, captcha_text

# Step 3: Submit request
def scrape_tribunal_orders():
    MAX_RETRIES = 10
    
    start_date = datetime.strptime("01/01/2010", "%d/%m/%Y")
    end_date = datetime.strptime("31/12/2011", "%d/%m/%Y")

    DATES = []
    current = start_date
    while current <= end_date:
        DATES.append(current.strftime("%d/%m/%Y"))
        current += timedelta(days=1)

    for order_date in DATES:
        print(f"\nScraping for Order Date: {order_date}")
        for attempt in range(1, MAX_RETRIES + 1):
            print(f"Attempt {attempt} of {MAX_RETRIES}")
            csrf_token, captcha_text = get_form_state()

            payload = {
                "csrftkn": csrf_token,
                "bench_name_2": "199",  # Mumbai
                "app_type_2": "ITA",    # ITA Income Tax Appeal
                "order_date": order_date,
                "bt2": "true",
                "c2": captcha_text
            }

            response = session.post(URL, data=payload)
            with open(f"debug_response_{order_date.replace('/', '-')}.html", "w", encoding="utf-8") as f:
                f.write(response.text)

            if "Please enter correct captcha" in response.text:
                print("Wrong CAPTCHA detected. Retrying...")
                time.sleep(1)
                continue

            if "No Records Found" in response.text:
                print("CAPTCHA accepted, but no records found. Skipping to next date.")
                break  # Skip retrying, move to next date

            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table", class_="table table-striped table-bordered")
            if not table:
                print("Table not found (likely CAPTCHA failure). Retrying...")
                time.sleep(1)
                continue

            print("CAPTCHA passed. Extracting table...")
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
                    "Order Date": order_date,
                    "Appeal Number": appeal_number,
                    "Assessment Year": assessment_year,
                    "Case Status": case_status,
                    "Parties": parties,
                    "Alpha Bench": alpha_bench,
                    "Order Link": order_link
                })

                if order_link:
                    pdf_url = urljoin("https://itat.gov.in", order_link)
                    pdf_resp = session.get(pdf_url)
                    filename = f"pdfs/{appeal_number[:50].replace('/', '_')}_{order_date.replace('/', '-')}.pdf"
                    with open(filename, "wb") as f:
                        f.write(pdf_resp.content)

            if results:
                pd.DataFrame(results).to_csv(f"itat_orders_{order_date.replace('/', '-')}.csv", index=False)
                print(f"Done. Saved to itat_orders_{order_date.replace('/', '-')}.csv")
            else:
                print("Table found, but no data rows.")
            break 

        else:
            print(f"Max retries exceeded for {order_date}. Skipping to next date.")
# Step 4: Run
scrape_tribunal_orders()
