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
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_date = st.date_input("Select Date", value=today)
    with col2:
        df = get_google_sheets_data()
        hotels = sorted(df['MAIN HOTEL NAME'].unique()) if not df.empty else []
        selected_hotel = st.selectbox("Select Hotel", hotels)
    with col3:
        kitchens = []
        if not df.empty and selected_hotel:
            kitchens = sorted(df[df['MAIN HOTEL NAME'] == selected_hotel]['KITCHEN NAME'].unique())
        selected_kitchen = st.selectbox("Select Kitchen", kitchens)
    filtered_df, _ = process_data_for_date(df, selected_date)
    if not filtered_df.empty:
        bills_df = filtered_df[(filtered_df['MAIN HOTEL NAME'] == selected_hotel) & (filtered_df['KITCHEN NAME'] == selected_kitchen)]
        if not bills_df.empty:
            edit_df = bills_df[['PIVOT_VEGETABLE_NAME', 'UNITS', 'QUANTITY']].copy().reset_index(drop=True)
            veg_options = sorted(bills_df['PIVOT_VEGETABLE_NAME'].unique())
            st.write("Edit the vegetable name and quantity below (directly in the table):")
            edited_df = st.data_editor(
                edit_df,
                column_config={
                    "PIVOT_VEGETABLE_NAME": st.column_config.SelectboxColumn(
                        "Vegetable Name", options=veg_options, required=True
                    ),
                    "QUANTITY": st.column_config.NumberColumn("Quantity", min_value=0.0, required=True),
                },
                num_rows="dynamic",
                use_container_width=True
            )
            if st.button("Save Changes", key="bills_save_edits"):
                changes = []
                for idx, row in edited_df.iterrows():
                    orig_name = bills_df.iloc[idx]['PIVOT_VEGETABLE_NAME']
                    orig_qty = bills_df.iloc[idx]['QUANTITY']
                    new_name = row['PIVOT_VEGETABLE_NAME']
                    new_qty = row['QUANTITY']
                    if orig_name != new_name or orig_qty != new_qty:
                        diff = new_qty - orig_qty
                        changes.append({
                            'DATE': selected_date.strftime('%Y-%m-%d'),
                            'HOTEL': selected_hotel,
                            'KITCHEN': selected_kitchen,
                            'VEGETABLE': new_name,
                            'UNITS': row['UNITS'],
                            'DIFF_QUANTITY': diff,
                            'OLD_QUANTITY': orig_qty,
                            'NEW_QUANTITY': new_qty
                        })
                if changes:
                    try:
                        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
                        SPREADSHEET_ID = st.secrets.general.id
                        credentials = service_account.Credentials.from_service_account_info(st.secrets["google_service_account"],scopes=SCOPES)
                        service = build('sheets', 'v4', credentials=credentials)
                        sheet = service.spreadsheets()
                        edits_sheet = f"Edits_{selected_date.strftime('%Y%m%d')}"
                        sheets_metadata = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
                        sheet_names = [s['properties']['title'] for s in sheets_metadata['sheets']]
                        if edits_sheet not in sheet_names:
                            requests = [{
                                'addSheet': {
                                    'properties': {'title': edits_sheet}
                                }
                            }]
                            body = {'requests': requests}
                            service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
                            header = list(changes[0].keys())
                            service.spreadsheets().values().update(
                                spreadsheetId=SPREADSHEET_ID,
                                range=f"{edits_sheet}!A1",
                                valueInputOption='RAW',
                                body={'values': [header]}
                            ).execute()
                        values = [list(c.values()) for c in changes]
                        service.spreadsheets().values().append(
                            spreadsheetId=SPREADSHEET_ID,
                            range=f"{edits_sheet}!A1",
                            valueInputOption='RAW',
                            insertDataOption='INSERT_ROWS',
                            body={'values': values}
                        ).execute()
                        st.success(f"Saved {len(changes)} changes to Google Sheets ({edits_sheet})")
                    except Exception as e:
                        st.error(f"Failed to save changes: {e}")
                else:
                    st.info("No changes to save.")
            st.subheader("Edited Table (Current Session)")
            st.dataframe(edited_df, use_container_width=True)
            # Download each hotel bill as CSV
            st.subheader("Download Hotel Bill as CSV")
            csv = edited_df.to_csv(index=False)
            st.download_button(
                label=f"Download {selected_hotel} Bill as CSV",
                data=csv,
                file_name=f"{selected_hotel}_bill_{selected_date.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            # Download as PDF (optional)
            if st.button(f"Download {selected_hotel} Bill as PDF"):
                pdf_buffer = create_kitchen_bills_pdf(bills_df, selected_date)
                if pdf_buffer:
                    st.download_button(
                        label=f"Download {selected_hotel} Bill as PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"{selected_hotel}_bill_{selected_date.strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.warning("PDF generation failed.")
        else:
            st.info("No bills found for this hotel and kitchen on the selected date.")
    else:
        st.info("No data found for the selected date.") 