import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional, Set
import streamlit as st
# from pydantic import BaseModel, Field
from pydantic.color import Color
from PIL import Image
import json
import pandas as pd

from st_cytoscape import cytoscape
from streamlit_antd_components import antd_menu, MenuItem, MenuDivider, antd_tree, TreeItem
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_agraph.config import Config, ConfigBuilder
import subprocess
import streamlit_pydantic as sp
from st_ant_tree import st_ant_tree

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


from modules import c1_generates_PPR_IH, c2_IH_extractor, c3_views_generator, c4_views_extractor, c5_integrator_EA, c6_get_connections, c7_transformer_csv_to_json1, c8_transformer_json1_to_aml, c9_transformer_xml_1_to_json1, c10_transformer_xml_2_to_json1, c12_attribute_updator

# from c1_generates_PPR_IH import GenerateTrees
# from c2_IH_extractor import GetIH 
# from c3_views_generator import Generate_Views
# from c4_views_extractor import ExtractViews
# from c5_integrator_EA import IntegrateViews
# from c6_get_connections import GetConnections
# from c7_transformer_csv_to_json1 import ExcelToJSONConverter
# from c8_transformer_json1_to_aml import JSON_AML_transformer 
# from c9_transformer_xml_1_to_json1 import XMLtoJSONConverter
# from c10_transformer_xml_2_to_json1 import XMLtoJSONConverter_2
# from c12_attribute_updator import JsonSearcher, PayloadUpdater


##aml-json converter
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser
from aml_base import Caexfile
from Py4AML_JSON_main.R_aml_json_converter import convert_aml_to_json

from xsdata.formats.dataclass.parsers import JsonParser
from xsdata.formats.dataclass.serializers import XmlSerializer 
from xsdata.formats.dataclass.context import XmlContext

### firestore database 
# Use a service account
cred = credentials.Certificate('DBkey.json')
  
# check if the app is already initialized to avoid ValueError: The default Firebase app already exists.
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# set page icon
icon=Image.open('PPR_AML_Logo.png')
st.set_page_config(page_title="PPR-AML", page_icon=icon, layout="wide")

# st.image(icon, width = 150, ) # create a column and place it
st.header(":blue[PPR - AML]", divider='blue')


# Added: File type identification based on content
def identify_file_type_content_string_check(file_content, file_name) -> str:
    """
    Classify based on the presence of specific strings in the content and fallback to file extension.
    """
    # Convert a part of the bytes to string for checking
    content_sample = file_content if isinstance(file_content, str) else file_content[:500].decode('utf-8', 'ignore')
    
    if "<CAEX" in content_sample:
        return 'aml'
    if '<export date=' in content_sample:
        return 'xml_2'
    if '<XPDMXML' in content_sample:
        return 'xml_1'
    
    # Fallback to file extension checks
    file_extension = file_name.split('.')[-1].lower()
    if file_extension == 'json':
        return 'json'
    if file_extension == 'csv':
        return 'csv'
    if file_extension in ['xls', 'xlsx']:
        return 'excel'
    
    return 'invalid'

    

