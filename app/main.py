import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
import os

# Import modules
from utils.sheets import get_google_sheets_data
from utils.data_processing import process_data_for_date, create_vegetable_report_data, create_vendor_report_data
from database.mongodb import push_data_to_mongodb, get_vegetable_prices, save_vegetable_prices
from reports.individual_reports import create_individual_hotel_reports_pdf
from reports.combined_reports import create_combined_report_pdf
from reports.bills_reports import create_kitchen_bills_pdf, create_kitchen_bills_preview
from reports.hotel_summary import create_hotel_summary_pdf

def check_password():
    """Simple password authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 Secure Access")
        password = st.text_input("Enter password to access the app:", type="password")
        
        if password == st.secrets.general.app_password:  # Replace with your password
            st.session_state.authenticated = True
            st.success("✅ Access granted. Loading app...")
            st.rerun()
        elif password != "":
            st.error("❌ Incorrect password")
        return False
    else:
        return True

def main():
    if not check_password():
        return  # Stop app from loading unless authenticated
    
    st.set_page_config(
        page_title="Hotel Order Management System",
        page_icon="🏨",
        layout="wide"
    )
    
    st.title("🏨 Hotel Order Management System")
    st.markdown("---")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page:", ["Home", "Data Preview", "Price Management", "Bills"])
    
    if page == "Home":
        st.header("Generate Reports")
        
        # Date selector and Fetch Data button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            selected_date = st.date_input(
                "Select Date:",
                value=datetime.now().date(),
                help="Select the date for which you want to generate reports"
            )
        
        with col3:
            if st.button("🔄 Fetch Latest Data", help="Refresh data from Google Sheets"):
                st.cache_data.clear()
                st.success("Data refreshed from Google Sheets!")
                st.rerun()
        
        # Generate reports button
        if st.button("🔄 Generate Reports", type="primary"):
            # Initialize progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Fetch data
            status_text.text("Step 1/4: Fetching data from Google Sheets...")
            progress_bar.progress(25)
            
            df = get_google_sheets_data()
            
            if not df.empty:
                # Step 2: Process data
                status_text.text("Step 2/4: Processing data...")
                progress_bar.progress(50)
                
                # Step 3: Generate reports
                status_text.text("Step 3/4: Generating reports...")
                progress_bar.progress(75)
                
                try:
                    # Generate reports
                    veg_report_data, vendor_report_data, combined_pdf_buffer, individual_hotel_pdf_buffer, kitchen_bills_pdf_buffer, kitchen_bills_preview = generate_reports(df, selected_date)
                    
                    # Step 4: Complete
                    status_text.text("Step 4/4: Finalizing...")
                    progress_bar.progress(100)
                    
                    if veg_report_data is not None:
                        # Display summary
                        status_text.text("✅ Reports generated successfully!")
                        st.success(f"Data processed successfully for {selected_date}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Total Vegetables", len(veg_report_data))
                        with col2:
                            st.metric("Total Vendors", len(vendor_report_data) if vendor_report_data else 0)
                        
                        # MongoDB Push Button
                        if st.button("📤 Push Data to MongoDB", type="primary"):
                            with st.spinner("Pushing data to MongoDB..."):
                                success, message = push_data_to_mongodb(df, selected_date)
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                        
                        # PDF download buttons
                        st.markdown("### 📥 Download Reports")
                        
                        # Create three columns for download buttons
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if combined_pdf_buffer:
                                st.download_button(
                                    label="📊 Download Complete Summary Report",
                                    data=combined_pdf_buffer.getvalue(),
                                    file_name=f"complete_order_report_{selected_date.strftime('%Y%m%d')}.pdf",
                                    mime="application/pdf",
                                    help="Downloads vegetable-wise and vendor-wise summary reports in a single PDF"
                                )
                        
                        with col2:
                            if individual_hotel_pdf_buffer:
                                st.download_button(
                                    label="🏨 Download Individual Hotel Reports",
                                    data=individual_hotel_pdf_buffer.getvalue(),
                                    file_name=f"individual_hotel_reports_{selected_date.strftime('%Y%m%d')}.pdf",
                                    mime="application/pdf",
                                    help="Downloads individual reports for each hotel (one hotel per page)"
                                )
                        
                        with col3:
                            if kitchen_bills_pdf_buffer:
                                st.download_button(
                                    label="🧾 Download Kitchen Bills",
                                    data=kitchen_bills_pdf_buffer.getvalue(),
                                    file_name=f"kitchen_bills_{selected_date.strftime('%Y%m%d')}.pdf",
                                    mime="application/pdf",
                                    help="Downloads bills for each kitchen sorted alphabetically by vegetable name"
                                )
                        
                        # Preview data
                        with st.expander("🔍 Preview Vegetable Report Data (Sorted Alphabetically)"):
                            st.dataframe(veg_report_data, use_container_width=True)
                        
                        if vendor_report_data:
                            with st.expander("🔍 Preview Vendor Report Data (Sorted Alphabetically)"):
                                for vendor, data in vendor_report_data.items():
                                    st.subheader(f"Vendor: {vendor}")
                                    st.dataframe(data, use_container_width=True)
                    else:
                        st.warning("No data found for the selected date.")
                
                except Exception as e:
                    st.error(f"Error generating reports: {str(e)}")
                
                finally:
                    # Clean up progress indicators
                    progress_bar.empty()
                    status_text.empty()
            else:
                progress_bar.empty()
                status_text.empty()
                st.error("Failed to fetch data from Google Sheets.")
    
    elif page == "Data Preview":
        st.header("📋 Data Preview")
        
        with st.spinner("Loading data from Google Sheets..."):
            df = get_google_sheets_data()
        
        if not df.empty:
            st.success(f"Successfully loaded {len(df)} records")
            
            # Show basic info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", len(df))
            with col2:
                st.metric("Unique Hotels", df['MAIN HOTEL NAME'].nunique() if 'MAIN HOTEL NAME' in df.columns else 0)
            with col3:
                st.metric("Unique Vegetables", df['PIVOT_VEGETABLE_NAME'].nunique() if 'PIVOT_VEGETABLE_NAME' in df.columns else 0)
            
            # Add filters
            st.subheader("🔍 Filter Data")
            
            # Convert DATE column to datetime if needed
            if 'DATE' in df.columns:
                try:
                    df['DATE'] = pd.to_datetime(df['DATE'], format='%d/%m/%Y', errors='coerce')
                except Exception as e:
                    st.warning(f"Error converting dates: {str(e)}")
            
            # Create filters in columns
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                # Date filter
                if 'DATE' in df.columns:
                    min_date = df['DATE'].min().date() if not df['DATE'].isna().all() else datetime.now().date()
                    max_date = df['DATE'].max().date() if not df['DATE'].isna().all() else datetime.now().date()
                    
                    selected_date_range = st.date_input(
                        "Select Date Range:",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date + timedelta(days=30),  # Allow some future dates
                        help="Filter data by date range"
                    )
                    
                    # Handle date selection
                    # Check if it's a tuple containing a tuple (this happens in some Streamlit versions)
                    if isinstance(selected_date_range, tuple) and len(selected_date_range) == 1 and isinstance(selected_date_range[0], tuple):
                        selected_date_range = selected_date_range[0]
                    
                    # Now handle as normal tuple or single date
                    if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
                        start_date, end_date = selected_date_range
                    else:
                        start_date = end_date = selected_date_range
                    
                    # Convert to datetime for filtering - safely
                    try:
                        start_datetime = pd.Timestamp(start_date)
                        end_datetime = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                    except TypeError:
                        st.error(f"Error processing date range: {selected_date_range}")
                        start_datetime = pd.Timestamp(min_date)
                        end_datetime = pd.Timestamp(max_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                    
                    # Filter by date
                    df_filtered = df[(df['DATE'] >= start_datetime) & (df['DATE'] <= end_datetime)]
                else:
                    df_filtered = df.copy()
                    st.info("No DATE column found in data.")
            
            with filter_col2:
                # Hotel filter
                if 'MAIN HOTEL NAME' in df.columns:
                    available_hotels = sorted(df_filtered['MAIN HOTEL NAME'].unique())
                    selected_hotels = st.multiselect(
                        "Select Hotels:",
                        options=available_hotels,
                        default=available_hotels,
                        help="Filter by hotel(s)"
                    )
                    
                    if selected_hotels:
                        df_filtered = df_filtered[df_filtered['MAIN HOTEL NAME'].isin(selected_hotels)]
                else:
                    st.info("No MAIN HOTEL NAME column found in data.")
            
            # Show filter summary
            st.info(f"Showing {len(df_filtered)} records after filtering")
            
            # Display filtered data
            st.subheader("Filtered Data")
            st.dataframe(df_filtered, use_container_width=True, height=400)
            
            # Hotel summary section
            if not df_filtered.empty and 'MAIN HOTEL NAME' in df_filtered.columns:
                st.subheader("Hotel Summaries")
                st.write("Download summary PDF with date, hotel name, and total amount:")
                
                # Get unique hotels
                unique_hotels = sorted(df_filtered['MAIN HOTEL NAME'].unique())
                
                # Create a grid of download buttons (3 per row)
                cols = st.columns(3)
                
                for i, hotel in enumerate(unique_hotels):
                    with cols[i % 3]:
                        # Filter data for this hotel
                        hotel_data = df_filtered[df_filtered['MAIN HOTEL NAME'] == hotel]
                        
                        if not hotel_data.empty:
                            # Get the date for the summary
                            if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
                                # Use the full date range
                                date_range = selected_date_range
                            else:
                                # If single date, use that date
                                date_range = selected_date_range
                            
                            # Create hotel summary PDF
                            hotel_summary_buffer = create_hotel_summary_pdf(hotel_data, date_range, hotel)
                            
                            if hotel_summary_buffer:
                                # Determine file name based on date range
                                if isinstance(date_range, tuple) and len(date_range) == 2:
                                    file_name = f"{hotel}_summary_{date_range[0].strftime('%Y%m%d')}_to_{date_range[1].strftime('%Y%m%d')}.pdf"
                                else:
                                    file_name = f"{hotel}_summary_{date_range.strftime('%Y%m%d')}.pdf"
                                
                                st.download_button(
                                    label=f"📥 {hotel} Summary",
                                    data=hotel_summary_buffer.getvalue(),
                                    file_name=file_name,
                                    mime="application/pdf",
                                    help=f"Download summary PDF for {hotel} showing daily totals and grand total"
                                )
            
            # Show column info
            with st.expander("📊 Column Information"):
                st.write("**Columns in the dataset:**")
                for i, col in enumerate(df.columns, 1):
                    st.write(f"{i}. {col}")
                    
            # Option to download filtered data
            if not df_filtered.empty:
                csv = df_filtered.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Filtered Data as CSV",
                    data=csv,
                    file_name=f"hotel_data_filtered_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )
        
        else:
            st.error("No data available or failed to connect to Google Sheets.")
    
    elif page == "Price Management":
        st.header("💰 Vegetable Price Management")
        
        # Date selector and Fetch Data button in the same row
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_date = st.date_input(
                "Select Date:",
                value=datetime.now().date(),
                help="Select the date for which you want to manage prices"
            )
        
        with col2:
            fetch_data = st.button("🔄 Fetch Latest Data", help="Refresh data from Google Sheets")
            if fetch_data:
                st.cache_data.clear()
                st.success("Data refreshed from Google Sheets!")
                st.rerun()
        
        # Get data
        with st.spinner("Loading data..."):
            df = get_google_sheets_data()
            filtered_df, _ = process_data_for_date(df, selected_date)
            
            # Get existing prices from MongoDB
            existing_prices = get_vegetable_prices(selected_date)
            
            # Show status of price data
            if not existing_prices.empty:
                st.success(f"✅ Found saved prices for {selected_date.strftime('%Y-%m-%d')}")
            else:
                st.info("ℹ️ No saved prices found for this date. Enter prices below.")
        
        if not filtered_df.empty:
            # Get unique vegetables with Telugu names
            veg_data = filtered_df[['PIVOT_VEGETABLE_NAME', 'UNITS', 'TELUGU NAME']].drop_duplicates()
            veg_data = veg_data.sort_values('PIVOT_VEGETABLE_NAME')
            
            # Create price input form
            st.subheader("Enter Actual Prices")
            
            with st.form("price_form"):
                prices = []
                
                for _, row in veg_data.iterrows():
                    veg_name = row['PIVOT_VEGETABLE_NAME']
                    units = row['UNITS']
                    telugu_name = row['TELUGU NAME'] if pd.notna(row['TELUGU NAME']) else ""
                    
                    # Get price from Google Sheets if available
                    sheets_price = ""
                    if 'PRICE' in filtered_df.columns:
                        price_from_sheets = filtered_df[(filtered_df['PIVOT_VEGETABLE_NAME'] == veg_name) & 
                                                      (filtered_df['UNITS'] == units)]['PRICE'].values
                        if len(price_from_sheets) > 0 and pd.notna(price_from_sheets[0]):
                            sheets_price = price_from_sheets[0]
                    
                    # Create display name that includes units if there are multiple unit types for same vegetable
                    veg_units_count = filtered_df[filtered_df['PIVOT_VEGETABLE_NAME'] == veg_name]['UNITS'].nunique()
                    if veg_units_count > 1:
                        display_name = f"{veg_name} ({units})"
                    else:
                        display_name = veg_name
                    
                    # Check if price exists in MongoDB
                    existing_price = ""
                    if not existing_prices.empty:
                        price_row = existing_prices[(existing_prices['vegetable_name'] == veg_name) & 
                                                  (existing_prices['units'] == units)]
                        if not price_row.empty:
                            existing_price = price_row.iloc[0]['actual_price']
                            
                    # Create a unique key for this vegetable to maintain state between reruns
                    input_key = f"price_{veg_name}_{units}_{selected_date.strftime('%Y%m%d')}"
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.text(display_name)
                    with col2:
                        st.text(telugu_name)
                    with col3:
                        # Use existing price if available, otherwise use Google Sheets price or leave empty
                        price = st.number_input(f"Price for {display_name}", 
                                               min_value=0.0, 
                                               value=float(existing_price) if existing_price else None,
                                               key=input_key,
                                               label_visibility="collapsed")
                    
                    # If price is 0 (not entered), use the price from Google Sheets
                    final_price = price
                    if price == 0 and sheets_price:
                        try:
                            final_price = float(sheets_price)
                        except (ValueError, TypeError):
                            final_price = 0
                    
                    prices.append({
                        'vegetable_name': veg_name,
                        'telugu_name': telugu_name,
                        'units': units,
                        'actual_price': final_price
                    })
                
                submit_button = st.form_submit_button("💾 Save Prices")
                
                if submit_button:
                    # Save prices to MongoDB
                    mongo_success, mongo_message = save_vegetable_prices(prices, selected_date)
                    
                    # Also save prices to Google Sheets
                    from utils.sheets import update_google_sheets_prices
                    sheets_success, sheets_message = update_google_sheets_prices(prices, selected_date)
                    
                    if mongo_success and sheets_success:
                        st.success(f"✅ {mongo_message}\n✅ {sheets_message}")
                        # Refresh the page to show updated prices
                        st.rerun()
                    elif mongo_success:
                        st.warning(f"✅ {mongo_message}\n❌ {sheets_message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {mongo_message}\n{'✅' if sheets_success else '❌'} {sheets_message}")
        else:
            st.warning(f"No data found for date: {selected_date}")

    elif page == "Bills":
        st.header("🧾 Kitchen Bills")
        
        # Date selector and Fetch Data button in the same row
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_date = st.date_input(
                "Select Date:",
                value=datetime.now().date(),
                help="Select the date for which you want to view kitchen bills"
            )
        
        with col2:
            fetch_data = st.button("🔄 Fetch Latest Data", help="Refresh data from Google Sheets")
            if fetch_data:
                st.cache_data.clear()
                st.success("Data refreshed from Google Sheets!")
                st.rerun()
        
        # Get data
        with st.spinner("Loading data..."):
            df = get_google_sheets_data()
            filtered_df, _ = process_data_for_date(df, selected_date)
            
            if filtered_df.empty:
                st.warning(f"No data found for date: {selected_date.strftime('%Y-%m-%d')}")
            else:
                # Generate kitchen bills preview
                kitchen_bills_preview = create_kitchen_bills_preview(filtered_df, selected_date)
                
                if kitchen_bills_preview:
                    # Generate PDF for download
                    kitchen_bills_pdf_buffer = create_kitchen_bills_pdf(filtered_df, selected_date)
                    
                    # Download button
                    if kitchen_bills_pdf_buffer:
                        st.download_button(
                            label="📥 Download Kitchen Bills PDF",
                            data=kitchen_bills_pdf_buffer.getvalue(),
                            file_name=f"kitchen_bills_{selected_date.strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            help="Download bills for each kitchen sorted alphabetically by vegetable name"
                        )
                    
                    # Display preview
                    st.subheader("Bills Preview")
                    
                    # Display each hotel and its kitchens
                    for hotel, kitchens in kitchen_bills_preview.items():
                        with st.expander(f"Hotel: {hotel}", expanded=True):
                            for kitchen, kitchen_data in kitchens.items():
                                st.markdown(f"#### Kitchen: {kitchen}")
                                st.dataframe(kitchen_data['data'], use_container_width=True)
                                st.markdown(f"**Grand Total: {kitchen_data['grand_total']}**")
                                st.markdown("---")
                else:
                    st.warning("No kitchen bills data available for the selected date.")

def generate_reports(df, selected_date):
    """Generate all reports for the selected date"""
    try:
        # Process data for the selected date
        filtered_df, _ = process_data_for_date(df, selected_date)
        
        if filtered_df.empty:
            return None, None, None, None, None, None
        
        # Create report data structures
        veg_report_data = create_vegetable_report_data(filtered_df)
        vendor_report_data = create_vendor_report_data(filtered_df)
        
        # Generate PDFs
        combined_pdf_buffer = create_combined_report_pdf(veg_report_data, vendor_report_data, selected_date)
        individual_hotel_pdf_buffer = create_individual_hotel_reports_pdf(filtered_df, selected_date)
        kitchen_bills_pdf_buffer = create_kitchen_bills_pdf(filtered_df, selected_date)
        
        # Create kitchen bills preview data
        kitchen_bills_preview = create_kitchen_bills_preview(filtered_df, selected_date)
        
        return veg_report_data, vendor_report_data, combined_pdf_buffer, individual_hotel_pdf_buffer, kitchen_bills_pdf_buffer, kitchen_bills_preview
    except Exception as e:
        st.error(f"Error generating reports: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None, None, None, None, None, None

if __name__ == "__main__":
    main()
