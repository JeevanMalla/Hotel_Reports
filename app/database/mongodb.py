import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

def get_mongodb_connection():
    """Get MongoDB connection"""
    try:
        # Use st.secrets for MongoDB connection string
        if "mongodb" in st.secrets:
            connection_string = st.secrets.mongodb.connection_string
        else:
            # Default local connection for development
            connection_string = ""
            
        client = MongoClient(connection_string)
        # Ping the server to check connection
        client.admin.command('ping')
        return client
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {str(e)}")
        return None

def push_data_to_mongodb(df, selected_date):
    """Push data from Google Sheets to MongoDB"""
    if df.empty:
        return False, "No data to push to MongoDB"
    
    try:
        client = get_mongodb_connection()
        if not client:
            return False, "Failed to connect to MongoDB"
        
        # Convert selected_date to string format for MongoDB
        date_str = selected_date.strftime('%Y-%m-%d')
        
        # Create or get database and collection
        db = client["hotel_orders"]
        collection = db["vegetable_orders"]
        
        # Process data for MongoDB
        from utils.data_processing import process_data_for_date
        filtered_df, _ = process_data_for_date(df, selected_date)
        if filtered_df.empty:
            return False, f"No data found for date: {date_str}"
        
        # Convert DataFrame to list of dictionaries for MongoDB
        records = filtered_df.to_dict('records')
        
        # Add timestamp and formatted date
        for record in records:
            record['timestamp'] = datetime.now()
            record['formatted_date'] = date_str
        
        # Delete existing records for this date to avoid duplicates
        collection.delete_many({"formatted_date": date_str})
        
        # Insert new records
        collection.insert_many(records)
        
        return True, f"Successfully pushed {len(records)} records to MongoDB"
        
    except Exception as e:
        return False, f"Error pushing data to MongoDB: {str(e)}"
    finally:
        if 'client' in locals() and client:
            client.close()

def get_vegetable_prices(selected_date):
    """Get vegetable prices from MongoDB"""
    try:
        client = get_mongodb_connection()
        if not client:
            return pd.DataFrame()
        
        # Convert selected_date to string format for MongoDB
        date_str = selected_date.strftime('%Y-%m-%d')
        
        # Get database and collection
        db = client["hotel_orders"]
        prices_collection = db["vegetable_prices"]
        
        # Get prices for the selected date
        prices = list(prices_collection.find({"date": date_str}))
        
        if not prices:
            return pd.DataFrame()
            
        # Convert to DataFrame
        prices_df = pd.DataFrame(prices)
        if '_id' in prices_df.columns:
            prices_df = prices_df.drop('_id', axis=1)
            
        return prices_df
        
    except Exception as e:
        st.error(f"Error fetching vegetable prices from MongoDB: {str(e)}")
        return pd.DataFrame()
    finally:
        if 'client' in locals() and client:
            client.close()

def save_vegetable_prices(prices_data, selected_date):
    """Save vegetable prices to MongoDB"""
    if not prices_data:
        return False, "No price data to save"
    
    try:
        client = get_mongodb_connection()
        if not client:
            return False, "Failed to connect to MongoDB"
        
        # Convert selected_date to string format for MongoDB
        date_str = selected_date.strftime('%Y-%m-%d')
        
        # Create or get database and collection
        db = client["hotel_orders"]
        prices_collection = db["vegetable_prices"]
        
        # Add date to each record
        for item in prices_data:
            item['date'] = date_str
            item['timestamp'] = datetime.now()
        
        # Delete existing prices for this date
        prices_collection.delete_many({"date": date_str})
        
        # Insert new prices
        prices_collection.insert_many(prices_data)
        
        return True, f"Successfully saved {len(prices_data)} price records to MongoDB"
        
    except Exception as e:
        return False, f"Error saving vegetable prices to MongoDB: {str(e)}"
    finally:
        if 'client' in locals() and client:
            client.close()
