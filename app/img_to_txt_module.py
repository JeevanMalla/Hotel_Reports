import streamlit as st
import pandas as pd
import datetime
import base64
import json
from pymongo import MongoClient
from groq import Groq
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ---------- GOOGLE SHEETS CONFIGURATION ----------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = st.secrets.general.id
SHEET_NAMES = ['Sheet16']

def get_sheets_service():
    creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def append_to_google_sheets_batch(data_df, sheet_name='Sheet16'):
    try:
        service = get_sheets_service()
        # Get the current sheet data to find the last row
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{sheet_name}!A:A"
            ).execute()
            existing_values = result.get('values', [])
            last_row = len(existing_values) if existing_values else 0
        except Exception:
            last_row = 0
        values_to_append = []
        if last_row == 0:
            values_to_append.append(data_df.columns.tolist())
            last_row = 1
        for _, row in data_df.iterrows():
            values_to_append.append(row.tolist())
        body = {'values': values_to_append}
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A:A",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        updates = result.get('updates', {})
        rows_added = len(values_to_append)
        return True, f"Successfully appended {rows_added} rows to Google Sheets. Updated range: {updates.get('updatedRange', 'Unknown')}"
    except Exception as e:
        return False, f"Error appending to Google Sheets: {str(e)}"

# ---------- MONGODB SETUP ----------
client = MongoClient(st.secrets['mongodb']['connection_string'])
db = client["hotel_orders"]

def get_vegetable_names_by_hotel(hotel_name):
    try:
        master_veg_collection = db["master_veg_name"]
        vegetable_docs = master_veg_collection.find({"HOTEL_NAME": hotel_name.upper()})
        vegetable_list = [doc.get("HOTEL_SPECIFIC_NAME", "") for doc in vegetable_docs]
        return vegetable_list
    except Exception as e:
        st.error(f"Error fetching vegetable names: {e}")
        return []

def get_vegetable_mapping_by_hotel(hotel_name):
    try:
        master_veg_collection = db["master_veg_name"]
        vegetable_docs = master_veg_collection.find({"HOTEL_NAME": hotel_name.upper()})
        vegetable_mapping = {}
        for doc in vegetable_docs:
            hotel_specific = doc.get("HOTEL_SPECIFIC_NAME", "")
            common_name = doc.get("COMMON_NAME", "")
            if hotel_specific and common_name:
                vegetable_mapping[hotel_specific.upper()] = common_name
        return vegetable_mapping
    except Exception as e:
        st.error(f"Error fetching vegetable mapping: {e}")
        return {}

def get_common_vegetable_name(hotel_specific_name, vegetable_mapping):
    if not hotel_specific_name or not vegetable_mapping:
        return hotel_specific_name
    hotel_specific_upper = hotel_specific_name.upper()
    if hotel_specific_upper in vegetable_mapping:
        return vegetable_mapping[hotel_specific_upper]
    for hotel_name, common_name in vegetable_mapping.items():
        if hotel_specific_upper in hotel_name or hotel_name in hotel_specific_upper:
            return common_name
    return hotel_specific_name

