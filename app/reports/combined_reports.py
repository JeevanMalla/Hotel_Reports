import io
import pandas as pd
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
import streamlit as st

from .pdf_utils import (
    create_title_style,
    create_section_title_style,
    create_vendor_title_style
)

def create_combined_report_pdf(veg_data, vendor_data, selected_date):
    """Generate SINGLE PDF containing both vegetable and vendor reports with Telugu support"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Main title
    title_style = create_title_style()
    #title = Paragraph(f"Complete Order Summary Report - {selected_date.strftime('%Y-%m-%d')}", title_style)
    #story.append(title)
    story.append(selected_date.strftime('%d-%m-%Y'),title_style)
    
    # SECTION 1: VEGETABLE-WISE SUMMARY
    section1_title = create_section_title_style()
    #story.append(Paragraph("SECTION 1: VEGETABLE-WISE ORDER SUMMARY", section1_title))
    #story.append(Spacer(1, 10))
    
    if veg_data.empty:
        story.append(Paragraph("No vegetable data available for the selected date.", styles['Normal']))
    else:
        # Create table data - handle Telugu text encoding
        table_data = []
        headers = veg_data.columns.tolist()
        table_data.append(headers)
        
        for _, row in veg_data.iterrows():
            row_data = []
            for col in headers:
                cell_value = str(row[col]) if row[col] is not None else ""
                # Handle Telugu text - ensure proper encoding
                if col == 'Telugu Name':
                    try:
                        if cell_value and cell_value != 'nan':
                            cell_value = cell_value.encode('utf-8').decode('utf-8')
                        else:
                            cell_value = ""
                    except:
                        cell_value = ""
                row_data.append(cell_value)
            table_data.append(row_data)
        
        # Create table with adjusted column widths
        available_width = 14.5 * inch  # A4 width minus margins
        num_cols = len(headers)
        if num_cols <= 4:
            col_widths = [available_width/num_cols] * num_cols
        else:
            # Adjust widths for better display
            col_widths = [1.8*inch, 1.2*inch] + [1*inch] * (num_cols - 2)
            if sum(col_widths) > available_width:
                col_widths = [available_width/num_cols] * num_cols
        
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (1, 1), (1, -1), 'NotoSansTelugu'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),  # Header row font size
            ('FONTSIZE', (0, 1), (-1, -1), 10),  # Data rows font size
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table)
    
    # Page break before vendor section
    story.append(PageBreak())
    
    # SECTION 2: VENDOR-WISE SUMMARY
    story.append(Paragraph("SECTION 2: VENDOR-WISE ORDER SUMMARY", section1_title))
    story.append(Spacer(1, 20))
    
    if not vendor_data:
        story.append(Paragraph("No vendor data available for the selected date.", styles['Normal']))
    else:
        vendor_names = list(vendor_data.keys())
        for i, (vendor_name, data) in enumerate(vendor_data.items()):
            if i > 0:
                story.append(PageBreak())
            
            # Vendor title
            vendor_title_style = create_vendor_title_style()
            vendor_title = Paragraph(f"Vendor: {vendor_name}", vendor_title_style)
            story.append(vendor_title)
            
            # Create table data - handle Telugu text encoding
            table_data = []
            headers = data.columns.tolist()
            table_data.append(headers)
            
            for _, row in data.iterrows():
                row_data = []
                for col in headers:
                    cell_value = str(row[col]) if row[col] is not None else ""
                    # Handle Telugu text - ensure proper encoding
                    if col == 'Telugu Name':
                        try:
                            if cell_value and cell_value != 'nan':
                                cell_value = cell_value.encode('utf-8').decode('utf-8')
                            else:
                                cell_value = ""
                        except:
                            cell_value = ""
                    row_data.append(cell_value)
                table_data.append(row_data)
            
            # Create table with adjusted column widths
            num_cols = len(headers)
            if num_cols <= 4:
                col_widths = [available_width/num_cols] * num_cols
            else:
                col_widths = [1.8*inch, 1.2*inch] + [0.9*inch] * (num_cols - 2)
                if sum(col_widths) > available_width:
                    col_widths = [available_width/num_cols] * num_cols
            
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (1, 1), (1, -1), 'NotoSansTelugu'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),  # Header row font size
                ('FONTSIZE', (0, 1), (-1, -1), 10),  # Data rows font size
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
