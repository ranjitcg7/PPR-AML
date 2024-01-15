import json
from typing import Dict, List
from pydantic import BaseModel
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

from payload import final_payload


class GetIH:
    def __init__(self) -> None:
        # Initialize Firestore
        cred = credentials.Certificate('DBkey.json')
        # check if the app is already initialized to avoid ValueError: The default Firebase app already exists.
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

        # Fetch the document
        doc_ref = self.db.collection('payload').document(final_payload)
        doc = doc_ref.get()
        
        # If the document exists, store its data as 'payload'
        if doc.exists:
            self.payload = doc.to_dict()
        else:
            print('No such document!')
            self.payload = None


    def extract_IH(self):
        # Load the payload data
        payload_data = self.payload
        
        # Initialize the IH_assets list and a set to keep track of processed parents
        IH_assets = []
        processed_parents = set()
        
        # Recursive function to traverse nested InternalElement and extract information
        def traverse_internal_element(data, parent=None):
            views = []
            connections = []

            # Check if the asset has the specified Name and ID
            skip_current_asset = parent and parent.get("Name") == "Plant" and parent.get("ID") == "12345"

            if not skip_current_asset:

                
                # Build the output dictionary dynamically
                output_dict = {
                    "PPR_status": "",
                    "Name": parent.get("Name", "") if parent else "",
                    "ID": parent.get("ID", "") if parent else "",
                    "Views": views,
                    "Connections" : connections
                }

                if "RoleRequirements" in data:
                    for role_req in data["RoleRequirements"]:
                        if "ProductRoleClass" in role_req.get("RefBaseRoleClassPath", ""):
                            output_dict["PPR_status"] = "PRODUCT"
                            for view in range(len(parent.get("InternalElement", []))):
                                if "Name" in parent["InternalElement"][view]:
                                    view_name = parent["InternalElement"][view]["Name"] 
                                    view_id = parent["InternalElement"][view]["ID"]
                                else:
                                    view_name = "str"
                                    view_id = "str"
                                views.append({"ViewName": view_name, "ViewID": view_id})

                        elif  "ProcessRoleClass" in role_req.get("RefBaseRoleClassPath", ""):
                            output_dict["PPR_status"] = "PROCESS"
                            for view in range(len(parent.get("InternalElement", []))):
                                if "Name" in parent["InternalElement"][view]:
                                    view_name = parent["InternalElement"][view]["Name"] 
                                    view_id = parent["InternalElement"][view]["ID"]
                                else:
                                    view_name = "str"
                                    view_id = "str"
                                views.append({"ViewName": view_name, "ViewID": view_id})

                        elif  "ResourceRoleClass" in role_req.get("RefBaseRoleClassPath", ""):
                            output_dict["PPR_status"] = "RESOURCE"
                            for view in range(len(parent.get("InternalElement", []))):
                                if "Name" in parent["InternalElement"][view]:
                                    view_name = parent["InternalElement"][view]["Name"] 
                                    view_id = parent["InternalElement"][view]["ID"]
                                else:
                                    view_name = "str"
                                    view_id = "str"
                                views.append({"ViewName": view_name, "ViewID": view_id})

                # If the output_dict contains valid data and the parent hasn't been processed, append it to IH_assets
                if output_dict["PPR_status"] == "PRODUCT" and output_dict["ID"] not in processed_parents:
                    IH_assets.append(output_dict)
                    processed_parents.add(output_dict["ID"])

                if output_dict["PPR_status"] == "PROCESS" and output_dict["ID"] not in processed_parents:
                    IH_assets.append(output_dict)
                    processed_parents.add(output_dict["ID"])

                if output_dict["PPR_status"] == "RESOURCE" and output_dict["ID"] not in processed_parents:
                    IH_assets.append(output_dict)
                    processed_parents.add(output_dict["ID"])
                
            # Recursively traverse nested InternalElement
            for internal_elem in data.get("InternalElement", []):
                traverse_internal_element(internal_elem, data)
        
        # Start the traversal with the top-level key "InstanceHierarchy"
        for item in payload_data.get("InstanceHierarchy", []):
            traverse_internal_element(item)
        
        # # Save the extracted information to the output file as a dictionary
        # with open("c2_IH_extractor.json", 'w') as output_file:
        #     json.dump({"IH_assets": IH_assets}, output_file, indent=4)
         
        extracted_IH_payload = {"IH_assets": IH_assets}

        # Save the result back to Firestore
        db = self.db
        db.collection('utils').document('extracted_IH_payload').set(extracted_IH_payload)
        ##st.success("Successfully extracted_IH_payload")

        return


# ih = GetIH()

# ih.extract_IH()


