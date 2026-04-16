import fitz
import pandas as pd
import re

def clean_amount(x):
    try:
        return float(x.replace(",", ""))
    except:
        return None


def dcm_parser(uploaded_files):

    rows = []

    for uploaded_file in uploaded_files:

        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")

        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"

        # ---------- HEADER ----------
        invoice_number = re.search(r"Invoice number:\s*(\d+)", full_text)
        invoice_number = invoice_number.group(1) if invoice_number else uploaded_file.name

        total_invoice = re.search(r"Total amount due in USD\s*\$?([\d,]+\.\d+)", full_text)
        total_invoice = clean_amount(total_invoice.group(1)) if total_invoice else None

        currency = "USD"

        # ---------- LINE EXTRACTION ----------
        blocks = re.split(r"Advertiser:", full_text)

        for block in blocks:

            adv_match = re.search(r'"([^"]+)"', block)
            camp_match = re.search(r'Campaign:\s*"([^"]+)"', block)
            fee_match = re.search(r'Fee:\s*([A-Z\s]+)', block)
            amt_match = re.search(r'([\d,]+\.\d+)\s*$', block.strip())

            if adv_match and camp_match and fee_match and amt_match:

                rows.append({
                    "Platform": "DCM",
                    "Invoice Number": invoice_number,
                    "Advertiser": adv_match.group(1),
                    "Campaign": camp_match.group(1),
                    "Insertion Order": None,
                    "Line Item": None,
                    "Cost Type": fee_match.group(1).strip(),
                    "Amount": clean_amount(amt_match.group(1)),
                    "Currency": currency,
                    "Total Invoice": total_invoice
                })

    return pd.DataFrame(rows)