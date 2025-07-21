import io
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.units import inch
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.sheets import get_google_sheets_data
from utils.data_processing import process_data_for_date
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Register Telugu font if needed
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont('NotoSansTelugu', './NotoSansTelugu.ttf'))
except Exception as e:
    st.warning(f"Could not register Telugu font: {str(e)}")

def create_kitchen_bills_pdf(df, selected_date):
    """Generate PDF with bills for each kitchen - sorted alphabetically by vegetable name"""
    if df.empty:
        return None
        
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Define custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        spaceBefore=10,
        alignment=1,
        textColor=colors.darkblue
    )
    
    kitchen_title_style = ParagraphStyle(
        'KitchenTitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=15,
        spaceBefore=10,
        alignment=1,
        textColor=colors.darkgreen
    )
    
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=20,
        alignment=1,
        textColor=colors.grey
    )
    
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=11,
        alignment=1,
        textColor=colors.darkgreen
    )
    
    no_data_style = ParagraphStyle(
        'NoData',
        parent=styles['Normal'],
        fontSize=14,
        alignment=1,
        textColor=colors.red
    )
    
    # Group data by hotel and kitchen
    if 'KITCHEN NAME' not in df.columns:
        # If KITCHEN NAME column doesn't exist, use MAIN HOTEL NAME as kitchen
        df['KITCHEN NAME'] = df['MAIN HOTEL NAME']
    
    # Get unique hotels
    hotels = sorted(df['MAIN HOTEL NAME'].unique())
    
    # Process each hotel
    for hotel in hotels:
        hotel_data = df[df['MAIN HOTEL NAME'] == hotel]
        
        # Get unique kitchens for this hotel
        kitchens = sorted(hotel_data['KITCHEN NAME'].unique())
        
        # Add hotel title
        hotel_title = Paragraph(f"Hotel: {hotel}", title_style)
        story.append(hotel_title)
        story.append(Paragraph(f"Date: {selected_date.strftime('%Y-%m-%d')}", date_style))
        
        # Process each kitchen
        for kitchen_idx, kitchen in enumerate(kitchens):
            kitchen_data = hotel_data[hotel_data['KITCHEN NAME'] == kitchen]
            
            # Create kitchen title
            kitchen_title = Paragraph(f"Kitchen: {kitchen}", kitchen_title_style)
            
            # Create a list to hold all kitchen elements that should stay together
            kitchen_elements = [kitchen_title, Spacer(1, 10)]
            
            if kitchen_data.empty:
                kitchen_elements.append(Paragraph("No orders found for this kitchen on the selected date.", no_data_style))
            else:
                # Group by vegetable and sum quantities (handling multiple units)
                kitchen_report_data = []
                
                # Get unique combinations of PIVOT_VEGETABLE_NAME and units for this kitchen
                veg_unit_combinations = kitchen_data[['PIVOT_VEGETABLE_NAME', 'UNITS', 'TELUGU NAME']].drop_duplicates()
                
                for _, row in veg_unit_combinations.iterrows():
                    veg_name = row['PIVOT_VEGETABLE_NAME']
                    units = row['UNITS']
                    telugu_name = row['TELUGU NAME']
                    
                    # Filter data for this specific vegetable-unit combination
                    veg_data = kitchen_data[(kitchen_data['PIVOT_VEGETABLE_NAME'] == veg_name) & 
                                          (kitchen_data['UNITS'] == units)]
                    total_qty = veg_data['QUANTITY'].sum()
                    
                    if total_qty > 0:  # Only include items with quantity > 0
                        # Create display name that includes units if there are multiple unit types for same vegetable
                        veg_units_count = kitchen_data[kitchen_data['PIVOT_VEGETABLE_NAME'] == veg_name]['UNITS'].nunique()
                        if veg_units_count > 1:
                            display_name = f"{veg_name} ({units})"
                        else:
                            display_name = veg_name
                        
                        # Get price if available
                        price = ""
                        if 'PRICE' in veg_data.columns:
                            price_values = veg_data['PRICE'].dropna()
                            if not price_values.empty:
                                price = price_values.iloc[0]
                        
                        # Calculate total amount if price is available
                        total = ""
                        if price and str(price).strip() and str(price) != 'nan':
                            try:
                                price_float = float(price)
                                total = price_float * total_qty
                                total = f"{total:.2f}"
                                price = f"{price_float:.2f}"
                            except (ValueError, TypeError):
                                pass
                        
                        kitchen_report_data.append([
                            display_name,
                            telugu_name if telugu_name and str(telugu_name) != 'nan' else '',
                            f"{total_qty} {units}",
                            price,
                            total
                        ])
                
                # Sort alphabetically by vegetable name
                kitchen_report_data.sort(key=lambda x: x[0])
                
                if kitchen_report_data:
                    # Create table
                    table_data = [['Vegetable Name', 'Telugu Name', 'Quantity', 'PRICE', 'TOTAL']]
                    table_data.extend(kitchen_report_data)
                    
                    # Calculate column widths
                    available_width = 7 * inch  # A4 width minus margins
                    col_widths = [2*inch, 1.5*inch, 1*inch, 1*inch, 1.5*inch]
                    
                    table = Table(table_data, colWidths=col_widths)
                    table.setStyle(TableStyle([
                        # Header styling
                        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 11),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        
                        # Data rows styling
                        ('FONTNAME', (1, 1), (1, -1), 'NotoSansTelugu'),  # Telugu column
                        ('FONTSIZE', (0, 1), (-1, -1), 10),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (2, 1), (4, -1), 'RIGHT'),  # Right align quantity, price and total columns
                    ]))
                    
                    # Add table to kitchen elements
                    kitchen_elements.append(table)
                    
                    # Calculate grand total
                    grand_total = 0
                    for row in kitchen_report_data:
                        if row[4] and row[4].strip():
                            try:
                                grand_total += float(row[4])
                            except (ValueError, TypeError):
                                pass
                    
                    # Add summary with grand total
                    total_items = len(kitchen_report_data)
                    summary_text = f"Total Items: {total_items} | Grand Total: {grand_total:.2f}"
                    summary = Paragraph(summary_text, summary_style)
                    kitchen_elements.append(Spacer(1, 20))
                    kitchen_elements.append(summary)
                    
                    # Add all kitchen elements as a single KeepTogether unit
                    story.append(KeepTogether(kitchen_elements))
                else:
                    kitchen_elements.append(Paragraph("No items with quantities found for this kitchen.", no_data_style))
                    story.append(KeepTogether(kitchen_elements))
            
            # Add spacer between kitchens
            story.append(Spacer(1, 20))
            
            # If not the last kitchen, add more spacing
            if kitchen_idx < len(kitchens) - 1:
                story.append(Spacer(1, 20))
        
        # Add page break after each hotel except the last one
        if hotel != hotels[-1]:
            story.append(PageBreak())
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def create_kitchen_bills_preview(df, selected_date):
    """Create a preview of kitchen bills for Streamlit display"""
    if df.empty:
        return None
    
    # Group data by hotel and kitchen
    if 'KITCHEN NAME' not in df.columns:
        # If KITCHEN NAME column doesn't exist, use MAIN HOTEL NAME as kitchen
        df['KITCHEN NAME'] = df['MAIN HOTEL NAME']
    
    # Get unique hotels
    hotels = sorted(df['MAIN HOTEL NAME'].unique())
    
    # Create preview data structure
    preview_data = {}
    
    # Process each hotel
    for hotel in hotels:
        hotel_data = df[df['MAIN HOTEL NAME'] == hotel]
        
        # Get unique kitchens for this hotel
        kitchens = sorted(hotel_data['KITCHEN NAME'].unique())
        
        hotel_kitchens = {}
        
        # Process each kitchen
        for kitchen in kitchens:
            kitchen_data = hotel_data[hotel_data['KITCHEN NAME'] == kitchen]
            
            if not kitchen_data.empty:
                # Group by vegetable and sum quantities (handling multiple units)
                kitchen_report_data = []
                
                # Get unique combinations of PIVOT_VEGETABLE_NAME and units for this kitchen
                veg_unit_combinations = kitchen_data[['PIVOT_VEGETABLE_NAME', 'UNITS', 'TELUGU NAME']].drop_duplicates()
                
                for _, row in veg_unit_combinations.iterrows():
                    veg_name = row['PIVOT_VEGETABLE_NAME']
                    units = row['UNITS']
                    telugu_name = row['TELUGU NAME']
                    
                    # Filter data for this specific vegetable-unit combination
                    veg_data = kitchen_data[(kitchen_data['PIVOT_VEGETABLE_NAME'] == veg_name) & 
                                          (kitchen_data['UNITS'] == units)]
                    total_qty = veg_data['QUANTITY'].sum()
                    
                    if total_qty > 0:  # Only include items with quantity > 0
                        # Create display name that includes units if there are multiple unit types for same vegetable
                        veg_units_count = kitchen_data[kitchen_data['PIVOT_VEGETABLE_NAME'] == veg_name]['UNITS'].nunique()
                        if veg_units_count > 1:
                            display_name = f"{veg_name} ({units})"
                        else:
                            display_name = veg_name
                        
                        # Get price if available
                        price = ""
                        if 'PRICE' in veg_data.columns:
                            price_values = veg_data['PRICE'].dropna()
                            if not price_values.empty:
                                price = price_values.iloc[0]
                        
                        # Calculate total amount if price is available
                        total = ""
                        if price and str(price).strip() and str(price) != 'nan':
                            try:
                                price_float = float(price)
                                total = price_float * total_qty
                                total = f"{total:.2f}"
                                price = f"{price_float:.2f}"
                            except (ValueError, TypeError):
                                pass
                        
                        kitchen_report_data.append({
                            'Vegetable Name': display_name,
                            'Telugu Name': telugu_name if telugu_name and str(telugu_name) != 'nan' else '',
                            'Quantity': f"{total_qty} {units}",
                            'PRICE': price,
                            'TOTAL': total
                        })
                
                # Sort alphabetically by vegetable name
                kitchen_report_data.sort(key=lambda x: x['Vegetable Name'])
                
                if kitchen_report_data:
                    # Convert to DataFrame for display
                    kitchen_df = pd.DataFrame(kitchen_report_data)
                    
                    # Calculate grand total
                    grand_total = 0
                    for item in kitchen_report_data:
                        if item['TOTAL'] and item['TOTAL'].strip():
                            try:
                                grand_total += float(item['TOTAL'])
                            except (ValueError, TypeError):
                                pass
                    
                    hotel_kitchens[kitchen] = {
                        'data': kitchen_df,
                        'grand_total': f"{grand_total:.2f}"
                    }
        
        if hotel_kitchens:
            preview_data[hotel] = hotel_kitchens
    
    return preview_data

# --- Streamlit Editable Bills Section ---
st.header("📝 Editable Bills Section")

# Select date, hotel, kitchen
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

# Filter data for selection
filtered_df, _ = process_data_for_date(df, selected_date)
if not filtered_df.empty:
    bills_df = filtered_df[(filtered_df['MAIN HOTEL NAME'] == selected_hotel) & (filtered_df['KITCHEN NAME'] == selected_kitchen)]
    if not bills_df.empty:
        # Prepare editable table for st.data_editor
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
        # Save button
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
        # Show the edited table
        st.subheader("Edited Table (Current Session)")
        st.dataframe(edited_df, use_container_width=True)
        # Reset button
        if st.button("Reset Edits", key="bills_reset_edits"):
            st.experimental_rerun()
    else:
        st.info("No bills found for this hotel and kitchen on the selected date.")
else:
    st.info("No data found for the selected date.")
