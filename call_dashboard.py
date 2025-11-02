import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Call Center Dashboard", layout="wide")

st.title("📊 Call Center Performance Dashboard")

# ---------- Upload Section ----------
uploaded_file = st.file_uploader("📥 Upload Daily Report (Excel or CSV)", type=["xlsx", "csv"])

if uploaded_file:
    # ---------- Load Data ----------
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("Preview of Uploaded Data")
    st.dataframe(df.head())

    # ---------- Manual Input Section ----------
    st.subheader("✏️ Manual Entry for Cons / Audit / Fatal Count")
    employees = df["Employee Name"].unique()
    manual_data = []

    for emp in employees:
        with st.expander(f"Manual Input for {emp}"):
            cons = st.number_input(f"{emp} - Cons Count", min_value=0, step=1)
            audit = st.number_input(f"{emp} - Audit Count", min_value=0, step=1)
            fatal = st.number_input(f"{emp} - Fatal Count", min_value=0, step=1)
            manual_data.append({"Employee Name": emp, "Cons Count": cons, "Audit Count": audit, "Fatal Count": fatal})

    manual_df = pd.DataFrame(manual_data)
    df = df.merge(manual_df, on="Employee Name", how="left")

    # ---------- Derived Metrics ----------
    df["Completed %"] = df["Completed %"].astype(float)
    df["Productivity%"] = df["Productivity%"].astype(float)

    summary = (
        df.groupby("Employee Name")[["Overall Calls", "Completed Calls", "Missed Calls",
                                     "Cons Count", "Audit Count", "Fatal Count", "Achieve Points", "Productivity%"]]
        .sum()
        .reset_index()
    )

    st.subheader("📈 Employee Performance Summary")
    st.dataframe(summary)

    # ---------- Charts ----------
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📞 Calls Completed by Employee")
        fig1 = px.bar(summary, x="Employee Name", y="Completed Calls", color="Employee Name",
                      title="Completed Calls per Agent")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.markdown("### ⚙️ Productivity % by Employee")
        fig2 = px.bar(summary, x="Employee Name", y="Productivity%",
                      color="Employee Name", title="Productivity % per Agent")
        st.plotly_chart(fig2, use_container_width=True)

    # ---------- Daily Trend ----------
    if "Date" in df.columns:
        st.markdown("### 🗓️ Daily Trend - Completed %")
        daily = df.groupby("Date")["Completed %"].mean().reset_index()
        fig3 = px.line(daily, x="Date", y="Completed %", markers=True, title="Average Completed % by Date")
        st.plotly_chart(fig3, use_container_width=True)

    # ---------- Export ----------
    st.markdown("### 📤 Export Summary")
    csv = summary.to_csv(index=False).encode("utf-8")
    st.download_button("Download Summary CSV", csv, "summary.csv", "text/csv")

else:
    st.info("👆 Please upload your daily Excel or CSV file to start the dashboard.")
