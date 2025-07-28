import os
import json
import tempfile
from groq import Groq
import streamlit as st

# Initialize the Groq client
client = Groq(api_key=st.secrets.api_key.groq)

def transcribe_audio(audio_file):
    """
    Transcribe audio using Groq's Whisper API
    
    Args:
        audio_file: Audio file object
        
    Returns:
        Transcribed text
    """
    try:
        # Create a transcription of the audio file
        transcription = client.audio.transcriptions.create(
            file=audio_file,  # Required audio file
            model="whisper-large-v3-turbo",  # Required model to use for transcription
            response_format="text",  # Get simple text response
            language="en",  # Optional
            temperature=0.0  # Optional
        )
        
        return transcription.text
    except Exception as e:
        st.error(f"❌ Error in Groq Whisper API call: {e}")
        raise e

def parse_voice_input(transcription_text):
    """
    Parse voice input to extract vegetable name and weight using Groq LLM
    
    Args:
        transcription_text: Transcribed text from voice input
        
    Returns:
        Dictionary with vegetable name and quantity
    """
    try:
        # Use Groq to parse the transcription
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts vegetable names and quantities from text. Extract ONLY the vegetable name and quantity. Return the result as a JSON object with keys 'vegetable_name' and 'quantity'."},
                {"role": "user", "content": f"Extract the vegetable name and quantity from this text: '{transcription_text}'"}
            ],
            temperature=0.1,
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
        
        # Parse the response
        response_text = response.choices[0].message.content
        
        # Clean up the response to get valid JSON
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()
            
        import json
        result = json.loads(response_text)
        return result
    except Exception as e:
        st.error(f"❌ Error parsing voice input: {e}")
        return {"vegetable_name": "", "quantity": 0}

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
