# ITAT Tribunal Order Scraper

This is a Python-based scraper to extract judicial orders from the [Income Tax Appellate Tribunal (ITAT)](https://itat.gov.in/judicial/tribunalorders) website. It automates the process of submitting a tribunal search form, solving CAPTCHA with OCR (EasyOCR), and downloading resulting PDF orders.

## Features

- Automated session handling with CSRF token
- CAPTCHA recognition via EasyOCR with fallback to manual input
- Extracts:
  - Appeal Number
  - Assessment Year
  - Case Status
  - Parties Involved
  - Alpha Bench
  - Downloadable Order Link
- Saves results to `itat_orders.csv`
- Downloads all order PDFs to a local `pdfs/` folder

## Dependencies

- `requests`
- `beautifulsoup4`
- `pandas`
- `Pillow`
- `easyocr`

Install them using:

```bash
pip install -r requirements.txt
