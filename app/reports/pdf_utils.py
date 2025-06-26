from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import pandas as pd

# Register Telugu font
pdfmetrics.registerFont(TTFont('NotoSansTelugu', './NotoSansTelugu.ttf'))

def create_title_style():
    """Create title style for PDF reports"""
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    return title_style

def create_section_title_style():
    """Create section title style for PDF reports"""
    styles = getSampleStyleSheet()
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'], 
        fontSize=14,
        spaceAfter=20,
        spaceBefore=10,
        alignment=1,
        textColor=colors.darkblue
    )
    return section_title

def create_hotel_title_style():
    """Create hotel title style for PDF reports"""
    styles = getSampleStyleSheet()
    hotel_title_style = ParagraphStyle(
        'HotelTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        spaceBefore=10,
        alignment=1,
        textColor=colors.darkblue
    )
    return hotel_title_style

def create_date_style():
    """Create date style for PDF reports"""
    styles = getSampleStyleSheet()
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=20,
        alignment=1,
        textColor=colors.grey
    )
    return date_style

def create_summary_style():
    """Create summary style for PDF reports"""
    styles = getSampleStyleSheet()
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=11,
        alignment=1,
        textColor=colors.darkgreen
    )
    return summary_style

def create_vendor_title_style():
    """Create vendor title style for PDF reports"""
    styles = getSampleStyleSheet()
    vendor_title_style = ParagraphStyle(
        'VendorTitle',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=15,
        spaceBefore=10,
        textColor=colors.darkgreen
    )
    return vendor_title_style

def create_no_data_style():
    """Create no data style for PDF reports"""
    styles = getSampleStyleSheet()
    no_data_style = ParagraphStyle(
        'NoData',
        parent=styles['Normal'],
        fontSize=14,
        alignment=1,
        textColor=colors.red
    )
    return no_data_style
