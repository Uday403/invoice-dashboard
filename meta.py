import fitz
import pandas as pd
import re

def clean_amount(x):
    try:
        return float(x.replace(",", ""))
    except:
        return None


def meta_parser(uploaded_files):

    rows = []

    for uploaded_file in uploaded_files:

        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")

        # ---------- HEADER ----------
        first_page_text = doc[0].get_text("text")

        invoice_number = re.search(r"Invoice\s*#\s*:\s*(\d+)", first_page_text)
        invoice_number = invoice_number.group(1) if invoice_number else uploaded_file.name

        billing_period = re.search(r"Billing\s*Period\s*:\s*([A-Za-z0-9\-]+)", first_page_text)
        billing_period = billing_period.group(1) if billing_period else None

        invoice_total = re.search(r"Invoice\s*Total\s*:\s*([\d,]+\.\d+)", first_page_text)
        invoice_total = clean_amount(invoice_total.group(1)) if invoice_total else None

        advertiser = re.search(r"Advertiser\s*:\s*([^\n]+)", first_page_text)
        advertiser = advertiser.group(1).strip() if advertiser else None

        currency_match = re.search(r"Invoice\s*Currency\s*:\s*([A-Z]+)", first_page_text)
        currency = currency_match.group(1) if currency_match else None

        # ---------- TABLE ----------
        for page in doc:

            lines = page.get_text("text").split("\n")

            buffer = ""

            for line in lines:

                line = line.strip()

                if not line:
                    continue

                amt_match = re.search(r"-?[\d,]+\.\d+$", line)

                if amt_match:

                    amount = clean_amount(amt_match.group())

                    full_row = (buffer + " " + line).strip()

                    # remove junk prefix
                    full_row = re.sub(r".*meta\.com\s*", "", full_row)

                    campaign = full_row.replace(amt_match.group(), "").strip()

                    # ---------- FINAL CLEAN FILTER ----------
                    if (
                        campaign
                        and not any(x in campaign.lower() for x in [
                            "invoice", "total", "gst", "freight", "currency", "conversion"
                        ])
                        and len(campaign) > 10
                    ):

                        campaign = re.sub(r"^\d+\s+", "", campaign)

                        rows.append({
                            "Platform": "Meta",
                            "Invoice Number": invoice_number,
                            "Advertiser": advertiser,
                            "Campaign": campaign,
                            "Insertion Order": None,
                            "Line Item": None,
                            "Cost Type": "Media Cost",
                            "Amount": amount,
                            "Currency": currency,
                            "Total Invoice": invoice_total,
                            "Billing Period": billing_period
                        })

                    buffer = ""

                else:
                    buffer += " " + line

    return pd.DataFrame(rows)