with st.sidebar:
    st.image(icon, width = 80, ) # create a column and place it
    st.title("PPR - AML")
    st.subheader("Upload your files here", divider='blue')

    # Upload EA-AML
    uploaded_EA_file = st.file_uploader("Upload Common Concept Model", accept_multiple_files=False, help="Upload Common Concept AML only", key="uploaded_EA_file")


    if uploaded_EA_file is not None:
        bytes_data = uploaded_EA_file.getvalue()
        context = XmlContext()
        parser = XmlParser(context=context)
        aml_object: Caexfile = parser.from_string(str(bytes_data, 'utf-8'), Caexfile)
        st.session_state["aml_object"] = aml_object

        # Firestore operation for AML files
        indent = True
        indent_value = 4
        cleaned_json = convert_aml_to_json(st.session_state["aml_object"], indent_value)
        
        # convert string (in json format) to python dictionary
        data = json.loads(cleaned_json)
        doc_ref = db.collection('utils').document("ea_cci")
        doc_ref.set(data)

        ##st.success(f"Processed EA (AML) File: {uploaded_EA_file.name}")



    # Upload different views/ files
    uploaded_files = st.file_uploader("Upload files", accept_multiple_files=True, help="Upload XML or CSV files only", key="uploaded_files")

    # Lists to hold files of different formats
    xml_1_files = []
    xml_2_files = []
    aml_files = []
    csv_files = []
    json_files = []
    excel_files = []
    invalid_files = []

    # Loop through all uploaded files
    for uploaded_file in uploaded_files:
        # Read only a sample of the file content for type identification to reduce memory overhead
        sample_content = uploaded_file.read(500)
        
        file_type = identify_file_type_content_string_check(sample_content, uploaded_file.name)
        
        if file_type == 'xml_1':
            xml_1_files.append(uploaded_file)
        elif file_type == 'xml_2':
            xml_2_files.append(uploaded_file)
        elif file_type == 'aml':
            aml_files.append(uploaded_file)
        elif file_type == 'json':
            json_files.append(uploaded_file)
        elif file_type == 'csv':
            csv_files.append(uploaded_file)
        elif file_type == 'excel':
            excel_files.append(uploaded_file)
        else:
            invalid_files.append(uploaded_file)



    # Placeholder for XML_1 processing logic
    for xml_1_file in xml_1_files:

        # get SUC_Library data from firestore
        doc_ref = db.collection("utils").document("SUC_Library")
        suc_library = doc_ref.get().to_dict()

        xml_1_content = xml_1_file.getvalue()
        converter = c9_transformer_xml_1_to_json1.XMLtoJSONConverter(suc_library)
        json_output = converter.convert(xml_1_content)

        doc_ref = db.collection('mini_payload').document(xml_1_file.name)
        doc_ref.set(json_output)
        ##st.success(f"Excel File: {xml_1_file.name}")
        st.success("Ready to Transform and Integrate")


        # from mini_payload to uploaded_views
        doc_ref = db.collection("mini_payload").document(xml_1_file.name)
        mini_payload = doc_ref.get().to_dict()

        transformer = c8_transformer_json1_to_aml.JSON_AML_transformer(mini_payload, "IdentificationRoleClassLib")
        xml_output = transformer.transform()

        context = XmlContext()
        parser = XmlParser(context=context)
        aml_object: Caexfile = parser.from_string(xml_output, Caexfile)

        # Firestore operation for AML files
        indent = True
        indent_value = 4
        cleaned_json = convert_aml_to_json(aml_object, indent_value)
        
        # convert string (in json format) to python dictionary
        data = json.loads(cleaned_json)
        doc_ref = db.collection('uploaded_views').document(xml_1_file.name)
        doc_ref.set(data)

        ##st.success(f"Processed XL (AML) File: from_XML 1")



    # Placeholder for XML_2 processing logic
    for xml_2_file in xml_2_files:

        # get SUC_Library data from firestore
        doc_ref = db.collection("utils").document("SUC_Library")
        suc_library = doc_ref.get().to_dict()

        xml_2_content = xml_2_file.getvalue()
        converter = c10_transformer_xml_2_to_json1.XMLtoJSONConverter_2(suc_library)
        json_output = converter.convert(xml_2_content)

        doc_ref = db.collection('mini_payload').document(xml_2_file.name)
        doc_ref.set(json_output)
        ##st.success(f"Excel File: {xml_2_file.name}")


        # from mini_payload to uploaded_views
        doc_ref = db.collection("mini_payload").document(xml_2_file.name)
        mini_payload = doc_ref.get().to_dict()

        transformer = c8_transformer_json1_to_aml.JSON_AML_transformer(mini_payload, "EngineeringRoleClassLib")
        xml_output = transformer.transform()

        context = XmlContext()
        parser = XmlParser(context=context)
        aml_object: Caexfile = parser.from_string(xml_output, Caexfile)

        # Firestore operation for AML files
        indent = True
        indent_value = 4
        cleaned_json = convert_aml_to_json(aml_object, indent_value)
        
        # convert string (in json format) to python dictionary
        data = json.loads(cleaned_json)
        doc_ref = db.collection('uploaded_views').document(xml_2_file.name)
        doc_ref.set(data)

        ##st.success(f"Processed XL (AML) File: from_XML 2")




    # Placeholder for XML processing logic
    for aml_file in aml_files:
        bytes_data = aml_file.getvalue()
        context = XmlContext()
        parser = XmlParser(context=context)
        aml_object: Caexfile = parser.from_string(str(bytes_data, 'utf-8'), Caexfile)
        st.session_state["aml_object"] = aml_object

        # Firestore operation for AML files
        indent = True
        indent_value = 4
        cleaned_json = convert_aml_to_json(st.session_state["aml_object"], indent_value)
        
        # convert string (in json format) to python dictionary
        data = json.loads(cleaned_json)
        doc_ref = db.collection('uploaded_views').document(aml_file.name)
        doc_ref.set(data)

        ##st.success(f"Processed XML (AML) File: {aml_file.name}")
        

    # # Placeholder for JSON processing logic
    # for json_file in json_files:
        
    #     # JSON processing logic here
    #     file_bytes = json_file.read()
    #     file_str = file_bytes.decode('utf-8') # convert bytes to string
    #     data = json.loads(file_str) # convert string (in json format) to python dictionary

    #     # Firestore operation for JSON files
    #     doc_ref = db.collection('uploaded_views').document(json_file.name)
    #     doc_ref.set(data)

    #     st.success(f"Processed JSON File: {json_file.name}")

    # Placeholder for Excel processing logic
    for excel_file in excel_files:

        # get SUC_Library data from firestore
        doc_ref = db.collection("utils").document("SUC_Library")
        suc_library = doc_ref.get().to_dict()
        
        df = pd.read_excel(excel_file)
        xl_to_json_converter = c7_transformer_csv_to_json1.ExcelToJSONConverter(df, suc_library)
        data = xl_to_json_converter.convert()

        doc_ref = db.collection('mini_payload').document(excel_file.name)
        doc_ref.set(data)
        ##st.success(f"Excel File: {excel_file.name}")

        # from mini_payload to uploaded_views
        doc_ref = db.collection("mini_payload").document(excel_file.name)
        mini_payload = doc_ref.get().to_dict()

        transformer = c8_transformer_json1_to_aml.JSON_AML_transformer(mini_payload, "RuntimeRoleClassLib")
        xml_output = transformer.transform()

        context = XmlContext()
        parser = XmlParser(context=context)
        aml_object: Caexfile = parser.from_string(xml_output, Caexfile)

        # Firestore operation for AML files
        indent = True
        indent_value = 4
        cleaned_json = convert_aml_to_json(aml_object, indent_value)
        
        # convert string (in json format) to python dictionary
        data = json.loads(cleaned_json)
        doc_ref = db.collection('uploaded_views').document(excel_file.name)
        doc_ref.set(data)

        ##st.success(f"Processed XL (AML) File: from_XL")


    # Handling invalid file formats
    if invalid_files:
        for invalid_file in invalid_files:
            st.write(f"Invalid file format: {invalid_file.name}")

    
