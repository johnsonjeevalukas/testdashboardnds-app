import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px
from datetime import datetime

# 👉 Database connection details
server = "172.18.1.25"
database = "JBB_POS_CL"
username = "dev_user"
password = "newdream@1234"

conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"

# 👉 Streamlit Sidebar
st.sidebar.header("Filter Data")

# ✅ Date Filter
from_date = st.sidebar.date_input("From Date", value=pd.to_datetime('2024-12-01'))
to_date = st.sidebar.date_input("To Date", value=pd.to_datetime(datetime.today().date()))

if from_date and to_date:
    from_date = from_date.strftime('%Y-%m-%d')
    to_date = to_date.strftime('%Y-%m-%d')
    date_filter = f"AND DELIVERY_DATE BETWEEN '{from_date}' AND '{to_date}'"
else:
    date_filter = ""

# ✅ Zip Code Filter
try:
    with pyodbc.connect(conn_str) as conn:
        zip_codes = pd.read_sql_query("SELECT DISTINCT ZIP_CODE FROM T_ECOMM_PARTY_ORD_MASTER", conn)
        zip_code_list = ["All"] + zip_codes["ZIP_CODE"].dropna().astype(str).tolist()
except Exception as e:
    zip_code_list = ["All"]

selected_zip = st.sidebar.selectbox("Select Zip Code", zip_code_list)
zip_filter = f"AND ZIP_CODE = '{selected_zip}'" if selected_zip != "All" else ""

# 👉 SQL Queries
UPCOMING_PARTY_COUNT = f"""
    SELECT COUNT(TRAY_ORDER_ID) AS COUNT 
    FROM T_ECOMM_PARTY_ORD_MASTER 
    WHERE DELIVERY_DATE > GETDATE() AND STATUS != 'CANCELED' {date_filter} {zip_filter}
"""

COMPLETED_PARTY_COUNT = f"""
    SELECT COUNT(TRAY_ORDER_ID) AS COUNT 
    FROM T_ECOMM_PARTY_ORD_MASTER 
    WHERE DELIVERY_DATE <= GETDATE() AND STATUS = 'COMPLETED' {date_filter} {zip_filter}
"""

PENDING_PARTY_COUNT = f"""
    SELECT COUNT(TRAY_ORDER_ID) AS COUNT 
    FROM T_ECOMM_PARTY_ORD_MASTER 
    WHERE DELIVERY_DATE <= GETDATE() AND STATUS = 'OPEN' {date_filter} {zip_filter}
"""

CANCELED_PARTY_COUNT = f"""
    SELECT COUNT(TRAY_ORDER_ID) AS COUNT 
    FROM T_ECOMM_PARTY_ORD_MASTER 
    WHERE DELIVERY_DATE <= GETDATE() AND STATUS = 'CANCELED' {date_filter} {zip_filter}
"""

PAYMENT_TYP_WISE_QUERY = f"""
    SELECT SUM(PYMNT.PAYMENT_AMOUNT) AS PAYMENT_AMOUNT, PYMNT.PAYMENT_TYPE 
    FROM T_ECOMM_PARTY_ORD_MASTER OM 
    INNER JOIN T_ECOMM_PARTY_ORDER_PAYMENTS_HISTORY PYMNT 
    ON PYMNT.TRAY_ORDER_ID = OM.TRAY_ORDER_ID 
    WHERE 1=1 {date_filter} {zip_filter}
    GROUP BY PYMNT.PAYMENT_TYPE
"""

DIFF_DISCOUNT_NETAMT = f"""
    SELECT 'DISCOUNT AMOUNT' AS AMT_TYPE, SUM((TOTAL * DISCOUNT_PERCENT) / 100) AS AMT 
    FROM T_ECOMM_PARTY_ORD_MASTER WHERE 1=1 {date_filter} {zip_filter}
    UNION ALL
    SELECT 'NET AMOUNT', SUM(NET_AMOUNT) FROM T_ECOMM_PARTY_ORD_MASTER WHERE 1=1 {date_filter} {zip_filter}
"""

