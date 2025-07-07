import io
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.units import inch
import streamlit as st

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
