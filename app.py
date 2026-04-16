import streamlit as st
import pandas as pd
import time
import importlib
import os
from PIL import Image

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Invoice Extraction Tool", layout="wide")

# =========================
# LOAD LOGO (SAFE)
# =========================
logo = None
logo_path = "assembly_logo.png"

if os.path.exists(logo_path):
    logo = Image.open(logo_path)

# =========================
# HEADER
# =========================
col1, col2 = st.columns([1, 5])

with col1:
    if logo:
        st.image(logo, width=120)

with col2:
    st.title("Invoice Extraction Tool")
    st.caption("Internal Tool | Fast Extraction + QA")

# =========================
# PLATFORM LIST
# =========================
PLATFORMS = [
    "DV360",
    "Meta",
    "DCM",
    "TTD",
    "Yahoo",
    "MIQ",
    "DoubleVerify",
    "Adtheorent"
]

platform = st.selectbox("Select Platform", PLATFORMS)

uploaded_files = st.file_uploader(
    "Upload Invoice PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

# =========================
# PARSER MAP (DYNAMIC)
# =========================
PARSER_MAP = {
    "DV360": "dv360",
    "Meta": "meta",
    "DCM": "dcm",
    "TTD": "ttd",
    "Yahoo": "yahoo",
    "MIQ": "miq",
    "DoubleVerify": "doubleverify",
    "Adtheorent": "adtheorent"
}

# =========================
# FALLBACK PARSER
# =========================
def dummy_parser(files, platform):
    rows = []
    for file in files:
        rows.append({
            "Platform": platform,
            "Invoice Number": file.name,
            "Advertiser": None,
            "Campaign": None,
            "Insertion Order": None,
            "Line Item": None,
            "Cost Type": None,
            "Amount": None,
            "Currency": None,
            "Total Invoice": None
        })
    return pd.DataFrame(rows)

# =========================
# MAIN PROCESS
# =========================
if uploaded_files:

    start_time = time.time()

    parser_name = PARSER_MAP.get(platform)

    if parser_name:
        try:
            module = importlib.import_module(f"parsers.{parser_name}")
            parser_function = getattr(module, f"{parser_name}_parser")
            df = parser_function(uploaded_files)
        except Exception as e:
            st.error(f"{platform} parser error: {e}")
            st.stop()
    else:
        df = dummy_parser(uploaded_files, platform)

    process_time = round(time.time() - start_time, 2)

    if df.empty:
        st.error("No data extracted. Check invoice format.")
        st.stop()

    # =========================
    # KPIs
    # =========================
    col1, col2, col3 = st.columns(3)

    col1.metric("Total Rows", len(df))
    col2.metric(
        "Total Spend",
        f"${df['Amount'].sum():,.2f}" if "Amount" in df.columns and df["Amount"].notna().any() else "$0"
    )
    col3.metric("Processing Time", f"{process_time}s")

    st.divider()

    # =========================
    # QA CHECKS
    # =========================
    st.subheader("⚠️ Data Quality Checks")

    for col in ["Campaign", "Insertion Order", "Amount", "Invoice Number", "Total Invoice"]:
        if col not in df.columns:
            df[col] = None

    df["Missing Data"] = df[[
        "Campaign", "Insertion Order", "Amount"
    ]].isnull().any(axis=1)

    invoice_totals = df.groupby("Invoice Number", dropna=False)["Amount"].sum().reset_index()
    invoice_totals.columns = ["Invoice Number", "Calculated Total"]

    df = df.merge(invoice_totals, on="Invoice Number", how="left")
    df["Difference"] = df["Total Invoice"] - df["Calculated Total"]

    col1, col2 = st.columns(2)
    col1.metric("Rows with Missing Data", int(df["Missing Data"].sum()))
    col2.metric("Invoices with Mismatch", int((df["Difference"] != 0).sum()))

    st.divider()

    # =========================
    # FILTERS
    # =========================
    st.subheader("🔍 Filters")

    filters = {}
    for col in df.columns:
        unique_vals = df[col].dropna().unique()

        if len(unique_vals) > 0 and len(unique_vals) < 100:
            selected = st.multiselect(col, unique_vals)
            if selected:
                filters[col] = selected

    filtered_df = df.copy()

    for col, vals in filters.items():
        filtered_df = filtered_df[filtered_df[col].isin(vals)]

    # =========================
    # COLUMN SELECTOR
    # =========================
    st.subheader("📑 Select Columns")

    selected_cols = st.multiselect(
        "Choose columns to display",
        filtered_df.columns.tolist(),
        default=filtered_df.columns.tolist()
    )

    final_df = filtered_df[selected_cols]

    # =========================
    # DATA TABLE
    # =========================
    st.subheader("📋 Extracted Data")

    def highlight_issues(row):
        if row.get("Missing Data") or (pd.notna(row.get("Difference")) and row.get("Difference") != 0):
            return ["background-color: #ffcccc"] * len(row)
        return [""] * len(row)

    st.dataframe(
        final_df.style.apply(highlight_issues, axis=1),
        use_container_width=True
    )

    # =========================
    # DOWNLOAD
    # =========================
    st.subheader("⬇️ Download")

    output_file = "Invoice_Output.xlsx"
    with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
        final_df.to_excel(writer, index=False, sheet_name="Data")

    with open(output_file, "rb") as f:
        st.download_button(
            "Download Excel",
            f,
            file_name=output_file
        )

else:
    st.info("Upload PDFs to start extraction")