def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def process_images_and_text_via_groq(images_data, text_message, hotel_name):
    try:
        client_groq = Groq(api_key=st.secrets.api_key.groq)
        vegetable_names = get_vegetable_names_by_hotel(hotel_name)
        if not vegetable_names:
            st.error(f"❌ No vegetables found for hotel {hotel_name}. Please check your database.")
            return []
        vegetable_list_str = "\n".join(vegetable_names)
        example_format = '[{"item_name": "TOMATOES", "quantity": 5, "units": "KGS"}, {"item_name": "ONIONS", "quantity": 3, "units": "KGS"}]'
        base_prompt = f"""You are a grocery order processing assistant. Analyze the provided images AND text instructions to extract grocery items with their quantities.\n\nEach item should have the following properties:\n- item_name: the name of the grocery item (must match one from the list below)\n- quantity: a number representing how many units to purchase\n- units: the unit of measurement (e.g., \"KGS\", \"PCS\", \"LITERS\", etc.)\n\nAvailable vegetable names for {hotel_name}:\n{vegetable_list_str}\n\nIMPORTANT INSTRUCTIONS:\n1. Analyze ALL provided images carefully for any grocery items, quantities, or order details\n2. Also consider the text message below for additional items or instructions\n3. Combine information from BOTH images and text to create a complete order\n4. If the same item appears in both image and text, use the higher quantity or combine them logically\n5. Extract items even if they're handwritten, in lists, or mentioned in conversation\n\nText Instructions: \"{text_message}\"\n\nReturn ONLY a valid JSON array with no additional text, explanations, or formatting.\nExample format: {example_format}\n\nExtract items from BOTH the images and text message above."""
        message_content = [{"type": "text", "text": base_prompt}]
        if images_data:
            for image_data in images_data:
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                })
            st.info(f"🖼️ Processing {len(images_data)} images + text message")
        else:
            st.info("📝 Processing text message only")
        st.info("🤖 Calling Groq API...")
        chat_completion = client_groq.chat.completions.create(
            messages=[{"role": "user", "content": message_content}],
            temperature=0.1,
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
        st.session_state.response_text = chat_completion.choices[0].message.content
        with st.expander("🔍 View Raw LLM Response"):
            st.code(st.session_state.response_text)
        return parse_llm_response(st.session_state.response_text, vegetable_names, hotel_name)
    except Exception as e:
        st.error(f"❌ Error in Groq API call: {e}")
        st.exception(e)
        return []

def parse_llm_response(response_text, vegetable_names, hotel_name):
    try:
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()
        start_bracket = response_text.find('[')
        end_bracket = response_text.rfind(']')
        if start_bracket != -1 and end_bracket != -1:
            response_text = response_text[start_bracket:end_bracket + 1]
        items_data = json.loads(response_text)
        if not isinstance(items_data, list):
            st.error("❌ LLM response is not a valid JSON array")
            return []
        vegetable_mapping = get_vegetable_mapping_by_hotel(hotel_name)
        items_extracted = []
        for i, item in enumerate(items_data):
            try:
                if not isinstance(item, dict):
                    st.warning(f"⚠️ Item {i+1} is not a valid object, skipping...")
                    continue
                required_keys = ["item_name", "quantity", "units"]
                missing_keys = [key for key in required_keys if key not in item]
                if missing_keys:
                    st.warning(f"⚠️ Item {i+1} missing keys: {missing_keys}, skipping...")
                    continue
                matched_name = None
                item_name = str(item["item_name"]).strip()
                for veg_name in vegetable_names:
                    if item_name.upper() == veg_name.upper():
                        matched_name = veg_name
                        break
                if not matched_name:
                    for veg_name in vegetable_names:
                        if item_name.upper() in veg_name.upper() or veg_name.upper() in item_name.upper():
                            matched_name = veg_name
                            st.info(f"🔄 Partial match found: '{item_name}' → '{veg_name}'")
                            break
                try:
                    quantity = float(item["quantity"])
                    if quantity <= 0:
                        st.warning(f"⚠️ Invalid quantity {quantity} for {item_name}, skipping...")
                        continue
                except (ValueError, TypeError):
                    st.warning(f"⚠️ Invalid quantity '{item['quantity']}' for {item_name}, skipping...")
                    continue
                final_item_name = matched_name or item_name
                common_name = get_common_vegetable_name(final_item_name, vegetable_mapping)
                final_item = {
                    "item_name": final_item_name,
                    "common_name": common_name,
                    "quantity": quantity,
                    "units": str(item["units"]).strip()
                }
                items_extracted.append(final_item)
                if not matched_name:
                    st.warning(f"⚠️ Vegetable '{item_name}' not found in database for {hotel_name}")
            except Exception as item_error:
                st.warning(f"⚠️ Error processing item {i+1}: {item_error}")
                continue
        st.success(f"✅ Successfully parsed {len(items_extracted)} valid items from LLM response")
        return items_extracted
    except json.JSONDecodeError as e:
        st.error(f"❌ Invalid JSON response from LLM: {e}")
        st.text("Raw response:")
        st.code(response_text)
        return []
    except Exception as e:
        st.error(f"❌ Error parsing LLM response: {e}")
        st.exception(e)
        return []

def build_dataframe_from_items(items_extracted, date_input, hotel_name, kitchen_name):
    rows_for_df = []
    for item in items_extracted:
        rows_for_df.append({
            "DATE": date_input.strftime("%Y-%m-%d"),
            "MAIN_HOTEL_NAME": hotel_name,
            "KITCHEN_NAME": kitchen_name,
            "PIVOT_VEGETABLE_NAME": item.get("common_name", item.get("item_name", "")),
            "QUANTITY": item.get("quantity", 0)
        })
    return pd.DataFrame(rows_for_df)

def image_txt_to_order_ui():
    if 'response_text' not in st.session_state:
        st.session_state['response_text'] = 'value'
    if 'processed_items' not in st.session_state:
        st.session_state['processed_items'] = []
    st.title("🏨 Hotel Orders Processing System (Image/Text to Order)")
    col1, col2 = st.columns(2)
    with col1:
        date_input = st.date_input("Select Date", datetime.date.today() + datetime.timedelta(days=1))
        hotel_name = st.selectbox(
            'Hotel Name',
            ('NOVOTEL', 'GRANDBAY', 'RADISSONBLU', 'BHEEMILI')
        )
    with col2:
        kitchen_name = st.selectbox(
            'Kitchen Name',
            ('EATS', 'BANQUETS KITCHEN', 'STAFF CANTEEN', 'GRANDBAY', 'MAIN KITCHEN', 
             'ZAFFRAN KITCHEN', 'BHEEMILI NOVOTEL', 'BHEEMILI MAIN KITCHEN', 'INFINTY KITCHEN')
        )
    st.write(f'Selected Hotel: **{hotel_name}** | Kitchen: **{kitchen_name}**')
    st.subheader("📝 Text Instructions")
    text_message = st.text_area(
        "Enter grocery items and quantities (this will be combined with image analysis):",
        placeholder="e.g., 'Need 5kg tomatoes, 3kg onions, 2kg potatoes for tomorrow's event'",
        height=100
    )
    st.subheader("📸 Upload Images")
    uploaded_images = st.file_uploader(
        "Upload one or more images (optional - will be combined with text)", 
        type=["jpg", "jpeg", "png"], 
        accept_multiple_files=True
    )
    if uploaded_images:
        st.subheader(f"📋 {len(uploaded_images)} Image(s) Uploaded")
        cols = st.columns(min(len(uploaded_images), 4))
        for idx, uploaded_image in enumerate(uploaded_images):
            with cols[idx % 4]:
                st.image(uploaded_image, caption=f"Image {idx+1}", use_column_width=True)
    if st.button("🚀 Process Images + Text", type="primary", use_container_width=True):
        if not uploaded_images and not text_message.strip():
            st.error("Please upload at least one image OR provide text instructions.")
        elif not hotel_name:
            st.error("Please select a hotel name.")
        else:
            with st.spinner("Processing images and text with AI..."):
                try:
                    images_data = []
                    if uploaded_images:
                        for i, uploaded_image in enumerate(uploaded_images):
                            try:
                                uploaded_image.seek(0)
                                bytes_data = uploaded_image.read()
                                if len(bytes_data) == 0:
                                    st.warning(f"⚠️ Image {i+1} appears to be empty, skipping...")
                                    continue
                                image_encoded = encode_image(bytes_data)
                                images_data.append(image_encoded)
                                st.info(f"✅ Successfully processed image {i+1} ({len(bytes_data)} bytes)")
                            except Exception as img_error:
                                st.error(f"❌ Error processing image {i+1}: {img_error}")
                                continue
                    if images_data or text_message.strip():
                        st.info(f"🔄 Analyzing {len(images_data)} images + text instructions...")
                        items_extracted = process_images_and_text_via_groq(images_data, text_message, hotel_name)
                        if items_extracted:
                            st.session_state.processed_items = items_extracted
                            st.success(f"✅ Successfully extracted {len(items_extracted)} items from images + text!")
                        else:
                            st.warning("⚠️ No items were extracted. Please check your images and text.")
                    else:
                        st.error("❌ No valid images or text provided.")
                except Exception as e:
                    st.error(f"❌ Error during processing: {e}")
                    st.exception(e)
    if st.session_state.processed_items:
        st.subheader("📊 Review and Edit Extracted Data")
        df = build_dataframe_from_items(
            st.session_state.processed_items, 
            date_input, 
            hotel_name, 
            kitchen_name
        )
        # Get valid vegetable options for dropdown
        veg_options = get_vegetable_names_by_hotel(hotel_name)
        edit_df = df.copy().reset_index(drop=True)
        st.write("Edit the vegetable name and quantity below (directly in the table):")
        edited_df = st.data_editor(
            edit_df,
            column_config={
                "PIVOT_VEGETABLE_NAME": st.column_config.SelectboxColumn(
                    "Vegetable Name", options=veg_options, required=True
                ),
                "QUANTITY": st.column_config.NumberColumn("Quantity", min_value=0.0, required=True),
            },
            num_rows="dynamic",
            use_container_width=True
        )
        if st.button("Save Edits", key="imgtxt_save_edits"):
            st.session_state['imgtxt_edited_df'] = edited_df.copy()
            st.success("Edits saved. You can now export or download the updated data.")
        # Show the edited DataFrame
        st.subheader("📋 Final Data for Export (with Common Names)")
        st.dataframe(edited_df[['DATE', 'MAIN_HOTEL_NAME', 'KITCHEN_NAME', 'PIVOT_VEGETABLE_NAME', 'QUANTITY']], use_container_width=True)
        total_items = len(edited_df)
        total_quantity = edited_df['QUANTITY'].sum()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 Total Items", total_items)
        with col2:
            st.metric("⚖️ Total Quantity", f"{total_quantity:,.2f}")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📊 Export to MongoDB", use_container_width=True):
                try:
                    audit_collection = db["audits"]
                    records = edited_df[['DATE', 'MAIN_HOTEL_NAME', 'KITCHEN_NAME', 'PIVOT_VEGETABLE_NAME', 'QUANTITY']].to_dict("records")
                    audit_collection.insert_many(records)
                    st.success("✅ Data exported to MongoDB successfully!")
                except Exception as e:
                    st.error(f"❌ Failed to export to MongoDB: {e}")
        with col2:
            if st.button("📈 Export to Google Sheets", use_container_width=True):
                success, message = append_to_google_sheets_batch(edited_df[['DATE', 'MAIN_HOTEL_NAME', 'KITCHEN_NAME', 'PIVOT_VEGETABLE_NAME', 'QUANTITY']])
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
        with col3:
            csv = edited_df[['DATE', 'MAIN_HOTEL_NAME', 'KITCHEN_NAME', 'PIVOT_VEGETABLE_NAME', 'QUANTITY']].to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"hotel_orders_{date_input.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        if st.button("🗑️ Clear Data", type="secondary"):
            st.session_state.processed_items = []
            st.rerun()
    with st.expander("📈 Recent Orders"):
        try:
            audit_collection = db["audits"]
            recent_orders = list(audit_collection.find().sort("_id", -1).limit(10))
            if recent_orders:
                recent_df = pd.DataFrame(recent_orders)
                if '_id' in recent_df.columns:
                    recent_df = recent_df.drop('_id', axis=1)
                st.dataframe(recent_df, use_container_width=True)
            else:
                st.info("No recent orders found")
        except Exception as e:
            st.error(f"Error fetching recent orders: {e}") 