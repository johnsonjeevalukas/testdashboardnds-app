import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px
from datetime import datetime
from streamlit_navigation_bar import st_navbar




# 👉 Database connection details
server = "172.18.1.25"
# database = "JBB_POS_CL"
# database = "JBB_POS_CL"
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

selected_zip = st.sidebar.multiselect("Select Zip Code", zip_code_list)
if selected_zip:  # Check if the list is not empty
    zip_filter = f"AND ZIP_CODE IN ({', '.join([f"'{zip}'" for zip in selected_zip])})"
else:
    zip_filter = ""

def test(x):
    order_by = "BOX DESC" if x == "Box" else "GROSS_SALES DESC"
    return f"""
     SELECT 
        ODTL.ITEM_ID,
        ISNULL(ISNULL(IM.NAME,OTHERS.NAME),'OTHERS') AS NAME,
        SUM(ISNULL(ISNULL(ISNULL(ODTL.BOX,OLP.BOX),ODTL.TRAY_QTY),0)) AS BOX,
        TRY_CONVERT(NUMERIC(8,2),SUM(ODTL.PRICE)) AS GROSS_SALES
    FROM T_ECOMM_PARTY_ORD_DETAIL ODTL
    LEFT JOIN T_ECOMM_PARTY_ORDER_LOOKUP OLP ON OLP.ITEM_PARTY_ID = ODTL.ITEM_PARTY_ID
    LEFT JOIN T_ECOMM_ITEM_MASTER IM ON IM.Clover_ID = ODTL.ITEM_ID
    LEFT JOIN (SELECT DISTINCT ITEM_ID, NAME FROM T_ECOMM_PARTY_ORD_DETAIL) OTHERS ON OTHERS.ITEM_ID=ODTL.ITEM_ID
    WHERE ODTL.TRAY_ORDER_ID IN (
        SELECT TRAY_ORDER_ID FROM T_ECOMM_PARTY_ORD_MASTER 
        WHERE STATUS != 'CANCELED' {date_filter} {zip_filter}
    )
    GROUP BY ODTL.ITEM_ID, IM.NAME, OTHERS.NAME
    ORDER BY {order_by}
    """
    
NET_CMOUNT_CMTD="""SELECT TRY_CAST(SUM(TRY_CONVERT(NUMERIC(8,2),NET_AMOUNT))AS VARCHAR) AS NET_AMOUNT_COMMITED FROM T_ECOMM_PARTY_ORD_MASTER WHERE STATUS IN ('OPEN','COMPLETED')"""
PYMNT_RCVD="""SELECT TRY_CAST(SUM(TRY_CONVERT(NUMERIC(8,2),PAYMENT_RECEIVED))AS VARCHAR) AS PYMNT_AMOUNT_COMMITED FROM T_ECOMM_PARTY_ORD_MASTER WHERE STATUS IN ('OPEN','COMPLETED')"""
PARTY_COUNT="""SELECT COUNT(1) AS PARTY_COUNT FROM T_ECOMM_PARTY_ORD_MASTER WHERE STATUS IN ('OPEN','COMPLETED')"""


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
        Part_details_1 = pd.read_sql_query(test("BOX DESC"), conn)
        NET_CMOUNT_CMTD = pd.read_sql_query(NET_CMOUNT_CMTD, conn)
        PYMNT_RCVD = pd.read_sql_query(PYMNT_RCVD, conn)
        PARTY_COUNT = pd.read_sql_query(PARTY_COUNT, conn)
        Summary_Party1_data = pd.read_sql_query(Summary_Party1, conn)
        party_details = Part_details_1
        if not party_details.empty:
            party_details = party_details.head(10)
        if Part_details_1.empty:
            Party_details_1 = pd.DataFrame(columns=["ITEM_ID", "NAME", "BOX", "GROSS_SALES"])
        if NET_CMOUNT_CMTD.empty:
            NET_CMOUNT_CMTD = pd.DataFrame(columns=["NET_AMOUNT_COMMITED"])
        if PYMNT_RCVD.empty:
            PYMNT_RCVD = pd.DataFrame(columns=["PYMNT_AMOUNT_COMMITED"])
        if PARTY_COUNT.empty:
            PARTY_COUNT = pd.DataFrame(columns=["PARTY_COUNT"])
        if Summary_Party1_data.empty:
            Summary_Party1_data = pd.DataFrame({"COUNT_ORD": [], "NET_AMOUNT": [], "MONTH_NAME": [], "MONTH_NUMBER": [], "YEAR": []})
except Exception as e:
    st.error(f"Database error: {e}")

order_data = Summary_Party1_data.sort_values(by=["YEAR", "MONTH_NUMBER"])


fig = px.bar(order_data, x="MONTH_NAME", y="COUNT_ORD", text="COUNT_ORD",
             labels={"COUNT_ORD": "Order Count", "MONTH_NAME": "Month"},
             title="Monthly Order Count & Net Amount")

fig.add_scatter(x=order_data["MONTH_NAME"], y=order_data["NET_AMOUNT"],
                mode='lines+markers', name='Net Amount')

fig.update_layout(
    yaxis_title="Order Count",
    xaxis_title="Month"
)
# ✅ KPI Cards
st.header("📊 Party Sales Trend")

# ✅ Use a custom div for column gap
st.markdown(
    """
    <div class="custom-metric-container">
        <div class="metric-item">
            <p>Total Parties</p>
            <h3>{}</h3>
        </div>
        <div class="metric-item">
            <p>NetAmt Commited</p>
            <h3>{}</h3>
        </div>
        <div class="metric-item">
            <p>NetAmt Received</p>
            <h3>{}</h3>
        </div>
        <div class="metric-item">
            <p>Gross Sale</p>
            <h3>{}</h3>
        </div>
    </div>
    """.format(
        PARTY_COUNT["PARTY_COUNT"].sum() if not PARTY_COUNT.empty else 0,
        NET_CMOUNT_CMTD["NET_AMOUNT_COMMITED"].sum() if not NET_CMOUNT_CMTD.empty else 0,
        PYMNT_RCVD["PYMNT_AMOUNT_COMMITED"].sum() if not PYMNT_RCVD.empty else 0,
        Part_details_1["GROSS_SALES"].sum().round(2)  if not Part_details_1.empty else 0,
    ),
    unsafe_allow_html=True
)
st.plotly_chart(fig, use_container_width=True)


st.markdown("""<div class='TOP10'>🏆 Top 10 Highly Sold </div>""", unsafe_allow_html=True)
sort_option = st.selectbox("Sort By:", options=["Box", "Gross Sales"], index=0)
TOP=st.number_input(label="Enter Top Count" ,placeholder="10" , value=10)
party_details = pd.read_sql_query(test(sort_option), conn)
if not party_details.empty:
    
    st.dataframe(party_details.head(TOP), use_container_width=True)
else:
    st.write("No data available.")
# ✅ CSS Styling
st.markdown(
    """
    <style>
    .stApp { 
        background-color: #1dc4b1; 
    }
    .custom-metric-container {
        display: flex;
        gap: 30px; /* Increase gap between columns */
        justify-content: center;
        margin-bottom: 20px;
    }
    .metric-item {
        background-color: white;
        color: #c48d1d;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        text-align: center;
        width: 180px;
    }
    .TOP10 {
        background-color: white;
        color: #c48d1d;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 20px; /* Add space below title */
    }
    .stDataFrame {
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        color: #333;
        font-size: 14px;
        margin-bottom: 60px; /* Space below table */
    }
    </style>
    
    </style>
    """,
    unsafe_allow_html=True
)
