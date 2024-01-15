from R_aml_json_converter import convert_aml_to_json
import streamlit as st
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser
from aml_base import Caexfile
import json

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

### firestore database 
# Use a service account
cred = credentials.Certificate('DBkey.json')
  
# check if the app is already initialized to avoid ValueError: The default Firebase app already exists.
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
# ... other Streamlit code here ...

# ... other code ...

uploaded_files = st.file_uploader("Upload AML file", accept_multiple_files=True)
uploaded_file_names = []
for uploaded_file in uploaded_files:
    file_extension = uploaded_file.name.split('.')[-1]  # Get the file extension

    if file_extension == 'aml':
        bytes_data = uploaded_file.getvalue()

        context = XmlContext()
        parser = XmlParser(context=context)
        aml_object: Caexfile = parser.from_string(str(bytes_data, 'utf-8'), Caexfile)

        st.session_state["aml_object"] = aml_object
        st.session_state["file_name"] = uploaded_file.name[:-4]
        st.session_state["uploaded_file_size"] = uploaded_file.size / 1000

        indent = True
        indent_value = 4

        cleaned_json = convert_aml_to_json(st.session_state["aml_object"], indent_value)
        
        # byte_length: float = len(cleaned_json)
        # delta = ((byte_length/1000)/float(st.session_state['raw_data_size'])-1)*100
        # rounded_delta = round(delta, 2)
        
        # col1, col2, col3 = st.columns([2, 1, 1])
        # col1.metric("File name", st.session_state["file_name"])
        # col2.metric("Data format", ".json")
        # col3.metric("File size", f"{byte_length / 1000} KB", delta=f"{rounded_delta} % ", delta_color="inverse")

        # Add the file name to the list
        uploaded_file_names.append(uploaded_file.name)

        # convert string (in json format) to python dictionary
        data = json.loads(cleaned_json)
        doc_ref = db.collection('aml-json_files').document(uploaded_file.name)
        doc_ref.set(data)

    elif file_extension == 'json':
        st.write(f'The file {uploaded_file.name} is in JSON format.')
        file_bytes = uploaded_file.read()  # this is bytes

        # Add the file name to the list
        uploaded_file_names.append(uploaded_file.name)

        # convert bytes to string
        file_str = file_bytes.decode('utf-8')
        
        # convert string (in json format) to python dictionary
        data = json.loads(file_str)
        doc_ref = db.collection('aml-json_files').document(uploaded_file.name)
        doc_ref.set(data)

    else:
        st.write(f'The file {uploaded_file.name} has an unrecognized format: .{file_extension}')


st.write(uploaded_file_names)
