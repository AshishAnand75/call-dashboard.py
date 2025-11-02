# call_dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import os
from io import BytesIO
from datetime import datetime

# ---------------------------
# Config & Helpers
# ---------------------------
st.set_page_config(page_title="Call Center Module", layout="wide")

DATA_DIR = "data"
MASTER_FILE = os.path.join(DATA_DIR, "master_data.xlsx")

REQUIRED_COLUMNS = [
    "Date", "Employee Name", "Overall Calls", "Completed Calls", "Completed %",
    "Incoming Calls", "Incoming completed call", "Incoming %", "Outbound Calls",
    "Missed Calls", "Login Hours", "Cons Count", "Audit Count", "Fatal Count",
    "Total Points", "Achieve Points", "Productivity%"
]

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def read_master():
    ensure_data_dir()
    if os.path.exists(MASTER_FILE):
        try:
            df = pd.read_excel(MASTER_FILE, engine="openpyxl")
            return df
        except Exception as e:
            st.error(f"Failed to read master file: {e}")
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
    else:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

def save_master(df):
    ensure_data_dir()
    try:
        df.to_excel(MASTER_FILE, index=False, engine="openpyxl")
    except Exception as e:
        st.error(f"Failed to save master file: {e}")

def clean_and_normalize(df):
    # Basic normalization: ensure required columns exist, convert types where possible
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Parse Date
    if "Date" in df.columns:
        try:
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
        except:
            # attempt different parsing
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date

    # Numeric conversions (safe)
    numeric_cols = ["Overall Calls", "Completed Calls", "Missed Calls", "Login Hours",
                    "Cons Count", "Audit Count", "Fatal Count", "Total Points",
                    "Achieve Points", "Productivity%"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Completed % and Incoming % may be strings with % sign
    for pct_col in ["Completed %", "Incoming %"]:
        if pct_col in df.columns:
            df[pct_col] = df[pct_col].astype(str).str.replace("%", "").replace("nan", "")
            df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce").fillna(0)

    return df[REQUIRED_COLUMNS]

def append_to_master(new_df):
    master = read_master()
    new_df = clean_and_normalize(new_df)
    if master.empty:
        combined = new_df
    else:
        # append and drop exact duplicates (optional)
        combined = pd.concat([master, new_df], ignore_index=True)
        combined.drop_duplicates(subset=REQUIRED_COLUMNS, keep="last", inplace=True)
    save_master(combined)
    return combined

def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Summary")
        writer.save()
    processed_data = output.getvalue()
    return processed_data

# ---------------------------
# UI: Sidebar - Navigation
# ---------------------------
st.sidebar.title("Call Module")
page = st.sidebar.radio("Navigate", ["Upload Data", "View Data", "Dashboard", "Manual Entry", "Export / Download"])

# ---------------------------
# Page: Upload Data
# ---------------------------
if page == "Upload Data":
    st.header("📥 Upload Daily Report")
    st.markdown("""
    - Upload a daily CSV or Excel file with columns like:
      `Date, Employee Name, Overall Calls, Completed Calls, Completed %, Incoming Calls, Incoming completed call, Incoming %, Outbound Calls, Missed Calls, Login Hours, Total Points, Achieve Points, Productivity%`.
    - If your file lacks `Cons Count, Audit Count, Fatal Count`, you can add them later in **Manual Entry**.
    """)
    uploaded_file = st.file_uploader("Choose an Excel (.xlsx) or CSV file", type=["xlsx", "csv"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                new_df = pd.read_csv(uploaded_file)
            else:
                new_df = pd.read_excel(uploaded_file, engine="openpyxl")
            st.success(f"Loaded `{uploaded_file.name}` — preview below.")
            st.dataframe(new_df.head())
            if st.button("Append to master data"):
                combined = append_to_master(new_df)
                st.success(f"Appended {len(new_df)} rows. Master now has {len(combined)} rows.")
                st.dataframe(combined.tail(10))
        except Exception as e:
            st.error(f"Failed to read uploaded file: {e}")

# ---------------------------
# Page: View Data
# ---------------------------
elif page == "View Data":
    st.header("🗂 View Master Data")
    master = read_master()
    if master.empty:
        st.info("No master data found. Upload a sheet first.")
    else:
        st.markdown("Use filters to inspect data:")
        c1, c2 = st.columns([2,1])
        with c1:
            name_filter = st.selectbox("Filter by Employee (All = show all)", options=["All"] + sorted(master["Employee Name"].dropna().unique().tolist()))
        with c2:
            date_filter = st.date_input("Filter by Date (optional)", value=None)

        df_view = master.copy()
        if name_filter != "All":
            df_view = df_view[df_view["Employee Name"] == name_filter]
        if date_filter:
            # date_input returns date; filter exact date
            df_view = df_view[df_view["Date"] == date_filter]

        st.dataframe(df_view.sort_values(by=["Date"], ascending=False).reset_index(drop=True))
        st.markdown(f"Total rows: **{len(df_view)}**")

# ---------------------------
# Page: Dashboard
# ---------------------------
elif page == "Dashboard":
    st.header("📊 Performance Dashboard")
    master = read_master()
    if master.empty:
        st.info("No data yet. Upload data in the Upload Data tab.")
    else:
        master = clean_and_normalize(master)

        # Filters
        st.sidebar.markdown("### Filters")
        months = sorted(pd.Series([d for d in master["Date"].dropna()]).apply(lambda x: x.replace(day=1)).unique().tolist())
        months_display = ["All"] + [m.strftime("%Y-%m") for m in months] if len(months) else ["All"]
        month_choice = st.sidebar.selectbox("Month (YYYY-MM)", options=months_display, index=0)

        employees = ["All"] + sorted(master["Employee Name"].dropna().unique().tolist())
        emp_choice = st.sidebar.selectbox("Employee", options=employees, index=0)

        df_dash = master.copy()
        if month_choice != "All":
            year, mon = map(int, month_choice.split("-"))
            df_dash = df_dash[(pd.to_datetime(df_dash["Date"]).dt.year == year) & (pd.to_datetime(df_dash["Date"]).dt.month == mon)]
        if emp_choice != "All":
            df_dash = df_dash[df_dash["Employee Name"] == emp_choice]

        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        total_calls = int(df_dash["Overall Calls"].sum())
        completed_calls = int(df_dash["Completed Calls"].sum())
        avg_completed_pct = round(df_dash["Completed %"].replace("", 0).astype(float).mean(), 2) if len(df_dash) else 0
        avg_productivity = round(df_dash["Productivity%"].astype(float).mean(), 2) if len(df_dash) else 0

        col1.metric("Total Calls", f"{total_calls:,}")
        col2.metric("Completed Calls", f"{completed_calls:,}")
        col3.metric("Avg Completed %", f"{avg_completed_pct}%")
        col4.metric("Avg Productivity %", f"{avg_productivity}%")

        st.markdown("---")

        # Employee summary
        st.subheader("Agent Summary")
        summary = (
            df_dash.groupby("Employee Name", dropna=False)[["Overall Calls", "Completed Calls", "Missed Calls", "Login Hours", "Cons Count", "Audit Count", "Fatal Count", "Achieve Points", "Productivity%"]]
            .sum()
            .reset_index()
            .sort_values(by="Completed Calls", ascending=False)
        )
        st.dataframe(summary.style.format({"Productivity%": "{:.2f}"}))

        # Charts
        st.subheader("Charts")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Completed Calls by Agent**")
            fig1 = px.bar(summary, x="Employee Name", y="Completed Calls", title="Completed Calls per Agent", labels={"Employee Name":"Agent"})
            st.plotly_chart(fig1, use_container_width=True)

        with c2:
            st.markdown("**Average Productivity % by Agent**")
            fig2 = px.bar(summary, x="Employee Name", y="Productivity%", title="Productivity % per Agent")
            st.plotly_chart(fig2, use_container_width=True)

        # Daily trend across selected month/period
        st.subheader("Daily Trends")
        if len(df_dash):
            daily = df_dash.groupby("Date").agg({
                "Overall Calls":"sum",
                "Completed Calls":"sum",
                "Productivity%":"mean",
                "Missed Calls":"sum"
            }).reset_index()
            fig3 = px.line(daily, x="Date", y="Completed Calls", markers=True, title="Daily Completed Calls")
            st.plotly_chart(fig3, use_container_width=True)

# ---------------------------
# Page: Manual Entry
# ---------------------------
elif page == "Manual Entry":
    st.header("✏️ Manual entry: Cons Count, Audit Count, Fatal Count")
    master = read_master()
    if master.empty:
        st.info("No data yet. Upload a sheet first.")
    else:
        # Select Employee and Date to update
        st.markdown("Choose the record (Employee + Date) to update. If multiple rows match, all will be updated.")
        employees = sorted(master["Employee Name"].dropna().unique().tolist())
        emp = st.selectbox("Employee", options=employees)
        dates = sorted(master[master["Employee Name"] == emp]["Date"].dropna().unique().tolist())
        if not dates:
            st.warning("No date entries for this employee in master data.")
        else:
            dt = st.selectbox("Date", options=dates)
            # show existing records
            mask = (master["Employee Name"] == emp) & (master["Date"] == pd.to_datetime(dt).date() if not isinstance(dt, pd.Timestamp) else pd.to_datetime(dt).date())
            st.write("Existing records:")
            st.dataframe(master[mask])

            with st.form("manual_update_form"):
                cons = st.number_input("Cons Count", min_value=0, value=int(master.loc[mask, "Cons Count"].sum() if mask.any() else 0))
                audit = st.number_input("Audit Count", min_value=0, value=int(master.loc[mask, "Audit Count"].sum() if mask.any() else 0))
                fatal = st.number_input("Fatal Count", min_value=0, value=int(master.loc[mask, "Fatal Count"].sum() if mask.any() else 0))
                submitted = st.form_submit_button("Save Manual Counts")
                if submitted:
                    master.loc[mask, "Cons Count"] = cons
                    master.loc[mask, "Audit Count"] = audit
                    master.loc[mask, "Fatal Count"] = fatal
                    save_master(master)
                    st.success("Manual counts updated in master data.")
                    st.dataframe(master[mask])

# ---------------------------
# Page: Export / Download
# ---------------------------
elif page == "Export / Download":
    st.header("📤 Export & Download")
    master = read_master()
    if master.empty:
        st.info("No data yet.")
    else:
        st.markdown("Download full master dataset or filtered summary.")
        if st.button("Download full master Excel"):
            bytes_data = df_to_excel_bytes(master)
            st.download_button("Download master_data.xlsx", data=bytes_data, file_name="master_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("Or create a monthly summary:")
        months = sorted(pd.Series([d for d in master["Date"].dropna()]).apply(lambda x: x.replace(day=1)).unique().tolist())
        months_display = [m.strftime("%Y-%m") for m in months] if len(months) else []
        chosen = st.selectbox("Choose month for summary", options=["--"] + months_display)
        if chosen and chosen != "--":
            y, m = map(int, chosen.split("-"))
            df_summary = master[(pd.to_datetime(master["Date"]).dt.year == y) & (pd.to_datetime(master["Date"]).dt.month == m)]
            if df_summary.empty:
                st.warning("No data for this month.")
            else:
                agg = df_summary.groupby("Employee Name")[["Overall Calls", "Completed Calls", "Missed Calls", "Cons Count", "Audit Count", "Fatal Count", "Achieve Points", "Productivity%"]].sum().reset_index()
                st.dataframe(agg)
                bytes_data = df_to_excel_bytes(agg)
                st.download_button("Download monthly_summary.xlsx", data=bytes_data, file_name=f"monthly_summary_{chosen}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------------------
# End
# ---------------------------
st.sidebar.markdown("---")
st.sidebar.caption("Module: local master_data.xlsx storage (data/). For persistent remote storage, use Google Sheets or a DB.")
