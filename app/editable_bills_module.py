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
    st.markdown("""
    **Instructions:**
    - Select the date and hotel.
    - Edit only the quantity for each item in each kitchen.
    - Preview the bill below and download as PDF.
    - To save your changes, click 'Save Changes to Google Sheet'.
    """)
    today = datetime.now().date()
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input("Select Date", value=today, key="edit_bill_date")
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
            all_changes = []
            for kitchen in kitchens:
                st.subheader(f"Kitchen: {kitchen}")
                kitchen_df = hotel_df[hotel_df['KITCHEN NAME'] == kitchen].copy()
                # Only show essential columns for editing
                edit_df = kitchen_df[['PIVOT_VEGETABLE_NAME', 'UNITS', 'QUANTITY']].copy().reset_index(drop=True)
                edited_df = st.data_editor(
                    edit_df,
                    column_config={
                        "QUANTITY": st.column_config.NumberColumn("Quantity", min_value=0.0, required=True),
                    },
                    disabled=[col for col in edit_df.columns if col != "QUANTITY"],
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"edit_{kitchen}"
                )
                # Add required columns for preview and PDF
                edited_df['MAIN HOTEL NAME'] = selected_hotel
                edited_df['KITCHEN NAME'] = kitchen
                edited_df['DATE'] = selected_date
                # Find changed rows
                changed_rows = []
                for idx, row in edited_df.iterrows():
                    orig_qty = edit_df.iloc[idx]['QUANTITY']
                    new_qty = row['QUANTITY']
                    if orig_qty != new_qty:
                        changed_row = row.copy()
                        changed_row['KITCHEN NAME'] = kitchen
                        changed_row['MAIN HOTEL NAME'] = selected_hotel
                        changed_row['DATE'] = selected_date.strftime('%Y-%m-%d')
                        changed_rows.append(changed_row)
                all_changes.extend(changed_rows)
                # Show bill preview (essential columns only)
                st.markdown("**Bill Preview (after edit):**")
                preview = create_kitchen_bills_preview(edited_df, selected_date)
                if preview and selected_hotel in preview and kitchen in preview[selected_hotel]:
                    bill_data = preview[selected_hotel][kitchen]['data']
                    # Only show columns that exist
                    preview_cols = ['Vegetable Name', 'Telugu Name', 'Quantity', 'TOTAL']
                    available_cols = [col for col in preview_cols if col in bill_data.columns]
                    bill_data_display = bill_data[available_cols]
                    grand_total = preview[selected_hotel][kitchen]['grand_total']
                    st.dataframe(bill_data_display, use_container_width=True)
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
            # Save all changed rows to a new sheet 'change' in Google Sheets
            if all_changes:
                if st.button("Save Changes to Google Sheet", key="save_changes_gsheet"):
                    try:
                        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
                        SPREADSHEET_ID = st.secrets.general.id
                        credentials = service_account.Credentials.from_service_account_info(st.secrets["google_service_account"],scopes=SCOPES)
                        service = build('sheets', 'v4', credentials=credentials)
                        sheet = service.spreadsheets()
                        change_sheet = "change"
                        # Check if sheet exists
                        sheets_metadata = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
                        sheet_names = [s['properties']['title'] for s in sheets_metadata['sheets']]
                        if change_sheet not in sheet_names:
                            requests = [{
                                'addSheet': {
                                    'properties': {'title': change_sheet}
                                }
                            }]
                            body = {'requests': requests}
                            service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
                            # Add header row
                            header = list(all_changes[0].index)
                            service.spreadsheets().values().update(
                                spreadsheetId=SPREADSHEET_ID,
                                range=f"{change_sheet}!A1",
                                valueInputOption='RAW',
                                body={'values': [header]}
                            ).execute()
                        # Append changes
                        values = [list(row.values) for row in all_changes]
                        service.spreadsheets().values().append(
                            spreadsheetId=SPREADSHEET_ID,
                            range=f"{change_sheet}!A1",
                            valueInputOption='RAW',
                            insertDataOption='INSERT_ROWS',
                            body={'values': values}
                        ).execute()
                        st.success(f"Saved {len(all_changes)} changed rows to Google Sheet 'change'.")
                    except Exception as e:
                        st.error(f"Failed to save changes: {e}")
        else:
            st.info("No bills found for this hotel on the selected date.")
    else:
        st.info("No data found for the selected date.") 