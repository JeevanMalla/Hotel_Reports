import streamlit as st
import pandas as pd
from utils.sheets import get_google_sheets_data
from utils.data_processing import process_data_for_date
from googleapiclient.discovery import build
from google.oauth2 import service_account
from reports.bills_reports import create_kitchen_bills_pdf
from io import BytesIO
from datetime import datetime

def show_editable_bills_section():
    st.header("📝 Editable Bills Section")
    today = datetime.now().date()
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input("Select Date", value=today)
    with col2:
        df = get_google_sheets_data()
        hotels = sorted(df['MAIN HOTEL NAME'].unique()) if not df.empty else []
        selected_hotel = st.selectbox("Select Hotel", hotels)
    filtered_df, _ = process_data_for_date(df, selected_date)
    if not filtered_df.empty:
        hotel_df = filtered_df[filtered_df['MAIN HOTEL NAME'] == selected_hotel]
        if not hotel_df.empty:
            kitchens = sorted(hotel_df['KITCHEN NAME'].unique())
            all_kitchen_edits = []
            for kitchen in kitchens:
                st.subheader(f"Kitchen: {kitchen}")
                kitchen_df = hotel_df[hotel_df['KITCHEN NAME'] == kitchen]
                edit_df = kitchen_df[['PIVOT_VEGETABLE_NAME', 'UNITS', 'QUANTITY']].copy().reset_index(drop=True)
                veg_options = sorted(kitchen_df['PIVOT_VEGETABLE_NAME'].unique())
                edited_df = st.data_editor(
                    edit_df,
                    column_config={
                        "PIVOT_VEGETABLE_NAME": st.column_config.SelectboxColumn(
                            "Vegetable Name", options=veg_options, required=True
                        ),
                        "QUANTITY": st.column_config.NumberColumn("Quantity", min_value=0.0, required=True),
                    },
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"edit_{kitchen}"
                )
                # Calculate and display total for this kitchen
                total_qty = edited_df['QUANTITY'].sum()
                st.markdown(f"**Total Quantity for {kitchen}: {total_qty:,.2f}**")
                edited_df['KITCHEN NAME'] = kitchen
                all_kitchen_edits.append(edited_df)
            # Combine all kitchens for download
            if all_kitchen_edits:
                combined_df = pd.concat(all_kitchen_edits, ignore_index=True)
                st.subheader("Download All Kitchen Bills for Hotel as CSV")
                csv = combined_df.to_csv(index=False)
                st.download_button(
                    label=f"Download All {selected_hotel} Kitchen Bills as CSV",
                    data=csv,
                    file_name=f"{selected_hotel}_all_kitchen_bills_{selected_date.strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.info("No bills found for this hotel on the selected date.")
    else:
        st.info("No data found for the selected date.") 