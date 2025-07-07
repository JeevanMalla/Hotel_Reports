import io
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import streamlit as st

def create_hotel_summary_pdf(df, date_range, hotel_name):
    """
    Generate a PDF with a table showing date and total amount for each date in the range
    for a specific hotel, with a grand total at the bottom.
    
    Args:
        df: DataFrame containing the data
        date_range: Tuple of (start_date, end_date) or single date
        hotel_name: Name of the hotel to generate summary for
        
    Returns:
        BytesIO buffer containing the PDF
    """
    if df.empty:
        return None
    
    # Filter data for the specific hotel
    hotel_data = df[df['MAIN HOTEL NAME'] == hotel_name]
    
    if hotel_data.empty:
        return None
    
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Define styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=1,  # Center alignment
        spaceAfter=20,
        spaceBefore=10,
        textColor=colors.darkblue
    )
    
    # Add title
    title = Paragraph(f"Hotel Summary - {hotel_name}", title_style)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Determine date range
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range
    
    # Convert to datetime for filtering
    try:
        start_datetime = pd.Timestamp(start_date)
        end_datetime = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    except TypeError:
        return None
    
    # Create a list of all dates in the range
    date_list = pd.date_range(start=start_datetime.date(), end=end_datetime.date())
    
    # Create table data
    table_data = [['Date', 'Total Amount']]
    grand_total = 0
    
    # Process each date
    for date in date_list:
        # Filter data for this date
        date_data = hotel_data[hotel_data['DATE'].dt.date == date.date()]
        
        # Calculate total amount for this date
        date_total = 0
        
        # Check if PRICE column exists
        if 'PRICE' in date_data.columns:
            # Calculate total amount for each vegetable and sum
            for _, row in date_data.iterrows():
                try:
                    price = float(row['PRICE']) if pd.notna(row['PRICE']) else 0
                    quantity = float(row['QUANTITY']) if pd.notna(row['QUANTITY']) else 0
                    date_total += price * quantity
                except (ValueError, TypeError):
                    pass
        
        # Add to grand total
        grand_total += date_total
        
        # Add row to table
        table_data.append([date.strftime('%Y-%m-%d'), f"{date_total:.2f}"])
    
    # Add grand total row
    table_data.append(['Grand Total', f"{grand_total:.2f}"])
    
    # Create table
    col_widths = [2.5*inch, 2.5*inch]
    table = Table(table_data, colWidths=col_widths)
    
    # Style the table
    table_style = [
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Data rows styling
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Grand total row styling
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]
    
    # Add alternating row colors
    for i in range(1, len(table_data) - 1):
        if i % 2 == 0:
            table_style.append(('BACKGROUND', (0, i), (-1, i), colors.white))
    
    table.setStyle(TableStyle(table_style))
    
    story.append(table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
