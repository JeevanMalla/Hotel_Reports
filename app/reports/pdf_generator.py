"""
Main PDF generator module that imports and re-exports functions from other PDF modules.
This is a compatibility layer for code that might still import from pdf_generator directly.
"""

from .individual_reports import create_individual_hotel_reports_pdf
from .combined_reports import create_combined_report_pdf

# Re-export the functions for backward compatibility
__all__ = ['create_individual_hotel_reports_pdf', 'create_combined_report_pdf']
