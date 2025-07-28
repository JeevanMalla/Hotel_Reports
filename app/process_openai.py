import streamlit as st
import base64
import json
from openai_integration import process_images_via_openai, transcribe_audio, parse_voice_input

def process_images_and_text_via_openai(images_data, text_message, hotel_name):
    """
    Process images and text using OpenAI's API
    
    Args:
        images_data: List of base64 encoded image strings
        text_message: Additional text instructions
        hotel_name: Name of the hotel
        
    Returns:
        List of extracted items
    """
    try:
        from img_to_txt_module import get_vegetable_names_by_hotel, parse_llm_response
        
        vegetable_names = get_vegetable_names_by_hotel(hotel_name)
        if not vegetable_names:
            st.error(f"❌ No vegetables found for hotel {hotel_name}. Please check your database.")
            return []
            
        st.info("🤖 Calling OpenAI API...")
        response_text = process_images_via_openai(images_data, text_message, vegetable_names, hotel_name)
        st.session_state.response_text = response_text
        
        with st.expander("🔍 View Raw LLM Response"):
            st.code(response_text)
            
        return parse_llm_response(response_text, vegetable_names, hotel_name)
    except Exception as e:
        st.error(f"❌ Error in OpenAI API call: {e}")
        st.exception(e)
        return []

def update_vegetable_data_with_voice(edited_df, transcription_text):
    """
    Update vegetable data based on voice input
    
    Args:
        edited_df: DataFrame containing the current vegetable data
        transcription_text: Transcribed text from voice input
        
    Returns:
        Updated DataFrame
    """
    try:
        # Parse the transcription to extract vegetable name and quantity
        parsed_data = parse_voice_input(transcription_text)
        
        if not parsed_data.get('vegetable_name') or not parsed_data.get('quantity'):
            st.warning("⚠️ Could not extract vegetable name or quantity from voice input.")
            return edited_df
            
        vegetable_name = parsed_data['vegetable_name'].upper()
        quantity = float(parsed_data['quantity'])
        
        # Check if vegetable exists in the DataFrame
        vegetable_exists = False
        for i, row in edited_df.iterrows():
            if row['PIVOT_VEGETABLE_NAME'].upper() == vegetable_name:
                # Update existing vegetable
                edited_df.at[i, 'QUANTITY'] = quantity
                vegetable_exists = True
                st.success(f"✅ Updated {vegetable_name} quantity to {quantity}")
                break
                
        # If vegetable doesn't exist, add it
        if not vegetable_exists:
            new_row = {
                'DATE': edited_df['DATE'].iloc[0] if not edited_df.empty else None,
                'MAIN_HOTEL_NAME': edited_df['MAIN_HOTEL_NAME'].iloc[0] if not edited_df.empty else None,
                'KITCHEN_NAME': edited_df['KITCHEN_NAME'].iloc[0] if not edited_df.empty else None,
                'PIVOT_VEGETABLE_NAME': vegetable_name,
                'QUANTITY': quantity
            }
            edited_df = edited_df.append(new_row, ignore_index=True)
            st.success(f"✅ Added {vegetable_name} with quantity {quantity}")
            
        return edited_df
    except Exception as e:
        st.error(f"❌ Error updating vegetable data: {e}")
        return edited_df
