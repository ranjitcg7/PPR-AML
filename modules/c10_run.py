import streamlit as st
import uuid
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

from c10_transformer_xml_2_to_json1 import XMLtoJSONConverter_2



### firestore database 
# Use a service account
cred = credentials.Certificate('DBkey.json')
  
# check if the app is already initialized to avoid ValueError: The default Firebase app already exists.
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()


# Fetch the document
doc_ref = db.collection('utils').document("SUC_Library")
doc = doc_ref.get()

# If the document exists, store its data as 'payload'
if doc.exists:
    SUC_Library = doc.to_dict()
else:
    print('No such document!')
    SUC_Library = None


# Upload different views/ files
uploaded_files = st.file_uploader("Upload files", accept_multiple_files=True)

xml_files = []

# Loop through all uploaded files
for uploaded_file in uploaded_files:
    # Check the file type and add it to the appropriate list
    if uploaded_file.type == "text/xml" or uploaded_file.type == "application/octet-stream":
        xml_files.append(uploaded_file)

generate_json_button = st.button('Generate json file', type="primary", key="generate_json_button")


if generate_json_button :
    # Placeholder for XML processing logic
    for xml_file in xml_files:
        xml_content = xml_file.getvalue()
        
        # Example usage
        converter = XMLtoJSONConverter_2(SUC_Library)
        json_output = converter.convert(xml_content)
        
        json_string = json.dumps(json_output, indent=4)
        
        st.download_button("Download converted JSON File", file_name="mini_payload_xml.json", mime="application/json", data=json_string, use_container_width=True)

        st.success(f"Processed XML (AML) File: {xml_file.name}")