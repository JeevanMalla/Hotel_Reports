import pandas as pd
import streamlit as st

def process_data_for_date(df, selected_date):
    """Filter and process data for selected date"""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Convert DATE column to datetime if needed
    try:
        df['DATE'] = pd.to_datetime(df['DATE'], format='%d/%m/%Y', errors='coerce')
        selected_date = pd.to_datetime(selected_date)
        
        # Filter by date
        filtered_df = df[df['DATE'].dt.date == selected_date.date()]
        
        if filtered_df.empty:
            st.warning(f"No data found for date: {selected_date.strftime('%Y-%m-%d')}")
            return pd.DataFrame(), pd.DataFrame()
        
        # Clean and prepare data
        filtered_df.loc[:, 'QUANTITY'] = pd.to_numeric(filtered_df['QUANTITY'], errors='coerce').fillna(0)
        filtered_df = filtered_df[filtered_df['QUANTITY'] > 0]  # Remove zero quantities
        
        return filtered_df, filtered_df
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

def create_vegetable_report_data(df):
    """Create data structure for Report 1: Vegetable-wise summary - SORTED ALPHABETICALLY"""
    if df.empty:
        return pd.DataFrame()
    
    # Define the desired hotel order
    desired_hotel_order = ['NOVOTEL', 'GRANDBAY', 'RADISSONBLU', ' BHEEMILI']
    
    available_hotels = df['MAIN HOTEL NAME'].unique()

    # Create ordered list of hotels - first the desired order, then any others alphabetically
    hotels = []
    for hotel in desired_hotel_order:
        if hotel in available_hotels:
            hotels.append(hotel)
    
    # Add any remaining hotels not in the desired order (sorted alphabetically)
    remaining_hotels = sorted([h for h in available_hotels if h not in desired_hotel_order])
    hotels.extend(remaining_hotels)

    
    # Group by PIVOT_VEGETABLE_NAME AND units combination to handle different units properly
    report_data = []
    
    # Get unique combinations of PIVOT_VEGETABLE_NAME and units
    veg_unit_combinations = df[['PIVOT_VEGETABLE_NAME', 'UNITS', 'TELUGU NAME']].drop_duplicates()
    
    for _, row in veg_unit_combinations.iterrows():
        veg_name = row['PIVOT_VEGETABLE_NAME']
        units = row['UNITS']
        telugu_name = row['TELUGU NAME']
        
        # Filter data for this specific vegetable-unit combination
        veg_data = df[(df['PIVOT_VEGETABLE_NAME'] == veg_name) & (df['UNITS'] == units)]
        
        # Create display name that includes units if there are multiple unit types for same vegetable
        veg_units_count = df[df['PIVOT_VEGETABLE_NAME'] == veg_name]['UNITS'].nunique()
        if veg_units_count > 1:
            display_name = f"{veg_name} ({units})"
        else:
            display_name = veg_name
        
        report_row = {
            'PIVOT_VEGETABLE_NAME': display_name,
            'Telugu Name': telugu_name,
        }
        
        total_qty = 0
        
        # Add quantity for each hotel
        for hotel in hotels:
            hotel_data = veg_data[veg_data['MAIN HOTEL NAME'] == hotel]
            qty = hotel_data['QUANTITY'].sum() if not hotel_data.empty else 0
            report_row[f"{hotel}"] = f"{qty} {units}" if qty > 0 else f"0 {units}"
            total_qty += qty
        
        report_row['Total Quantity'] = f"{total_qty} {units}"
        report_data.append(report_row)
    
    # Convert to DataFrame and sort alphabetically by PIVOT_VEGETABLE_NAME
    result_df = pd.DataFrame(report_data)
    if not result_df.empty:
        result_df = result_df.sort_values('PIVOT_VEGETABLE_NAME', ascending=True).reset_index(drop=True)
    
    return result_df

def create_vendor_report_data(df):
    """Create data structure for Report 2: Vendor-wise summary with Telugu names - SORTED ALPHABETICALLY"""
    if df.empty:
        return {}
    
    # Define the desired hotel order
    desired_hotel_order = ['NOVOTEL', 'GRANDBAY', 'RADISSONBLU', ' BHEEMILI']
    
    # Get unique hotels from data
    available_hotels = df['MAIN HOTEL NAME'].unique()
    
    # Create ordered list of hotels - first the desired order, then any others alphabetically
    hotels = []
    for hotel in desired_hotel_order:
        if hotel in available_hotels:
            hotels.append(hotel)
    
    # Add any remaining hotels not in the desired order (sorted alphabetically)
    remaining_hotels = sorted([h for h in available_hotels if h not in desired_hotel_order])
    hotels.extend(remaining_hotels)
    
    vendors = sorted(df['VENDOR'].dropna().unique())  # Sort vendors alphabetically too

    vendor_reports = {}
    
    for vendor in vendors:
        if pd.isna(vendor) or vendor == '':
            continue
            
        vendor_data = df[df['VENDOR'] == vendor]
        vendor_report = []
        
        # Get unique combinations of PIVOT_VEGETABLE_NAME and units for this vendor
        veg_unit_combinations = vendor_data[['PIVOT_VEGETABLE_NAME', 'UNITS', 'TELUGU NAME']].drop_duplicates()
        
        for _, row in veg_unit_combinations.iterrows():
            veg_name = row['PIVOT_VEGETABLE_NAME']
            units = row['UNITS']
            telugu_name = row['TELUGU NAME']
            
            # Filter data for this specific vegetable-unit combination
            veg_data = vendor_data[(vendor_data['PIVOT_VEGETABLE_NAME'] == veg_name) & (vendor_data['UNITS'] == units)]
            
            # Create display name that includes units if there are multiple unit types for same vegetable
            veg_units_count = vendor_data[vendor_data['PIVOT_VEGETABLE_NAME'] == veg_name]['UNITS'].nunique()
            if veg_units_count > 1:
                display_name = f"{veg_name} ({units})"
            else:
                display_name = veg_name
            
            report_row = {
                'PIVOT_VEGETABLE_NAME': display_name,
                'Telugu Name': telugu_name
            }
            total_qty = 0
            
            for hotel in hotels:
                hotel_data = veg_data[veg_data['MAIN HOTEL NAME'] == hotel]
                qty = hotel_data['QUANTITY'].sum() if not hotel_data.empty else 0
                report_row[hotel] = f"{qty} {units}" if qty > 0 else f"0 {units}"
                total_qty += qty
            
            report_row['Total'] = f"{total_qty} {units}"
            vendor_report.append(report_row)
        
        # Convert to DataFrame and sort alphabetically by PIVOT_VEGETABLE_NAME
        vendor_df = pd.DataFrame(vendor_report)
        if not vendor_df.empty:
            vendor_df = vendor_df.sort_values('PIVOT_VEGETABLE_NAME', ascending=True).reset_index(drop=True)
        
        vendor_reports[vendor] = vendor_df
    
    return vendor_reports
