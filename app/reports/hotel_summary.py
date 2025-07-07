import io
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import streamlit as st

def create_hotel_summary_pdf(df, selected_date, hotel_name):
    """
    Generate a PDF with a simple table showing date, hotel name, and total amount
    for a specific hotel on a specific date.
    
    Args:
        df: DataFrame containing the data
        selected_date: Date for which to generate the summary
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
    
    # Calculate total amount
    total_amount = 0
    
    # Check if PRICE column exists
    if 'PRICE' in hotel_data.columns:
        # Calculate total amount for each vegetable and sum
        for _, row in hotel_data.iterrows():
            try:
                price = float(row['PRICE']) if pd.notna(row['PRICE']) else 0
                quantity = float(row['QUANTITY']) if pd.notna(row['QUANTITY']) else 0
                total_amount += price * quantity
            except (ValueError, TypeError):
                pass
    
    # Format date as string
    date_str = selected_date.strftime('%Y-%m-%d')
    
    # Create table data
    table_data = [
        ['Date', 'Hotel', 'Total Amount'],
        [date_str, hotel_name, f"{total_amount:.2f}"]
    ]
    
    # Create table
    col_widths = [1.5*inch, 2.5*inch, 2*inch]
    table = Table(table_data, colWidths=col_widths)
    
    # Style the table
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Data row styling
        ('FONTSIZE', (0, 1), (-1, 1), 11),
        ('BACKGROUND', (0, 1), (-1, 1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    story.append(table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