# Integrating uploaded  files
    integrate_button = st.button('Transform & Integrate', type="primary", key="integrate_button", help="Transform and integrate the uploaded files")

## Can add only one final .aml  file  right now. Later extend to merge multiple files
    if integrate_button:

        # Use a service account
        cred = credentials.Certificate('DBkey.json')

        # check if the app is already initialized to avoid ValueError: The default Firebase app already exists.
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()

        # get SUC_Library data from firestore
        doc_ref = db.collection("utils").document("SUC_Library")
        suc_library = doc_ref.get().to_dict()


        # Fetch all documents in the collection
        docs = db.collection('uploaded_views').stream()

        # Convert to a list
        docs_list = list(docs)

        # Initialize merged_dict with the first document
        merged_dict = docs_list[0].to_dict()

        if len(docs_list) == 1:

            extract_views = c4_views_extractor.ExtractViews(suc_library)
            extract_views.run()
            # Save the result back to Firestore
            db.collection('payload').document('payload_aml-json_merged_views').set(merged_dict)
            st.success("Successfully uploaded AML file")

        else:
            extract_views = c4_views_extractor.ExtractViews(suc_library)
            extract_views.run()

            integrator = c5_integrator_EA.IntegrateViews()
            integrator.execute()

            st.success("Successfully Integrated")

        ## extract IHs from the Payload
        instances = c2_IH_extractor.GetIH()
        instances.extract_IH()





