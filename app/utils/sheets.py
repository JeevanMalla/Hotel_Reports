import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Constants
# SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
# SPREADSHEET_ID = st.secrets.general.id
# SHEET_NAMES = ['LIST_CREATION']

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = st.secrets.general.id
SHEET_NAMES = ['LIST_CREATION']

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_google_sheets_data():
    """Fetch data from Google Sheets with timeout handling"""
    try:
        credentials = service_account.Credentials.from_service_account_info(st.secrets["google_service_account"],scopes=SCOPES)
        # Authenticate with Google Sheets API
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # Fetch data from the sheet with timeout
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAMES[0]}!A:L"  # Assuming 12 columns (A to L)
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            st.error("No data found in the sheet")
            return pd.DataFrame()
        
        # Convert to DataFrame with proper handling of missing columns
        headers = values[0]
        data = values[1:]
        
        # Ensure all rows have the same number of columns as the header
        for i in range(len(data)):
            # Extend rows that are too short
            while len(data[i]) < len(headers):
                data[i].append('')
            # Truncate rows that are too long
            if len(data[i]) > len(headers):
                data[i] = data[i][:len(headers)]
                
        df = pd.DataFrame(data, columns=headers)  # First row as header
        
        # Debug: Check Telugu name encoding
        if 'TELUGU NAME' in df.columns:
            st.sidebar.write("**Debug - Telugu Names Sample:**")
            sample_telugu = df['TELUGU NAME'].dropna().head(3).tolist()
            for i, name in enumerate(sample_telugu):
                st.sidebar.write(f"{i+1}. {repr(name)} -> {name}")
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching data from Google Sheets: {str(e)}")
        return pd.DataFrame()

def update_google_sheets_prices(prices_data, selected_date):
    """Update actual prices in Google Sheets"""
    try:
        # Authenticate with Google Sheets API
        credentials = service_account.Credentials.from_service_account_info(st.secrets["google_service_account"],scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # Format date for comparison
        date_str = selected_date.strftime('%d/%m/%Y')  # Format used in Google Sheets
        
        # First get the data as a DataFrame for easier filtering
        df = get_google_sheets_data()
        if df.empty:
            return False, "No data found in Google Sheets"
        
        # Make sure all column names are uppercase for consistency
        df.columns = [col.upper() for col in df.columns]
        
        # Add ACTUAL PRICE column if it doesn't exist
        if 'ACTUAL PRICE' not in df.columns:
            df['ACTUAL PRICE'] = ''
            
            # Get the original sheet data to update headers
            result = sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_NAMES[0]}!1:1"  # Just get headers
            ).execute()
            
            headers = result.get('values', [[]])[0]
            headers.append('ACTUAL PRICE')
            
            # Update the headers in Google Sheets
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_NAMES[0]}!A1:{chr(65 + len(headers) - 1)}1",
                valueInputOption='USER_ENTERED',
                body={'values': [headers]}
            ).execute()
        
        # Check required columns exist
        required_columns = ['DATE', 'PIVOT_VEGETABLE_NAME', 'UNITS', 'ACTUAL PRICE']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns in Google Sheets: {missing_columns}"
        
        # Filter only rows for the selected date
        date_df = df[df['DATE'] == date_str]
        if date_df.empty:
            return False, f"No entries found for date {date_str} in Google Sheets"
        
        # Get the original sheet data to find row indices
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAMES[0]}"
        ).execute()
        
        all_values = result.get('values', [])
        if not all_values:
            return False, "No data found in Google Sheets"
            
        headers = all_values[0]
        actual_price_col_idx = headers.index('ACTUAL PRICE') if 'ACTUAL PRICE' in headers else len(headers)
        
        # Prepare batch updates
        batch_updates = []
        updates_count = 0
        
        # For each price entry, find matching row in the filtered dataframe
        for price_item in prices_data:
            veg_name = price_item['vegetable_name']
            units = price_item['units']
            price = price_item['actual_price']
            
            if price == 0:
                continue  # Skip zero prices
            
            # Find matching rows in the sheet data
            for i, row in enumerate(all_values[1:], start=2):  # Start from 2 for 1-indexing and header
                if len(row) <= 2:  # Skip very short rows
                    continue
                    
                try:
                    date_col_idx = headers.index('DATE')
                    veg_name_col_idx = headers.index('PIVOT_VEGETABLE_NAME')
                    units_col_idx = headers.index('UNITS')
                    
                    # Make sure row has enough elements
                    if (len(row) > date_col_idx and 
                        len(row) > veg_name_col_idx and 
                        len(row) > units_col_idx):
                        
                        # Check for exact match
                        if (row[date_col_idx] == date_str and 
                            row[veg_name_col_idx].strip() == veg_name.strip() and 
                            row[units_col_idx].strip() == units.strip()):
                            
                            # Add to batch update
                            cell_range = f"{SHEET_NAMES[0]}!{chr(65 + actual_price_col_idx)}{i}"
                            batch_updates.append({
                                'range': cell_range,
                                'values': [[str(price)]]
                            })
                            updates_count += 1
                except (IndexError, ValueError) as e:
                    st.sidebar.write(f"Error processing row {i}: {str(e)}")
                    continue  # Skip problematic rows
        
        if updates_count == 0:
            return False, "No matching rows found to update prices"
        
        # Execute batch update
        if batch_updates:
            body = {
                'valueInputOption': 'USER_ENTERED',
                'data': batch_updates
            }
            
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body
            ).execute()
        
        return True, f"Successfully updated {updates_count} price entries in Google Sheets"
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return False, f"Error updating prices in Google Sheets: {str(e)}\n{error_details}"