Summary_Party1 = f"""
    SELECT COUNT(1) AS COUNT_ORD, SUM(NET_AMOUNT) AS NET_AMOUNT,
           DATENAME(MONTH, DELIVERY_DATE) AS MONTH_NAME,
           MONTH(DELIVERY_DATE) AS MONTH_NUMBER, YEAR(DELIVERY_DATE) AS YEAR 
    FROM T_ECOMM_PARTY_ORD_MASTER
    WHERE 1=1 {date_filter} {zip_filter}
    GROUP BY DATENAME(MONTH, DELIVERY_DATE), MONTH(DELIVERY_DATE), YEAR(DELIVERY_DATE)
    ORDER BY YEAR DESC, MONTH_NUMBER DESC
"""

# 👉 Execute Queries
try:
    with pyodbc.connect(conn_str) as conn:
        upcoming_count = pd.read_sql_query(UPCOMING_PARTY_COUNT, conn).iloc[0, 0] or 0
        completed_count = pd.read_sql_query(COMPLETED_PARTY_COUNT, conn).iloc[0, 0] or 0
        pending_count = pd.read_sql_query(PENDING_PARTY_COUNT, conn).iloc[0, 0] or 0
        canceled_count = pd.read_sql_query(CANCELED_PARTY_COUNT, conn).iloc[0, 0] or 0
        
        PAYMENT_TYP_WISE = pd.read_sql_query(PAYMENT_TYP_WISE_QUERY, conn)
        DIFF_DISCOUNT_NETAMT_RESULT = pd.read_sql_query(DIFF_DISCOUNT_NETAMT, conn)
        Summary_Party1_data = pd.read_sql_query(Summary_Party1, conn)
except Exception as e:
    st.error(f"Database error: {e}")

# 👉 Handle Missing Data
if PAYMENT_TYP_WISE.empty:
    PAYMENT_TYP_WISE = pd.DataFrame({"PAYMENT_TYPE": ["No Data"], "PAYMENT_AMOUNT": [0]})

if DIFF_DISCOUNT_NETAMT_RESULT.empty:
    DIFF_DISCOUNT_NETAMT_RESULT = pd.DataFrame({"AMT_TYPE": ["No Data"], "AMT": [0]})

if Summary_Party1_data.empty:
    Summary_Party1_data = pd.DataFrame({"COUNT_ORD": [], "NET_AMOUNT": [], "MONTH_NAME": [], "MONTH_NUMBER": [], "YEAR": []})

# 👉 Total Net Amount for KPI
total_net_amount = DIFF_DISCOUNT_NETAMT_RESULT.loc[
    DIFF_DISCOUNT_NETAMT_RESULT['AMT_TYPE'] == 'NET AMOUNT', 'AMT'
].sum() or 0

# ✅ KPI Cards
st.header("📊 KPI Overview")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Upcoming Orders", upcoming_count)
col2.metric("Completed Orders", completed_count)
col3.metric("Pending Orders", pending_count)
col4.metric("Canceled Orders", canceled_count)
col5.metric("Total Net Amount",total_net_amount)

# ✅ Data for Visualization
df = pd.DataFrame({
    "Status": ["Upcoming", "Completed", "Pending", "Canceled"],
    "Count": [upcoming_count, completed_count, pending_count, canceled_count]
})

order_data = Summary_Party1_data.sort_values(by=["YEAR", "MONTH_NUMBER"])

# ✅ Bar Chart
bar_chart = px.bar(df, x="Status", y="Count", color="Status", title="Order Status Count")

# ✅ Line + Bar Chart
fig = px.bar(order_data, x="MONTH_NAME", y="COUNT_ORD", text="COUNT_ORD",
             labels={"COUNT_ORD": "Order Count", "MONTH_NAME": "Month"},
             title="Monthly Order Count & Net Amount")

fig.add_scatter(x=order_data["MONTH_NAME"], y=order_data["NET_AMOUNT"],
                mode='lines+markers', name='Net Amount')

fig.update_layout(
    yaxis_title="Order Count",
    xaxis_title="Month"
)

# 👉 Display Charts
st.plotly_chart(bar_chart, use_container_width=True)
st.plotly_chart(fig, use_container_width=True)

# ✅ Styling
st.markdown(
    """
    <style>
    .stApp { background-color: #1dc4b1; }
    .stMetric { color: #c48d1d; }
    </style>
    """,
    unsafe_allow_html=True
)
