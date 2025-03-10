import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px

# Database connection details
server = "172.18.1.25"
database = "JBB_POS_CL"
username = "dev_user"
password = "newdream@1234"

conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"

# Streamlit Sidebar
st.sidebar.header("Filter Data")
from_date = st.sidebar.date_input("From Date")
to_date = st.sidebar.date_input("To Date")
st.markdown(
    """
    <style>
    body {
        background-color: #27CCC4;
    }
    .stApp {
        background-color: #27CCC4;
    }
    .css-1d391kg {
        background-color: #1F9E9E !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
# Connecting to Database
try:
    with pyodbc.connect(conn_str) as conn:
        
        # Fetch unique Zip Codes for dropdown filter
        ZIP_CODE_QUERY = "SELECT DISTINCT ZIP_CODE FROM T_ECOMM_PARTY_ORD_MASTER"
        zip_codes = pd.read_sql_query(ZIP_CODE_QUERY, conn)
        zip_code_list = ["All"] + zip_codes["ZIP_CODE"].dropna().astype(str).tolist()
        
        selected_zip = st.sidebar.selectbox("Select Zip Code", zip_code_list)

        # Adjusting SQL Queries with Filters
        date_filter = f"AND DELIVERY_DATE BETWEEN '{from_date}' AND '{to_date}'"
        zip_filter = f"AND ZIP_CODE = '{selected_zip}'" if selected_zip != "All" else ""

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

        # Executing Queries
        upcoming_count = pd.read_sql_query(UPCOMING_PARTY_COUNT, conn).iloc[0, 0]
        completed_count = pd.read_sql_query(COMPLETED_PARTY_COUNT, conn).iloc[0, 0]
        pending_count = pd.read_sql_query(PENDING_PARTY_COUNT, conn).iloc[0, 0]
        canceled_count = pd.read_sql_query(CANCELED_PARTY_COUNT, conn).iloc[0, 0]

        PAYMENT_TYP_WISE = pd.read_sql_query(PAYMENT_TYP_WISE_QUERY, conn)
        DIFF_DISCOUNT_NETAMT_RESULT = pd.read_sql_query(DIFF_DISCOUNT_NETAMT, conn)
        Summary_Party1_data = pd.read_sql_query(Summary_Party1, conn)

        # Handling Empty DataFrames
        if PAYMENT_TYP_WISE.empty:
            PAYMENT_TYP_WISE = pd.DataFrame({"PAYMENT_TYPE": ["No Data"], "PAYMENT_AMOUNT": [0]})

        if DIFF_DISCOUNT_NETAMT_RESULT.empty:
            DIFF_DISCOUNT_NETAMT_RESULT = pd.DataFrame({"AMT_TYPE": ["No Data"], "AMT": [0]})

        if Summary_Party1_data.empty:
            Summary_Party1_data = pd.DataFrame({"COUNT_ORD": [], "NET_AMOUNT": [], "MONTH_NAME": [], "MONTH_NUMBER": [], "YEAR": []})

        # Data for Visualization
        df = pd.DataFrame({
            "Status": ["Upcoming", "Completed", "Pending", "Canceled"],
            "Count": [upcoming_count, completed_count, pending_count, canceled_count]
        })

        order_data = Summary_Party1_data.sort_values(by=["YEAR", "MONTH_NUMBER"])

        # Charts
        pie_chart = px.pie(df, values="Count",names="Status", hole=0.4, title="Order Status Distribution" , width=200 , height=250)
        pie_chart2 = px.pie(PAYMENT_TYP_WISE, values="PAYMENT_AMOUNT" ,names="PAYMENT_TYPE", hole=0.4, title="Payment Type Distribution" , width=200 , height=250)
        pie_chart3 = px.pie(DIFF_DISCOUNT_NETAMT_RESULT, values="AMT" , names="AMT_TYPE", hole=0.4, title="Discount and Net Amount" , width=200 , height=250)

        bar_chart = px.bar(df, x="Status", y="Count", color="Status", title="Order Status Count")

        fig = px.bar(order_data, x="MONTH_NAME", y="COUNT_ORD", 
                     text="COUNT_ORD", opacity=0.7, 
                     labels={"COUNT_ORD": "Order Count", "MONTH_NAME": "Month"},
                     title="Monthly Order Count & Net Amount")

        fig.add_scatter(x=order_data["MONTH_NAME"], y=order_data["NET_AMOUNT"],
                        mode='lines+markers', name='Net Amount',
                        yaxis='y2')

        fig.update_layout(
            yaxis=dict(title='Order Count', side='left'),
            yaxis2=dict(title='Net Amount (₹)', overlaying='y', side='right'),
            xaxis=dict(title='Month'),
            title_x=0.5
        )

except Exception as e:
    st.error(f"Error: {e}")

# Streamlit Layout
st.title(" :bar_chart: Party Order Status Dashboard")

col1, col2, col3 = st.columns(3)
with col1:
    st.plotly_chart(pie_chart3, use_container_width=True)
with col2:
    st.plotly_chart(pie_chart, use_container_width=True)
with col3:
    st.plotly_chart(pie_chart2, use_container_width=True)

st.plotly_chart(fig, use_container_width=True)
st.plotly_chart(bar_chart, use_container_width=True)
