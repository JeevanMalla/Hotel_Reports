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
                # Ensure required columns for preview/PDF
                for col in ['PIVOT_VEGETABLE_NAME', 'UNITS', 'TELUGU NAME']:
                    if col not in edited_df.columns:
                        edited_df[col] = ''
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
                # Bill Preview (match main bill module logic)
                st.markdown("**Bill Preview (after edit):**")
                # Group by vegetable/unit, sum quantities, and show columns as in main bill
                grouped = (
                    edited_df.groupby(['PIVOT_VEGETABLE_NAME', 'UNITS'], dropna=False)
                    .agg({'QUANTITY': 'sum'})
                    .reset_index()
                )
                # If PRICE exists, use it; else, fill with blank
                if 'PRICE' in kitchen_df.columns:
                    price_map = kitchen_df.set_index(['PIVOT_VEGETABLE_NAME', 'UNITS'])['PRICE'].to_dict()
                    grouped['PRICE'] = grouped.apply(lambda row: price_map.get((row['PIVOT_VEGETABLE_NAME'], row['UNITS']), ''), axis=1)
                else:
                    grouped['PRICE'] = ''
                # Calculate TOTAL if price is available
                def calc_total(row):
                    try:
                        return f"{float(row['PRICE']) * float(row['QUANTITY']):.2f}" if row['PRICE'] and str(row['PRICE']).strip() else ''
                    except:
                        return ''
                grouped['TOTAL'] = grouped.apply(calc_total, axis=1)
                # Format columns for display
                grouped['Quantity'] = grouped['QUANTITY'].astype(str) + ' ' + grouped['UNITS'].astype(str)
                display_cols = ['PIVOT_VEGETABLE_NAME', 'Quantity', 'PRICE', 'TOTAL']
                display_df = grouped[display_cols].rename(columns={
                    'PIVOT_VEGETABLE_NAME': 'Vegetable Name'
                })
                st.dataframe(display_df, use_container_width=True)
                # Show summary
                total_items = len(display_df)
                grand_total = 0
                for t in display_df['TOTAL']:
                    try:
                        if t and str(t).strip():
                            grand_total += float(t)
                    except:
                        pass
                st.markdown(f"**Total Items: {total_items} | Grand Total: {grand_total:.2f}**")
                # Prepare DataFrame for PDF (match main bill module)
                pdf_df = grouped.copy()
                pdf_df['MAIN HOTEL NAME'] = selected_hotel
                pdf_df['KITCHEN NAME'] = kitchen
                pdf_df['DATE'] = selected_date
                pdf_df['PIVOT_VEGETABLE_NAME'] = grouped['PIVOT_VEGETABLE_NAME']
                pdf_df['UNITS'] = grouped['UNITS']
                # Use TELUGU NAME from kitchen_df if available
                if 'TELUGU NAME' in kitchen_df.columns:
                    telugu_map = kitchen_df.set_index(['PIVOT_VEGETABLE_NAME', 'UNITS'])['TELUGU NAME'].to_dict()
                    pdf_df['TELUGU NAME'] = grouped.apply(lambda row: telugu_map.get((row['PIVOT_VEGETABLE_NAME'], row['UNITS']), ''), axis=1)
                else:
                    pdf_df['TELUGU NAME'] = ''
                pdf_df['QUANTITY'] = grouped['QUANTITY']
                pdf_df['PRICE'] = grouped['PRICE']
                # Reorder columns to match main bill module
                pdf_df = pdf_df[['MAIN HOTEL NAME', 'KITCHEN NAME', 'DATE', 'PIVOT_VEGETABLE_NAME', 'UNITS', 'TELUGU NAME', 'QUANTITY', 'PRICE']]
                # Download as PDF (trigger immediately)
                pdf_buffer = create_kitchen_bills_pdf(pdf_df, selected_date)
                st.download_button(
                    label=f"Download {kitchen} Bill as PDF",
                    data=pdf_buffer.getvalue() if pdf_buffer else b'',
                    file_name=f"{selected_hotel}_{kitchen}_bill_{selected_date.strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    disabled=pdf_buffer is None
                )
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
                        # For each changed row, find the original row in the main sheet and add row number and changed quantity
                        main_df = get_google_sheets_data()
                        main_df = main_df.reset_index().rename(columns={'index': 'ROW_NUMBER'})
                        save_rows = []
                        for changed in all_changes:
                            # Robust match: normalize all compared columns
                            def norm(val):
                                if pd.isnull(val):
                                    return ''
                                if isinstance(val, (int, float)):
                                    return str(val)
                                return str(val).strip().lower()
                            def norm_date(val):
                                try:
                                    return pd.to_datetime(val).strftime('%Y-%m-%d')
                                except:
                                    return str(val)
                            main_df['__MATCH_HOTEL'] = main_df['MAIN HOTEL NAME'].apply(norm)
                            main_df['__MATCH_KITCHEN'] = main_df['KITCHEN NAME'].apply(norm)
                            main_df['__MATCH_DATE'] = main_df['DATE'].apply(norm_date)
                            main_df['__MATCH_VEG'] = main_df['PIVOT_VEGETABLE_NAME'].apply(norm)
                            main_df['__MATCH_UNITS'] = main_df['UNITS'].apply(norm)
                            ch_hotel = norm(changed['MAIN HOTEL NAME'])
                            ch_kitchen = norm(changed['KITCHEN NAME'])
                            ch_date = norm_date(changed['DATE'])
                            ch_veg = norm(changed['PIVOT_VEGETABLE_NAME'])
                            ch_units = norm(changed['UNITS'])
                            match = main_df[
                                (main_df['__MATCH_HOTEL'] == ch_hotel) &
                                (main_df['__MATCH_KITCHEN'] == ch_kitchen) &
                                (main_df['__MATCH_DATE'] == ch_date) &
                                (main_df['__MATCH_VEG'] == ch_veg) &
                                (main_df['__MATCH_UNITS'] == ch_units)
                            ]
                            if not match.empty:
                                orig_row = match.iloc[0].to_dict()
                                orig_row['Changed Quantity'] = changed['QUANTITY']
                                save_rows.append(orig_row)
                        # Remove temp columns
                        for col in ['__MATCH_HOTEL', '__MATCH_KITCHEN', '__MATCH_DATE', '__MATCH_VEG', '__MATCH_UNITS']:
                            if col in main_df.columns:
                                main_df.drop(columns=[col], inplace=True)
                        if save_rows:
                            # Add header if new sheet
                            result = sheet.values().get(
                                spreadsheetId=SPREADSHEET_ID,
                                range=f"{change_sheet}!A1"
                            ).execute()
                            existing_values = result.get('values', [])
                            if not existing_values:
                                header = list(save_rows[0].keys())
                                sheet.values().update(
                                    spreadsheetId=SPREADSHEET_ID,
                                    range=f"{change_sheet}!A1",
                                    valueInputOption='RAW',
                                    body={'values': [header]}
                                ).execute()
                            # Append changes
                            values = [list(row.values()) for row in save_rows]
                            sheet.values().append(
                                spreadsheetId=SPREADSHEET_ID,
                                range=f"{change_sheet}!A1",
                                valueInputOption='RAW',
                                insertDataOption='INSERT_ROWS',
                                body={'values': values}
                            ).execute()
                            st.success(f"Saved {len(save_rows)} changed rows to Google Sheet 'change'.")
                        else:
                            st.info("No matching rows found in main sheet for changes.")
                    except Exception as e:
                        st.error(f"Failed to save changes: {e}")
        else:
            st.info("No bills found for this hotel on the selected date.")
    else:
        st.info("No data found for the selected date.") 