import pdfplumber
import pandas as pd
import re

AMOUNT_PATTERN = re.compile(r"\$([\d,]+\.\d{2})")

def clean(t):
    t = t.replace("\n", " ")
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def extract_campaign_and_city(cell_text):
    text = clean(cell_text)

    text = re.sub(r"TUPSSCo-op_[A-Za-z0-9]+", "", text)
    text = re.sub(r"\b\d{4,}\b", "", text)

    city = ""
    if "|" in text:
        text, city = text.split("|", 1)
        city = clean(re.sub(r"\b\d{4,}\b", "", city))

    text = text.replace(" _", "_")

    return clean(text), clean(city)


def ttd_parser(uploaded_files):

    rows = []

    for uploaded_file in uploaded_files:

        final_campaign = ""
        final_city = ""
        total_amount = 0.0

        with pdfplumber.open(uploaded_file) as pdf:

            for page in pdf.pages:
                table = page.extract_table()

                if not table:
                    continue

                # remove header
                if table[0] and "ADVERTISER" in (table[0][0] or ""):
                    table = table[1:]

                for row in table:
                    if not row:
                        continue

                    advertiser = row[0] if len(row) > 0 else ""
                    campaign_cell = row[1] if len(row) > 1 else ""
                    charge_desc = row[4] if len(row) > 4 else ""
                    amount = row[5] if len(row) > 5 else ""

                    # Only cost rows
                    if charge_desc and any(x in charge_desc for x in [
                        "Media Cost", "Data Cost", "TTD Fee", "Feature Cost", "Platform Fee"
                    ]):

                        if campaign_cell:
                            campaign, city = extract_campaign_and_city(campaign_cell)

                            if campaign:
                                final_campaign = campaign
                            if city:
                                final_city = city

                        if amount:
                            m = AMOUNT_PATTERN.search(amount)
                            if m:
                                amt = float(m.group(1).replace(",", ""))
                                total_amount += amt

                                rows.append({
                                    "Platform": "TTD",
                                    "Invoice Number": uploaded_file.name,
                                    "Advertiser": advertiser,
                                    "Campaign": final_campaign,
                                    "Insertion Order": None,
                                    "Line Item": None,
                                    "Cost Type": charge_desc,
                                    "Amount": amt,
                                    "Currency": "USD",
                                    "Total Invoice": None
                                })

    return pd.DataFrame(rows)