import streamlit as st
import pandas as pd
from utils.sheets import get_google_sheets_data
from utils.data_processing import process_data_for_date
from googleapiclient.discovery import build
from google.oauth2 import service_account
from reports.bills_reports import create_kitchen_bills_pdf, create_kitchen_bills_preview
from io import BytesIO
from datetime import datetime

def show_editable_bills_section():
    st.header("📝 Edit Bill (Quantity Only)")
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
                kitchen_df = hotel_df[hotel_df['KITCHEN NAME'] == kitchen].copy()
                # Only QUANTITY is editable
                edited_df = st.data_editor(
                    kitchen_df,
                    column_config={
                        "QUANTITY": st.column_config.NumberColumn("Quantity", min_value=0.0, required=True),
                    },
                    disabled=[col for col in kitchen_df.columns if col != "QUANTITY"],
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"edit_{kitchen}"
                )
                # Show bill in the same format as Bills section
                st.markdown("**Bill Preview (after edit):**")
                # Use the same preview as Bills section
                preview = create_kitchen_bills_preview(edited_df, selected_date)
                if preview and selected_hotel in preview and kitchen in preview[selected_hotel]:
                    bill_data = preview[selected_hotel][kitchen]['data']
                    grand_total = preview[selected_hotel][kitchen]['grand_total']
                    st.dataframe(bill_data, use_container_width=True)
                    st.markdown(f"**Grand Total Amount: {grand_total}**")
                    # Download as PDF
                    if st.button(f"Download {kitchen} Bill as PDF", key=f"pdf_{kitchen}"):
                        pdf_buffer = create_kitchen_bills_pdf(edited_df, selected_date)
                        if pdf_buffer:
                            st.download_button(
                                label=f"Download {kitchen} Bill as PDF",
                                data=pdf_buffer.getvalue(),
                                file_name=f"{selected_hotel}_{kitchen}_bill_{selected_date.strftime('%Y%m%d')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        else:
                            st.warning("PDF generation failed.")
                else:
                    st.info("No bill data available after edit.")
                all_kitchen_edits.append(edited_df)
        else:
            st.info("No bills found for this hotel on the selected date.")
    else:
        st.info("No data found for the selected date.") 