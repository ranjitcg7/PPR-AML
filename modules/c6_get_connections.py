import json
from typing import Dict, List
from pydantic import BaseModel
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from .c1_generates_PPR_IH import GenerateTrees
from payload import final_payload
    





# Define the GetConnections class according to your code
class GetConnections:
    def __init__(self, element_id):
        self.element_id = element_id
        self.id = id
        # Initialize Firestore
        cred = credentials.Certificate('DBkey.json')

        # check if the app is already initialized to avoid ValueError: The default Firebase app already exists.
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)

        db = firestore.client()

        # Fetch the document
        doc_ref = db.collection('payload').document(final_payload)
        doc = doc_ref.get()

        # If the document exists, store its data as 'payload'
        if doc.exists:
            self.payload = doc.to_dict()
        else:
            print('No such document!')
            self.payload = None

        # Fetch the document
        doc_ref2 = db.collection('utils').document("extracted_IH_payload")
        doc2 = doc_ref2.get()

        # If the document exists, store its data as 'payload'
        if doc2.exists:
            self.extracted_IH_payload = doc2.to_dict()
        else:
            print('No such document!')
            self.extracted_IH_payload = None


    def get_external_interface_ids(self, instance_hierarchy=None):
        if instance_hierarchy is None:
            instance_hierarchy = self.payload.get('InstanceHierarchy', [])
        
        external_interface_ids = []
        
        for element in instance_hierarchy:
            # Check if the ID matches
            if element.get('ID') == self.element_id:
                # Found the element. Get its ExternalInterface IDs if available
                for internal_element in element.get('InternalElement', []):
                    for external_interface in internal_element.get('ExternalInterface', []):
                        if 'ID' in external_interface:
                            external_interface_ids.append(external_interface['ID'])
                return external_interface_ids  # No need to traverse further
            
            # Otherwise, check inside its nested InternalElement
            external_interface_ids.extend(
                self.get_external_interface_ids(
                    element.get('InternalElement', [])
                )
            )
        
        return external_interface_ids

    def search_ref_partner_sides(self, instance_hierarchy=None):
        if instance_hierarchy is None:
            instance_hierarchy = self.payload.get('InstanceHierarchy', [])
        
        ref_partner_sides = []
        external_interface_ids = self.get_external_interface_ids()

        for element in instance_hierarchy:
            # Check for InternalLink
            if 'InternalLink' in element:
                internal_links = element['InternalLink']
                if isinstance(internal_links, dict):
                    internal_links = [internal_links]
                
                for internal_link in internal_links:
                    ref_side_a = internal_link.get('RefPartnerSideA')
                    ref_side_b = internal_link.get('RefPartnerSideB')
                    
                    if ref_side_a in external_interface_ids:
                        ref_partner_sides.append(ref_side_b)
                    
                    if ref_side_b in external_interface_ids:
                        ref_partner_sides.append(ref_side_a)
            
            # Otherwise, check inside its nested InternalElement
            ref_partner_sides.extend(
                self.search_ref_partner_sides(
                    element.get('InternalElement', [])
                )
            )
            
        return ref_partner_sides
    
    def find_element_ids_by_external_interface(self, external_interface_ids, instance_hierarchy=None, parent_id=None):
        if instance_hierarchy is None:
            instance_hierarchy = self.payload.get('InstanceHierarchy', [])
        
        element_ids = []
        for element in instance_hierarchy:
            current_parent_id = element.get('ID', None)
            # Check for ExternalInterface
            if 'ExternalInterface' in element:
                external_interfaces = element['ExternalInterface']
                if isinstance(external_interfaces, dict):
                    external_interfaces = [external_interfaces]
                
                for external_interface in external_interfaces:
                    if external_interface.get('ID') in external_interface_ids:
                        if parent_id:
                            element_ids.append(parent_id)
                        
            # Otherwise, check inside its nested InternalElement
            element_ids.extend(
                self.find_element_ids_by_external_interface(
                    external_interface_ids,
                    element.get('InternalElement', []),
                    current_parent_id
                )
            )
        
        # Remove duplicates
        element_ids = list(set(element_ids))
        return element_ids


    def get_common_tree_items(self):
        # Call ppr_tree() method from GenerateTrees
        generate_trees = GenerateTrees()
        product_children, process_children, resource_children = generate_trees.ppr_tree()

        # Get external_interface_ids and find the corresponding element_ids
        external_interface_ids = self.get_external_interface_ids()
        asset_ids = self.find_element_ids_by_external_interface(external_interface_ids)

        # Add the related element_ids (if any) to the asset_ids
        ref_partner_sides = self.search_ref_partner_sides()
        related_element_ids = self.find_element_ids_by_external_interface(ref_partner_sides)
        asset_ids.extend(related_element_ids)

        # Remove duplicates and the initially provided element_id
        asset_ids = list(set(asset_ids))
        if self.element_id in asset_ids:
            asset_ids.remove(self.element_id)

        # Create new lists to store only the common TreeItems
        common_product_children = [item for item in product_children if item.id in asset_ids]
        common_process_children = [item for item in process_children if item.id in asset_ids]
        common_resource_children = [item for item in resource_children if item.id in asset_ids]

        return common_product_children, common_process_children, common_resource_children



# Initialize the GetConnections class
#connections = GetConnections("b938ff15-1975-441b-8160-3818343b48e9")

# Execute the methods and capture the outputs
# external_interface_ids = connections.get_external_interface_ids()
#ref_partner_sides = connections.search_ref_partner_sides()
#asset_ids = connections.find_element_ids_by_external_interface(ref_partner_sides)


# # Print the results for debugging
# print("External Interface IDs:", external_interface_ids)
# print("Ref Partner Sides:", ref_partner_sides)
# print("Element IDs of Ref Partner Sides:", element_ids_of_ref_partner_sides)


#print("Asset IDs:", asset_ids)
#print("Asset Names:", asset_names)
#print("asset_PPR_status:", asset_PPR_status)

# # Call the new method
# common_product_children, common_process_children, common_resource_children = connections.get_common_tree_items()

# #Print the common TreeItems
# print("Common Product Children:", common_product_children)
# print("Common Process Children:", common_process_children)
# print("Common Resource Children:", common_resource_children)