import base64
import os
from openai import OpenAI
import streamlit as st
from typing import List, Dict, Any, Optional

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets.get("openai", {}).get("api_key", ""))

def encode_image(image_bytes):
    """
    Encode image bytes to base64 string
    """
    return base64.b64encode(image_bytes).decode('utf-8')

def process_images_via_openai(images_data: List[str], text_message: str, vegetable_names: List[str], hotel_name: str) -> str:
    """
    Process images using OpenAI's GPT-4 Vision API
    
    Args:
        images_data: List of base64 encoded image strings
        text_message: Additional text instructions
        vegetable_names: List of valid vegetable names
        hotel_name: Name of the hotel
        
    Returns:
        Raw response from OpenAI
    """
    try:
        vegetable_list_str = "\n".join(vegetable_names)
        example_format = '[{"item_name": "TOMATOES", "quantity": 5, "units": "KGS"}, {"item_name": "ONIONS", "quantity": 3, "units": "KGS"}]'
        
        # Create the system message
        base_prompt = f"""You are a grocery order processing assistant. Analyze the provided images AND text instructions to extract grocery items with their quantities.

Each item should have the following properties:
- item_name: the name of the grocery item (must match one from the list below)
- quantity: a number representing how many units to purchase
- units: the unit of measurement (e.g., "KGS", "PCS", "LITERS", etc.)

Available vegetable names for {hotel_name}:
{vegetable_list_str}

IMPORTANT INSTRUCTIONS:
1. Analyze ALL provided images carefully for any grocery items, quantities, or order details
2. Also consider the text message below for additional items or instructions
3. Combine information from BOTH images and text to create a complete order
4. If the same item appears in both image and text, use the higher quantity or combine them logically
5. Extract items even if they're handwritten, in lists, or mentioned in conversation

Text Instructions: "{text_message}"

Return ONLY a valid JSON array with no additional text, explanations, or formatting.
Example format: {example_format}

Extract items from BOTH the images and text message above."""

        # Prepare the messages
        content = [{"type": "text", "text": base_prompt}]
        
        # Add images to the content
        for image_data in images_data:
            content.append({
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{image_data}"
            })
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",  # Using GPT-4 Vision model
            messages=[
                {"role": "user", "content": content}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"❌ Error in OpenAI API call: {e}")
        raise e

def transcribe_audio(audio_file) -> str:
    """
    Transcribe audio file using OpenAI's Whisper API
    
    Args:
        audio_file: Audio file object
        
    Returns:
        Transcribed text
    """
    try:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
        return transcription.text
    except Exception as e:
        st.error(f"❌ Error in OpenAI Audio Transcription API call: {e}")
        raise e

def parse_voice_input(transcription: str) -> Dict[str, Any]:
    """
    Parse voice input to extract vegetable name and weight
    
    Args:
        transcription: Transcribed text from voice input
        
    Returns:
        Dictionary with vegetable name and quantity
    """
    try:
        # Use OpenAI to parse the transcription
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts vegetable names and quantities from text. Extract ONLY the vegetable name and quantity. Return the result as a JSON object with keys 'vegetable_name' and 'quantity'."},
                {"role": "user", "content": f"Extract the vegetable name and quantity from this text: '{transcription}'"}
            ],
            temperature=0.1
        )
        
        # Parse the response
        import json
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        st.error(f"❌ Error parsing voice input: {e}")
        return {"vegetable_name": "", "quantity": 0}
