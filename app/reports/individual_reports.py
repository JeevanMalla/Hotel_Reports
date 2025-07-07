import io
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
import streamlit as st

# Register Telugu font if needed
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont('NotoSansTelugu', './NotoSansTelugu.ttf'))
except Exception as e:
    st.warning(f"Could not register Telugu font: {str(e)}")

def create_individual_hotel_reports_pdf(df, selected_date):
    """Generate PDF with individual reports for each hotel - one hotel per page exactly"""
    if df.empty:
        return None
        
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    
    # Define the desired hotel order
    desired_hotel_order = ['NOVOTEL', 'GRANDBAY', 'RADISSONBLU', ' BHEEMILI']
    
    # Get unique hotels from data in desired order
    available_hotels = df['MAIN HOTEL NAME'].unique()
    hotels = []
    for hotel in desired_hotel_order:
        if hotel in available_hotels:
            hotels.append(hotel)
    
    # Add any remaining hotels not in the desired order (sorted alphabetically)
    remaining_hotels = sorted([h for h in available_hotels if h not in desired_hotel_order])
    hotels.extend(remaining_hotels)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Define styles
    hotel_title_style = ParagraphStyle(
        'HotelTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        spaceBefore=10,
        alignment=1,
        textColor=colors.darkblue
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
    
    # Generate individual hotel reports - one per page
    for hotel_index, hotel in enumerate(hotels):
        # Hotel title and date on a single line
        combined_title = Paragraph(f"Hotel: {hotel}  -  Date: {selected_date.strftime('%Y-%m-%d')}", hotel_title_style)
        story.append(combined_title)
        
        # Filter data for this hotel
        hotel_data = df[df['MAIN HOTEL NAME'] == hotel]
        
        if hotel_data.empty:
            story.append(Paragraph("No orders found for this hotel on the selected date.", no_data_style))
        else:
            # Group by vegetable and sum quantities (handling multiple units)
            hotel_report_data = []
            
            # Get unique combinations of PIVOT_VEGETABLE_NAME and units for this hotel
            veg_unit_combinations = hotel_data[['PIVOT_VEGETABLE_NAME', 'UNITS', 'TELUGU NAME']].drop_duplicates()
            
            for _, row in veg_unit_combinations.iterrows():
                veg_name = row['PIVOT_VEGETABLE_NAME']
                units = row['UNITS']
                telugu_name = row['TELUGU NAME']
                
                # Filter data for this specific vegetable-unit combination
                veg_data = hotel_data[(hotel_data['PIVOT_VEGETABLE_NAME'] == veg_name) & (hotel_data['UNITS'] == units)]
                total_qty = veg_data['QUANTITY'].sum()
                
                if total_qty > 0:  # Only include items with quantity > 0
                    # Create display name that includes units if there are multiple unit types for same vegetable
                    veg_units_count = hotel_data[hotel_data['PIVOT_VEGETABLE_NAME'] == veg_name]['UNITS'].nunique()
                    if veg_units_count > 1:
                        display_name = f"{veg_name} ({units})"
                    else:
                        display_name = veg_name
                    
                    hotel_report_data.append([
                        display_name,
                        telugu_name if telugu_name and str(telugu_name) != 'nan' else '',
                        f"{total_qty} {units}"
                    ])
            
            # Sort alphabetically by vegetable name
            hotel_report_data.sort(key=lambda x: x[0])
            
            if hotel_report_data:
                # Create table
                table_data = [['Vegetable Name', 'Telugu Name', 'Quantity']]
                table_data.extend(hotel_report_data)
                
                # Calculate column widths
                available_width = 7 * inch  # A4 width minus margins
                col_widths = [2.5*inch, 2*inch, 2.5*inch]
                
                # Adjust font size based on number of items to ensure it fits on one page
                font_size = 10  # Default font size
                
                table = Table(table_data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    # Header styling
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),  # Slightly smaller header
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),  # Reduced padding
                    
                    # Data rows styling
                    ('FONTNAME', (1, 1), (1, -1), 'NotoSansTelugu'),  # Telugu column
                    ('FONTSIZE', (0, 1), (-1, -1), font_size),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),  # Reduced padding
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),  # Reduced padding
                    ('TOPPADDING', (0, 0), (-1, -1), 1),  # Minimal top padding
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),  # Minimal bottom padding
                ]))
                
                story.append(table)
                
                # Add summary
                story.append(Spacer(1, 20))
                total_items = len(hotel_report_data)
                summary_text = f"Total Items Ordered: {total_items}"
                story.append(Paragraph(summary_text, summary_style))
            else:
                story.append(Paragraph("No items with quantities found for this hotel.", no_data_style))
        
        # Add page break after each hotel except the last one
        if hotel_index < len(hotels) - 1:
            story.append(PageBreak())
    
    # Add a separate price page at the end with all vegetables
    story.append(PageBreak())
    
    # Price page title
    price_title_style = ParagraphStyle(
        'PriceTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        spaceBefore=10,
        alignment=1,
        textColor=colors.darkgreen
    )
    # Combined price title and date on a single line
    combined_price_title = Paragraph(f"Vegetable Prices  -  Date: {selected_date.strftime('%Y-%m-%d')}", price_title_style)
    story.append(combined_price_title)
    
    # Get all vegetables from the data
    all_veg_data = []
    veg_unit_combinations = df[['PIVOT_VEGETABLE_NAME', 'UNITS', 'TELUGU NAME']].drop_duplicates()
    
    for _, row in veg_unit_combinations.iterrows():
        veg_name = row['PIVOT_VEGETABLE_NAME']
        units = row['UNITS']
        telugu_name = row['TELUGU NAME']
        
        # Create display name that includes units if there are multiple unit types for same vegetable
        veg_units_count = df[df['PIVOT_VEGETABLE_NAME'] == veg_name]['UNITS'].nunique()
        if veg_units_count > 1:
            display_name = f"{veg_name} ({units})"
        else:
            display_name = veg_name
        
        # Calculate total quantity for this vegetable-unit combination across all hotels
        total_qty = df[(df['PIVOT_VEGETABLE_NAME'] == veg_name) & (df['UNITS'] == units)]['QUANTITY'].sum()
        
        all_veg_data.append([
            display_name,
            telugu_name if telugu_name and str(telugu_name) != 'nan' else '',
            units,
            f"{total_qty:.2f}",  # Total quantity column
            ""  # Empty actual price column for manual entry
        ])
    
    # Sort alphabetically by vegetable name
    all_veg_data.sort(key=lambda x: x[0])
    
    if all_veg_data:
        # Create table
        price_table_data = [['Vegetable Name', 'Telugu Name', 'Units', 'Total Quantity', 'Actual Price']]
        price_table_data.extend(all_veg_data)
        
        # Calculate column widths for price table - adjusted to fit more content
        col_widths = [1.6*inch, 1.6*inch, 0.7*inch, 1.0*inch, 1.6*inch]
        
        # Adjust font size based on number of items to fit on one page
        font_size = 10
        
        price_table = Table(price_table_data, colWidths=col_widths)
        price_table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),  # Smaller header
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),  # Reduced padding
            
            # Data rows styling
            ('FONTNAME', (1, 1), (1, -1), 'NotoSansTelugu'),  # Telugu column
            ('FONTSIZE', (0, 1), (-1, -1), font_size),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),  # Minimal padding
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),  # Minimal padding
            ('TOPPADDING', (0, 0), (-1, -1), 1),  # Minimal padding
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),  # Minimal padding
        ]))
        
        story.append(price_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
