import pandas as pd

# Define the structure
columns = [
    'Date_Acquired', 'Card_Name', 'Set_Name', 'Card_Number', 
    'Condition', 'Buy_Price', 'Platform', 'Status'
]

# Initialize an empty DataFrame
df = pd.DataFrame(columns=columns)

# Convert columns to correct types for analytics
df['Date_Acquired'] = pd.to_datetime(df['Date_Acquired'])
df['Buy_Price'] = df['Buy_Price'].astype(float)

print("Data Frame Initialized and Ready for Analysis!")

from pokemontcgsdk.card import Card

# 1. Load your friend's inventory
df = pd.read_excel('C:/LuckyPaws/pokemon_inventory.xlsx')

def get_market_price(name, number):
    try:
        # Search for the card by name and number to be precise
        cards = Card.where(q=f'name:"{name}" number:"{number}"')
        
        if cards:
            # We take the first match and look for TCGPlayer 'Market' price
            tcg_data = cards[0].tcgplayer
            if tcg_data and tcg_data.prices:
                # Most cards use the 'holofoil' or 'normal' price key
                # This pulls the 'market' value specifically
                price_obj = tcg_data.prices.holofoil or tcg_data.prices.normal
                return price_obj.market
        return None
    except Exception as e:
        print(f"Error fetching {name}: {e}")
        return None

# 2. Apply the function to the DataFrame
print("Fetching market prices... this may take a moment.")
df['Current_Market_Price'] = df.apply(lambda x: get_market_price(x['Card_Name'], x['Card_Number']), axis=1)

# 3. Calculate Unrealized Profit/Loss
df['Estimated_Profit'] = df['Current_Market_Price'] - df['Buy_Price']

# 4. Save the "Live" report
df.to_excel('market_value_report.xlsx', index=False)
print("Report generated!")

# Analytics Logic: Adjusted Net Value
# Subtract 13% for eBay/TCGPlayer fees and $5 for shipping
df['Net_If_Sold'] = (df['Current_Market_Price'] * 0.87) - 5

# Condition Multiplier
# (e.g., if it's Lightly Played (LP), it's only worth 80% of Market)
condition_weights = {'NM': 1.0, 'LP': 0.8, 'MP': 0.5}
print(df.columns)
df['Condition_Adjusted_Price'] = df['Current_Market_Price'] * df['Condition '].map(condition_weights)

import streamlit as st
import plotly.express as px
import os

EXCEL_FILE = 'pokemon_inventory.xlsx'

# Initialize file if missing
if not os.path.exists(EXCEL_FILE):
    df = pd.DataFrame(columns=['Date', 'Card_Name', 'Set_Name', 'Condition', 'Buy_Price', 'Market_Value'])
    df.to_excel(EXCEL_FILE, index=False)

st.set_page_config(page_title="Pokemon Analytics", layout="wide")
st.title("📊 Reseller Strategy Dashboard")

# --- DATA LOADING ---
df = pd.read_excel(EXCEL_FILE)
df['Date'] = pd.to_datetime(df['Date'])

# --- SIDEBAR: DATA ENTRY ---
st.sidebar.header("Add New Stock")
with st.sidebar.form("entry_form", clear_on_submit=True):
    date = st.date_input("Purchase Date")
    name = st.text_input("Card Name")
    set_n = st.text_input("Set")
    cond = st.selectbox("Condition", ["NM", "LP", "MP", "PSA 10", "PSA 9"])
    buy = st.number_input("Buy Price ($)", min_value=0.0)
    mkt = st.number_input("Current Market Value ($)", min_value=0.0) # Manual entry for now
    
    submit = st.form_submit_button("Add to Inventory")
    if submit:
        new_row = pd.DataFrame([[date, name, set_n, cond, buy, mkt]], columns=df.columns)
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(EXCEL_FILE, index=False)
        st.sidebar.success("Added!")

# --- DASHBOARD SECTION ---
if not df.empty:
    # 1. Key Metrics
    total_inv = df['Buy_Price'].sum()
    est_value = df['Market_Value'].sum()
    roi = ((est_value - total_inv) / total_inv) * 100 if total_inv > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Capital Invested", f"${total_inv:,.2f}")
    col2.metric("Est. Portfolio Value", f"${est_value:,.2f}")
    col3.metric("Projected ROI", f"{roi:.1f}%", delta=f"{roi:.1f}%")

    st.divider()

    # 2. Visuals
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.write("### Value by Set")
        fig_set = px.pie(df, values='Market_Value', names='Set_Name', hole=0.4)
        st.plotly_chart(fig_set, use_container_width=True)

    with chart_col2:
        st.write("### Inventory Growth")
        # Grouping by date to see cumulative investment over time
        growth_df = df.groupby('Date')['Buy_Price'].sum().cumsum().reset_index()
        fig_growth = px.area(growth_df, x='Date', y='Buy_Price', title="Cumulative Spend")
        st.plotly_chart(fig_growth, use_container_width=True)

    # 3. The Raw Data Table
    st.write("### Inventory Details")
    st.dataframe(df, use_container_width=True)
else:
    st.info("No data found. Use the sidebar to add your first card!")

