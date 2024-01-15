import streamlit as st
import uuid
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import pandas as pd

from c12_attribute_updator import JsonSearcher, PayloadUpdater

# Assuming necessary imports are done

# Use a service account
cred = credentials.Certificate('DBkey.json')

# Check if the app is already initialized to avoid ValueError
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Fetch the document only if 'payload' is not already in the session state
if 'payload' not in st.session_state:
    doc_ref = db.collection('payload').document("payload_aml-json_merged_views")
    doc = doc_ref.get()
    if doc.exists:
        st.session_state['payload'] = doc.to_dict()
    else:
        print('No such document!')
        st.session_state['payload'] = None

selected_view = st.text_input('Selected View', '5320f744-f942-4137-85ca-048feed11e16')

# Fetch attributes using the JsonSearcher class
searcher_instance = JsonSearcher(json.dumps(st.session_state['payload'], indent=4), selected_view)
attributes = searcher_instance.find_attributes()

# Convert the attributes to a DataFrame for Streamlit's data editor
df = pd.DataFrame(attributes)
edited_df = st.data_editor(df, num_rows="dynamic")

# Button to trigger the update
update_button = st.button('Update attributes')

if update_button:
    # Convert the edited DataFrame back to a list of dictionaries
    new_attributes = edited_df.to_dict(orient='records')
    
    try:
        # Use the cached payload from st.session_state
        updater = PayloadUpdater(st.session_state['payload'], selected_view, new_attributes)
        update_status = updater.update_payload()
        
        # Update Firestore with the modified payload
        db.collection('payload').document('payload_aml-json_merged_views').set(st.session_state['payload'])
        st.write(update_status)
    except ValueError as e:
        st.write(f"Error: {str(e)}")
