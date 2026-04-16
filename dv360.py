import fitz  # PyMuPDF
import pandas as pd
import re

def clean_amount(x):
    try:
        return float(x.replace(",", "").strip())
    except:
        return None

def dv360_parser(uploaded_files):

    rows = []

    for file in uploaded_files:

        doc = fitz.open(stream=file.read(), filetype="pdf")

        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"

        # -------- CLEAN TEXT --------
        full_text = re.sub(r'\n+', '\n', full_text)

        # -------- HEADER --------
        invoice_number = re.search(r"Invoice number:\s*(\d+)", full_text)
        invoice_number = invoice_number.group(1) if invoice_number else None

        total_invoice = re.search(r"Total amount due in USD\s*\$?([\d,]+\.\d+)", full_text)
        total_invoice = clean_amount(total_invoice.group(1)) if total_invoice else None

        currency = "USD"

        # -------- SPLIT INTO LINES --------
        lines = full_text.split("\n")

        buffer = ""
        current_cost_type = None

        for line in lines:

            line = line.strip()

            if not line:
                continue

            # -------- DETECT COST BLOCK --------
            if any(x in line for x in [
                "Media Cost",
                "Platform Fee",
                "Third Party Fees",
                "Overdelivery Adjustment",
                "Data Fee",
                "Adjustment"
            ]):

                # Normalize Cost Type
                if "Media Cost" in line:
                    current_cost_type = "Media Cost"
                else:
                    current_cost_type = "Fee Cost"

                buffer = line
                continue

            # -------- BUILD MULTI-LINE BLOCK --------
            if current_cost_type:
                buffer += " " + line

                # -------- DETECT AMOUNT (INCLUDING NEGATIVE) --------
                amt_match = re.search(r"(-?\d{1,3}(?:,\d{3})*\.\d{2})$", line)

                if amt_match:

                    amount = clean_amount(amt_match.group(1))

                    # -------- EXTRACT FIELDS --------
                    advertiser = None
                    campaign = None
                    io = None

                    adv_match = re.search(r"Advertiser:\s*(.*?)\s*ID:", buffer)
                    if adv_match:
                        advertiser = adv_match.group(1).strip()

                    camp_match = re.search(r"Campaign:\s*(.*?)\s*ID:", buffer)
                    if camp_match:
                        campaign = re.sub(r"\s+", " ", camp_match.group(1)).strip()

                    io_match = re.search(r"Insertion Order:\s*(.*?)\s*ID:", buffer)
                    if io_match:
                        io = re.sub(r"\s+", " ", io_match.group(1)).strip()

                    rows.append({
                        "Platform": "DV360",
                        "Invoice Number": invoice_number,
                        "Advertiser": advertiser,
                        "Campaign": campaign,
                        "Insertion Order": io,
                        "Line Item": None,
                        "Cost Type": current_cost_type,
                        "Amount": amount,
                        "Currency": currency,
                        "Total Invoice": total_invoice
                    })

                    # RESET BLOCK
                    buffer = ""
                    current_cost_type = None

    return pd.DataFrame(rows)