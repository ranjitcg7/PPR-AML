import uuid
import json
import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.serializers import JsonSerializer
from aml_base import Caexfile, CaexfileInstanceHierarchy, InternalElementType, InternalElementTypeRoleRequirements, CaexfileSystemUnitClassLib, SystemUnitFamilyType, RoleClassType, CaexfileRoleClassLib, CaexfileInterfaceClassLib

class IntegrateViews:
    def __init__(self, cred_file='DBkey.json'):
        cred = credentials.Certificate(cred_file)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        self.new_file = Caexfile(file_name="integrated_file.aml")
        self.new_ih = CaexfileInstanceHierarchy(name="InstanceHierarchy")
        self.main_ie = InternalElementType(name="Plant", id="12345")
        self.aml_xs_json_string = None

    def fetch_raw_views(self):
        raw_views = []
        collection_ref = self.db.collection("Extracted_views")
        docs = collection_ref.stream()
        for doc in docs:
            raw_views.append(doc.to_dict())
        return raw_views

    def integrate_views(self, raw_views):
        id_to_ie = {}
        #base_system_unit_path = "suc_class"
        for view_data in raw_views:
            for entry in view_data['IH_views']:
                id_value = entry['id']
                name_value = entry['asset_name']
                view_value = entry['view']
                RefBaseRCpath = entry['RefBaseRCpath']
                if id_value in id_to_ie:
                    existing_ie = id_to_ie[id_value]
                    existing_ie.role_requirements.append(InternalElementTypeRoleRequirements(ref_base_role_class_path = RefBaseRCpath[0]))   
                    existing_ie.internal_element.append(view_value)
                    # existing_ie.ref_base_system_unit_path = base_system_unit_path # check this line
                else:
                    ie = InternalElementType(name=name_value, id=str(uuid.uuid4()))
                    ie.internal_element.append(view_value)
                    # ie.ref_base_system_unit_path = base_system_unit_path # check this line
                    ie.role_requirements.append(InternalElementTypeRoleRequirements(ref_base_role_class_path = RefBaseRCpath[0]))
                    id_to_ie[id_value] = ie
            for int_links in view_data['InternalLinks']:
                self.main_ie.internal_link.append(int_links)

            for sucl in view_data['SystemUnitClassLib']:
                self.new_file.system_unit_class_lib.append(sucl)

            for rcl in view_data['RoleClassLib']:
                self.new_file.role_class_lib.append(rcl)

            for ifcl in view_data['InterfaceClassLib']:
                self.new_file.interface_class_lib.append(ifcl)


        for ie in id_to_ie.values():
            self.main_ie.internal_element.append(ie)
        self.new_ih.internal_element.append(self.main_ie)
        self.new_file.instance_hierarchy.append(self.new_ih)

    def save_to_firestore(self):
        json_serializer = JsonSerializer(context=XmlContext(), indent=4)
        self.aml_xs_json_string = json_serializer.render(self.new_file)
        self.db.collection('payload').document('payload_aml-json_merged_views').set(json.loads(self.aml_xs_json_string))

    def execute(self):
        raw_views = self.fetch_raw_views()
        self.integrate_views(raw_views)
        self.save_to_firestore()












# # Usage
# integrator = IntegrateViews()
# integrator.execute()

# # Streamlit download button
# st.download_button("Download json File", 
#                    file_name="integrated_file.json", 
#                    mime="application/json", 
#                    data=integrator.aml_xs_json_string, 
#                    use_container_width=True, 
#                    key="download_button1")

