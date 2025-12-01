import streamlit as st
import pandas as pd
import datetime as dt
from io import BytesIO
import hashlib

# ----------------------
# Page background color
# ----------------------
st.markdown(
    """
    <style>
    html, body, [class*="css"]  {
        background-color: #f0f8ff !important;  /* light blue, change as needed */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------
# Streamlit page config
# ----------------------
st.set_page_config(
    page_title="Limpopo Province Pharmaceutical Desktop",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ----------------------
# Password handling
# ----------------------
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


USERS = {
    "admin": "21232f297a57a5a743894a0e4a801fc3",
    "pharma": "6cb75f652a9b52798eb6cf2201057c73"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# ----------------------
# Login screen with logo
# ----------------------
def login_screen():
    try:
        st.image("logo.png", width=550)  # Logo at top
    except:
        st.warning("⚠️ Logo not found. Place 'logo.png' in the same folder.")

    st.markdown("""
        <div style='text-align:center; padding: 10px;'>
            <h1 style='color:#0047AB;'>Rx💊 Pharmaceutical Products Dashboard</h1>
            <h3 style='margin-top:-10px; color:#888;'>Secure Login</h3>
            <hr style='margin-top:15px;'>
        </div>
    """, unsafe_allow_html=True)

    login_col = st.columns([1, 2, 1])[1]
    with login_col:
        username = st.text_input("👤 Username")
        password = st.text_input("🔒 Password", type="password")
        if st.button("Login", use_container_width=True):
            if username in USERS and USERS[username] == hash_password(password):
                st.session_state.logged_in = True
            else:
                st.error("❌ Invalid username or password")


if not st.session_state.logged_in:
    login_screen()
    st.stop()

# ----------------------
# Dashboard header
# ----------------------
st.markdown("""
    <div style='background-color:#0047AB;padding:15px;border-radius:10px'>
        <h1 style='color:white;text-align:center;'>Rx💊 Limpopo Province Pharmaceutical Stock Dashboard</h1>
    </div>
""", unsafe_allow_html=True)

st.write("Upload your Excel file to start analyzing pharmaceutical stock levels across facilities.")
uploaded_file = st.file_uploader("📂 Upload Excel File", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

    # ----------------------
    # Identify columns
    # ----------------------
    # Prioritize 'Facility Name' for search
    facility_col = None
    for c in df.columns:
        if c.lower() == "facility name":
            facility_col = c
            break
    if not facility_col:
        for c in df.columns:
            if c.lower() in ["facility", "hospital", "clinic"]:
                facility_col = c
                break

    desc_col = next(
        (c for c in df.columns if c.lower() in ["description", "item description", "medicine", "nsn description"]),
        None)
    stock_col = next((c for c in df.columns if c.lower() in ["on hand", "stock", "stock_on_hand", "qty", "quantity"]),
                     None)
    expiry_col = next((c for c in df.columns if c.lower() in ["expiry", "expiry date", "expiration", "exp"]), None)

    missing = [name for name, col in
               zip(["Facility", "Description", "Stock", "Expiry"], [facility_col, desc_col, stock_col, expiry_col]) if
               col is None]
    if missing:
        st.error("❌ Missing required columns: " + ", ".join(missing))
        st.stop()

    df[stock_col] = pd.to_numeric(df[stock_col], errors="coerce").fillna(0)
    df[expiry_col] = pd.to_datetime(df[expiry_col], errors="coerce")
    df["Days_Left"] = (df[expiry_col] - dt.datetime.today()).dt.days


    # ----------------------
    # Expiry status
    # ----------------------
    def expiry_status(days):
        if pd.isna(days): return "No Expiry"
        if days < 0: return "Expired"
        if days <= 30: return "⚠️ Expiring <30 days"
        if days <= 90: return "🟡 Expiring <90 days"
        return "🟢 OK"


    df["Expiry_Status"] = df["Days_Left"].apply(expiry_status)

    # ----------------------
    # Filters
    # ----------------------
    st.subheader("🔍 Filters")
    col1, col2 = st.columns([2, 3])
    with col1:
        search_facility = st.text_input("🏥 Search Facility")
    with col2:
        search_text = st.text_input("🔎 Search Item")

    df_filtered = df.copy()
    if search_facility.strip():
        df_filtered = df_filtered[df_filtered[facility_col].str.contains(search_facility, case=False, na=False)]
    if search_text.strip():
        df_filtered = df_filtered[df_filtered[desc_col].str.contains(search_text, case=False, na=False)]

    # ----------------------
    # Stock Summary
    # ----------------------
    st.subheader("📊 Stock Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Expired Items", df_filtered[df_filtered["Expiry_Status"] == "Expired"].shape[0])
    c2.metric("Expiring <30 Days", df_filtered[df_filtered["Expiry_Status"] == "⚠️ Expiring <30 days"].shape[0])
    c3.metric("Expiring <90 Days", df_filtered[df_filtered["Expiry_Status"] == "🟡 Expiring <90 days"].shape[0])
    c4.metric("Total Items", df_filtered.shape[0])

    # ----------------------
    # Items expiring soon
    # ----------------------
    st.subheader("⚠️ Items Expiring Soon")
    df_expiring = df_filtered[df_filtered["Days_Left"] <= 90]


    def color_row(r):
        if r["Expiry_Status"] == "Expired":
            return ["background-color:#ff9999"] * len(r)
        elif r["Expiry_Status"] == "⚠️ Expiring <30 days":
            return ["background-color:#ffe16b"] * len(r)
        elif r["Expiry_Status"] == "🟡 Expiring <90 days":
            return ["background-color:#fff4b3"] * len(r)
        else:
            return [""] * len(r)


    if not df_expiring.empty:
        st.dataframe(df_expiring.style.apply(color_row, axis=1), height=400, use_container_width=True)
    else:
        st.info("✅ No items expiring within 90 days.")

    st.dataframe(df_filtered, height=500, use_container_width=True)


    # ----------------------
    # Download button
    # ----------------------
    @st.cache_data
    def to_excel(data):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            data.to_excel(writer, index=False, sheet_name="Filtered")
        return output.getvalue()


    st.download_button(
        label="💾 Download Excel",
        data=to_excel(df_filtered),
        file_name="filtered_stock.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

else:
    st.info("⬆️ Upload an Excel file to begin.")

# ----------------------
# Cleanup padding
# ----------------------
st.markdown("""
    <style>
    .css-18e3th9{padding-top:0rem;}
    .css-1d391kg{padding-left:0rem;padding-right:0rem;}
    </style>
""", unsafe_allow_html=True)