# Deleting old  files
    if st.button('Reset', key="reset", ):
        # Fetch all documents in the collection
        old_docs = db.collection('uploaded_views').stream()
        for doc in old_docs:
            # Delete each document
            db.collection('uploaded_views').document(doc.id).delete()

        old_docs = db.collection('Extracted_views').stream()
        for doc in old_docs:
            # Delete each document
            db.collection('Extracted_views').document(doc.id).delete()

        old_docs = db.collection('mini_payload').stream()
        for doc in old_docs:
            # Delete each document
            db.collection('mini_payload').document(doc.id).delete()


        st.success('Successfully deleted old files')




col_IH, col_views_connections = st.columns([1,3])

with col_IH:
    st.subheader("Instance Hierarchy", help="Select an asset to view its attributes, views, and connections")

    # call Class from C1
    generate_trees = c1_generates_PPR_IH.GenerateTrees()
    product_children, process_children, resource_children = generate_trees.ppr_tree()

    #### the following method is perfect for converting list to antd tree list structure ####
    def convert_to_antd_tree_item(self_tree_item_list):
        return [TreeItem(item.name, item.id) for item in self_tree_item_list]

    product_children = convert_to_antd_tree_item(product_children)
    process_children = convert_to_antd_tree_item(process_children)
    resource_children = convert_to_antd_tree_item(resource_children)
    #### the above method is perfect for converting list to antd tree list structure ####


    tree_IH = [TreeItem('Products:', '100', children = product_children),
            TreeItem('Process:', '200', children = process_children),
            TreeItem('Resuorce:', '300', children = resource_children)  ]

    instance = antd_tree(
        items=tree_IH,
        checkbox=False,
        show_line=True,
        icon=None,
        expand_all=True,
        selected_keys=[1],
        key=1,
    )   
    data = {'Name': "selected_IH", 'ID': instance[0]}
    db.collection('UserInteraction').document("selected_IH").set(data)
    selected_instance = instance[0]


