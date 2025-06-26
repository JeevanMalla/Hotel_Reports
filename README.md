# Hotel Order Management System

A Streamlit application for managing hotel vegetable orders with MongoDB integration, Google Sheets data import, and PDF report generation.

## Features

- **Password Protected Access**: Secure access to the application
- **Google Sheets Integration**: Import data from Google Sheets
- **MongoDB Integration**: Store and retrieve vegetable orders and prices
- **PDF Report Generation**:
  - Combined summary reports with vegetable-wise and vendor-wise data
  - Individual hotel reports (one hotel per page) with Telugu vegetable names
  - Price management page with actual price column
- **Modular Code Structure**: Well-organized codebase for better maintainability

## Project Structure

```
deploy_hotel/
├── app/
│   ├── main.py                # Main Streamlit application
│   ├── database/
│   │   ├── __init__.py        # Database module exports
│   │   └── mongodb.py         # MongoDB connection and operations
│   ├── reports/
│   │   ├── __init__.py        # Reports module exports
│   │   ├── combined_reports.py # Combined PDF report generation
│   │   ├── individual_reports.py # Individual hotel PDF reports
│   │   └── pdf_utils.py       # PDF utilities and styles
│   └── utils/
│       ├── __init__.py        # Utils module exports
│       ├── data_processing.py # Data processing functions
│       └── sheets.py          # Google Sheets integration
├── NotoSansTelugu.ttf         # Telugu font for PDF generation
└── new_pivot_hotel.py         # Original application file (legacy)
```

## Setup

1. Install required dependencies:
   ```
   pip install streamlit pandas google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client reportlab pymongo
   ```

2. Set up Streamlit secrets:
   - Create a `.streamlit/secrets.toml` file with:
   ```toml
   [general]
   app_password = "your_app_password"

   [gcp_service_account]
   type = "service_account"
   project_id = "your_project_id"
   private_key_id = "your_private_key_id"
   private_key = "your_private_key"
   client_email = "your_client_email"
   client_id = "your_client_id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "your_client_cert_url"

   [mongodb]
   connection_string = "your_mongodb_connection_string"
   ```

3. Run the application:
   ```
   cd deploy_hotel
   streamlit run app/main.py
   ```

## Usage

1. **Home Page**:
   - Select a date and generate reports
   - Push data to MongoDB
   - Download PDF reports

2. **Data Preview**:
   - View raw data from Google Sheets
   - See basic statistics

3. **Price Management**:
   - Enter actual prices for vegetables
   - Save prices to MongoDB

## Notes

- Telugu text requires the NotoSansTelugu.ttf font to be present in the project directory
- Individual hotel reports are designed to fit exactly one page per hotel
- The price management page allows for entering actual prices that are stored in MongoDB
