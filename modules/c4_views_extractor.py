import json
import firebase_admin
from firebase_admin import credentials, firestore

class ExtractViews:
    def __init__(self, suc_library):
        # Initialize Firestore
        cred = credentials.Certificate('DBkey.json')
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        self.suc_library = suc_library
    
    def get_uploaded_views(self):
        raw_views = []
        collection_ref = self.db.collection("uploaded_views")
        docs = collection_ref.stream()
        for doc in docs:
            raw_views.append({"id": doc.id, "data": doc.to_dict()})
        return raw_views
    
    def find_matching_suc(self, ie_id):
        """Find matching SUC data for the given IE_ID."""
        for entry in self.suc_library['SUCLibrary']:
            for ie in entry['InternalElements']:
                if ie['IE_ID'] == ie_id:
                    return entry
        return None
    
    def extract_ids_with_details(self, internal_elements, output_data, view_name):
        for element in internal_elements:
            id_value = None
            view_object = None

            # newly added path*
            role_requirements_list = element.get("RoleRequirements", [])
            ref_base_role_class_paths = []
            if role_requirements_list:
                for role_requirement in role_requirements_list:
                    ref_base_role_class_path = role_requirement.get("RefBaseRoleClassPath", "Key not found")
                    ref_base_role_class_paths.append(ref_base_role_class_path)
            else:
                ref_base_role_class_path = "RoleRequirements is empty"
            
            if 'Attribute' in element:
                attributes = element['Attribute']
                for attribute in attributes:
                    if attribute.get('Name') == 'id':
                        id_value = attribute.get('Value')
                        view_object = element
                        asset_name = element.get('Name')
                if id_value is not None:
                    matching_suc_entry = self.find_matching_suc(id_value)
                    ref_base_system_unit_path = []  # Initialize as an empty list
                    if matching_suc_entry is not None:
                        # Prepend "Diamond/" to the SUC_Name and append to the list
                        ref_base_system_unit_path.append("Diamond/" + matching_suc_entry['SUC_Name'])  
                        
                    new_view = {
                        "id": id_value,
                        "asset_name": asset_name,
                        "view_name": view_name,
                        "view": view_object,
                        "RefBaseRCpath": ref_base_role_class_paths,    # newly added path*
                        "RefBaseSystemUnitPath": ref_base_system_unit_path    # newly added path* Make sure that this is coming from a lib
                    }
                    output_data['IH_views'].append(new_view)
            if 'InternalElement' in element:
                self.extract_ids_with_details(element['InternalElement'], output_data, view_name)
    
    def extract_internal_links(self, internal_elements, output_data):
        for element in internal_elements:
            if 'InternalLink' in element:
                internal_links = element['InternalLink']
                if isinstance(internal_links, list):
                    output_data['InternalLinks'].extend(internal_links)
                else:
                    output_data['InternalLinks'].append(internal_links)
            if 'InternalElement' in element:
                self.extract_internal_links(element['InternalElement'], output_data)
    
    def update_view_names(self, output_data):
        for entry in output_data['IH_views']:
            view_name = entry['view_name']
            if 'Name' in entry['view']:
                entry['view']['Name'] = view_name

    def extract_libraries(self, payload, output_data):
        """Extract the specified libraries from the JSON data and merge with existing data."""
        libraries = ["SystemUnitClassLib", "RoleClassLib", "InterfaceClassLib", "AttributeTypeLib"]
        for lib in libraries:
            if lib in payload:
                if lib in output_data:
                    output_data[lib].extend(payload[lib])  # merge the new data
                else:
                    output_data[lib] = payload[lib]  # directly add the new data

    def run(self):
        uploaded_views = self.get_uploaded_views()
        view_counter = 1
        for view in uploaded_views:
            payload = view["data"]
            input_file_name = view["id"]
            output_data = {
                "IH_views": [],
                "InternalLinks": [],
                "SystemUnitClassLib": [],
                "RoleClassLib": [],
                "InterfaceClassLib": [],
                "AttributeTypeLib": [],
            }

            view_name_parts = input_file_name.split('_')
            view_name = "View" + str(view_counter)
            for part in view_name_parts:
                if "view" in part.lower():
                    view_name = part
                    break

            if 'InstanceHierarchy' in payload:
                instance_hierarchy = payload['InstanceHierarchy']
                for element in instance_hierarchy:
                    if 'InternalElement' in element:
                        self.extract_ids_with_details(element['InternalElement'], output_data, view_name)
                        self.extract_internal_links(element['InternalElement'], output_data)
            
            # Extract the specified libraries from the JSON payload
            self.extract_libraries(payload, output_data)
            
            self.update_view_names(output_data)
            
            document_name = "Extracted_" + input_file_name
            self.db.collection('Extracted_views').document(document_name).set(output_data)
            
            view_counter += 1

# The class ExtractViews now integrates the extraction of the specified libraries without overwriting the IH_views.


# # Create an instance of the class and run the processor
# processor = ExtractViews()
# processor.run()