with col_views_connections:

    views_connections_container = st.container()
    attributes_container = st.container()

    with views_connections_container:
        col_views, col_connections = st.columns(2)

        with col_views:
            st.subheader("Views", help="Select a view to display its associated attributes.")
    
            # call Class from C3
            views = c3_views_generator.Generate_Views()
            id_to_search = views.get_IH_id()
            views_list = views.ppr_tree(id_to_search)

            #### the following method is perfect for converting list to antd tree list structure ####
            def convert_to_antd_tree_item(self_tree_item_list):
                return [TreeItem(item.name, item.id) for item in self_tree_item_list]

            views_tree = convert_to_antd_tree_item(views_list)

            #### the above method is perfect for converting list to antd tree list structure ####


            tree_V = [TreeItem('Views:', '100', children = views_tree)]

            view = antd_tree(
                items=tree_V,
                checkbox=False,
                show_line=True,
                icon=None,
                expand_all=True,
                selected_keys=[1],
                key="views_tree",
            )   
            data = {'Name': "selected_View", 'ID': view[0]}
            db.collection('UserInteraction').document("selected_view").set(data)
            selected_view = view[0]


        with col_connections:
            st.subheader("Connections", help="View the connected Product, Process, and Resources for the selected asset")

            connections = c6_get_connections.GetConnections(selected_instance)
    
            connected_products, connected_processes, connected_resources = connections.get_common_tree_items()


            def convert_to_antd_tree_item(self_tree_item_list):
                return [TreeItem(item.name, item.id) for item in self_tree_item_list]

            connected_products = convert_to_antd_tree_item(connected_products)
            connected_processes = convert_to_antd_tree_item(connected_processes)
            connected_resources = convert_to_antd_tree_item(connected_resources)

            tree_list = [TreeItem('Connected Products:', '1', children = connected_products),
                        TreeItem('Connected Process:', '2', children = connected_processes),
                        TreeItem('Connected Resource:', '3', children = connected_resources),]

            instance2 = antd_tree(
                items=tree_list,
                checkbox=False,
                show_line=True,
                icon=None,
                expand_all=True, 
                key= 2    
            )
            # st.write(f'The selected item key is **{instance2}**')
    
    with attributes_container:
        st.divider()

        st.subheader("Attributes", help="Attributes related to the selected asset, based on the chosen view")

        # Initialize Firestore (move this to the top of your Streamlit script if not already done)
        cred = credentials.Certificate('DBkey.json')
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()

        # Fetch the payload from Firestore
        doc_ref = db.collection('payload').document("payload_aml-json_merged_views")
        doc = doc_ref.get()
        if doc.exists:
            payload_data = doc.to_dict()
        else:
            st.write('No such document in Firestore!')
            payload_data = {}

        # Use the payload data for the JsonSearcher
        searcher_instance = c12_attribute_updator.JsonSearcher(selected_view, data_source=payload_data)

        attributes = searcher_instance.find_attributes()
        asset_name = searcher_instance.find_name(name_type="asset")
        view_name = searcher_instance.find_name(name_type="view")
        asset_name_str = asset_name if asset_name else "Unknown Asset"
        view_name_str = view_name if view_name else "Unknown View"
        st.write("These are the attributes of " + asset_name_str + " from the " + view_name_str)

        # Convert the attributes to a DataFrame for Streamlit's data editor
        df = pd.DataFrame(attributes)

        edited_df = st.data_editor(df,
                column_config={
                    "Name": st.column_config.TextColumn(
                        "Name",
                        help="Manage your attribute names in this column"
                    ),
                    "Value": st.column_config.TextColumn(
                        "Value",
                        help="Manage the values for each attribute in this column"
                    )
                },
                disabled=["command", "is_widget"],
                hide_index=True,
                num_rows="dynamic",
                use_container_width=False
            )

        # Button to confirm the edits
        update_button = st.button('Confirm Edits', help="Add the edited attributes to the AML file")

        if update_button:
            # Here, handle the edited data
            new_attributes = edited_df.to_dict(orient='records')
            
            try:
                # Update the payload with new attributes
                updater = c12_attribute_updator.PayloadUpdater(payload_data, selected_view, new_attributes)
                update_status = updater.update_payload()

                # Update Firestore with the modified payload
                db.collection('payload').document('payload_aml-json_merged_views').set(payload_data)
                st.write(update_status)
            except ValueError as e:
                st.write(f"Error: {str(e)}")



# Download the final AML file
with st.sidebar:

    # Downloading integrated files
    # Create XML context and JSON parser
    context = XmlContext()
    json_parser = JsonParser(context=context)

    # Fetch the integrated file from Firestore
    integrated_file_ref = db.collection('payload').document('payload_aml-json_merged_views')

    # Get the document snapshot of the integrated file
    integrated_file_snapshot = integrated_file_ref.get()

    if integrated_file_snapshot.exists:
        # Convert the DocumentSnapshot to a dictionary
        data = integrated_file_snapshot.to_dict()

        # bind the data to the AML data model using the json parser
        aml_object: Caexfile = json_parser.bind_dataclass(data, Caexfile)

        # serialize the AML object to xml string
        xml_string = XmlSerializer(context=context).render(aml_object)

        #st.write(f'The integrated file was in JSON format and has been converted to AML.')
        st.download_button(
            label="Download AML",
            data=xml_string.encode('utf-8'),  # encode to bytes
            file_name="integrated_file.aml",
            mime='application/xml',
            type='primary',
            use_container_width=True, 
            help="Download the transformed and integrated AML file"
        )
    else:
        st.write("No integrated file found in Firestore.")
