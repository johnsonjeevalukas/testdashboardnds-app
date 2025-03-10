import streamlit as st
import pandas as pd
import plotly.express as px

# Load Data from Excel
file_path = "data.xlsx"
sheet_name = "part_ord_master"

def load_data():
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        df["DELIVERY_DATE"] = pd.to_datetime(df["DELIVERY_DATE"], errors="coerce")
        return df.dropna(subset=["DELIVERY_DATE"])  # Drop rows with invalid dates
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

data = load_data()

# Sidebar Filters
st.sidebar.header("Filter Data")
from_date = st.sidebar.date_input("From Date", pd.to_datetime("2024-01-01"))
to_date = st.sidebar.date_input("To Date", pd.to_datetime("today"))

# Filter by date range
data_filtered = data[(data["DELIVERY_DATE"] >= pd.Timestamp(from_date)) &
                     (data["DELIVERY_DATE"] <= pd.Timestamp(to_date))]

# Filter by ZIP Code if available
if "ZIP_CODE" in data.columns:
    zip_code_list = ["All"] + data["ZIP_CODE"].dropna().astype(str).unique().tolist()
    selected_zip = st.sidebar.selectbox("Select Zip Code", zip_code_list)
    if selected_zip != "All":
        data_filtered = data_filtered[data_filtered["ZIP_CODE"] == selected_zip]

# Calculate Order Status Counts
today = pd.Timestamp.today()
upcoming_count = data_filtered[(data_filtered["DELIVERY_DATE"] > today) & (data_filtered["STATUS"] != "CANCELED")].shape[0]
completed_count = data_filtered[(data_filtered["DELIVERY_DATE"] <= today) & (data_filtered["STATUS"] == "COMPLETED")].shape[0]
pending_count = data_filtered[(data_filtered["DELIVERY_DATE"] <= today) & (data_filtered["STATUS"] == "OPEN")].shape[0]
canceled_count = data_filtered[(data_filtered["DELIVERY_DATE"] <= today) & (data_filtered["STATUS"] == "CANCELED")].shape[0]

# Payment Type Distribution
if {"PAYMENT_TYPE", "NET_AMOUNT"}.issubset(data_filtered.columns):
    payment_summary = data_filtered.groupby("PAYMENT_TYPE")["NET_AMOUNT"].sum().reset_index()
else:
    payment_summary = pd.DataFrame({"PAYMENT_TYPE": [], "NET_AMOUNT": []})

# Discount & Net Amount Calculation
if {"TOTAL", "DISCOUNT_PERCENT", "NET_AMOUNT"}.issubset(data_filtered.columns):
    discount_amt = (data_filtered["TOTAL"] * data_filtered["DISCOUNT_PERCENT"] / 100).sum()
    net_amt = data_filtered["NET_AMOUNT"].sum()
    discount_data = pd.DataFrame({"AMT_TYPE": ["DISCOUNT AMOUNT", "NET AMOUNT"], "AMT": [discount_amt, net_amt]})
else:
    discount_data = pd.DataFrame({"AMT_TYPE": [], "AMT": []})

# Monthly Order Count
if {"DELIVERY_DATE", "TRAY_ORDER_ID"}.issubset(data_filtered.columns):
    data_filtered["MONTH_NAME"] = data_filtered["DELIVERY_DATE"].dt.strftime("%B")
    data_filtered["MONTH_NUMBER"] = data_filtered["DELIVERY_DATE"].dt.month
    data_filtered["YEAR"] = data_filtered["DELIVERY_DATE"].dt.year
    order_summary = data_filtered.groupby(["YEAR", "MONTH_NAME", "MONTH_NUMBER"]).size().reset_index(name="COUNT_ORD")
    order_summary = order_summary.sort_values(by=["YEAR", "MONTH_NUMBER"], ascending=[False, False])
else:
    order_summary = pd.DataFrame({"MONTH_NAME": [], "MONTH_NUMBER": [], "YEAR": [], "COUNT_ORD": []})

# Data for Visualization
status_data = pd.DataFrame({"Status": ["Upcoming", "Completed", "Pending", "Canceled"],
                            "Count": [upcoming_count, completed_count, pending_count, canceled_count]})

# Charts
pie_chart = px.pie(status_data, values="Count", names="Status", hole=0.4, title="Order Status Distribution")
pie_chart2 = px.pie(payment_summary, values="NET_AMOUNT", names="PAYMENT_TYPE", hole=0.4, title="Payment Type Distribution")
pie_chart3 = px.pie(discount_data, values="AMT", names="AMT_TYPE", hole=0.4, title="Discount and Net Amount")

bar_chart = px.bar(status_data, x="Status", y="Count", color="Status", title="Order Status Count")

if not order_summary.empty:
    fig = px.bar(order_summary, x="MONTH_NAME", y="COUNT_ORD", text="COUNT_ORD", opacity=0.7,
                 labels={"COUNT_ORD": "Order Count", "MONTH_NAME": "Month"},
                 title="Monthly Order Count")
else:
    fig = None

# Streamlit Layout
st.title(" :bar_chart: Party Order Status Dashboard")

col1, col2, col3 = st.columns(3)
with col1:
    st.plotly_chart(pie_chart3, use_container_width=True)
with col2:
    st.plotly_chart(pie_chart, use_container_width=True)
with col3:
    st.plotly_chart(pie_chart2, use_container_width=True)

if fig:
    st.plotly_chart(fig, use_container_width=True)

st.plotly_chart(bar_chart, use_container_width=True)
