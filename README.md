# ITAT Tribunal Order Scraper

This Python-based scraper extracts judicial orders from the [Income Tax Appellate Tribunal (ITAT)](https://itat.gov.in/judicial/tribunalorders) website. It automates form submission using POST requests, handles CSRF tokens dynamically, solves CAPTCHA using EasyOCR, and downloads order PDFs with relevant case details.

## Features

- **Dynamic CSRF Token Parsing**: The script first makes a `GET` request to the ITAT search page and parses the current CSRF token directly from the HTML form field.
- **CAPTCHA OCR via EasyOCR**: The CAPTCHA image is fetched, saved locally, and decoded using `easyocr.Reader(['en'])`. If the OCR fails, it can be extended to allow manual entry fallback.
- **Form POST Automation**: The script mimics browser behavior by POSTing the form with hardcoded parameters for:
  - Bench: Bangalore (`211`)
  - Appeal Type: Income Tax Appeal (`ITA`)
  - Date of Order: `03/06/2025`
- **Table Data Extraction**: On a successful response, it parses all rows from the resulting HTML table, extracting:
  - Appeal Number
  - Assessment Year
  - Case Status
  - Parties Involved
  - Alpha Bench
  - Order Link
- **File Output**:
  - Saves metadata to `itat_orders.csv`
  - Downloads PDF orders into the `pdfs/` directory

## 🛠️ Dependencies

Install all required packages via:

```bash
pip install -r requirements.txt
