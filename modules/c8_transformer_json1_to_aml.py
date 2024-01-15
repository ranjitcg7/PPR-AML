import streamlit as st
import uuid
import json
import os
from xsdata.formats.dataclass.serializers import JsonSerializer
from xsdata.formats.dataclass.parsers import JsonParser
from collections import defaultdict
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser, JsonParser
from xsdata.formats.dataclass.serializers import XmlSerializer, JsonSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig

from aml_base import (
    Caexfile, CaexfileSystemUnitClassLib, SystemUnitClassType, AttributeInstance, 
    CaexfileInstanceHierarchy, InternalElementType, InternalElementTypeRoleRequirements,  
    CaexfileExternalReference, RoleClassTypeExternalInterface, SystemUnitClassTypeInternalLink, AttributeType, 
    RoleClassType, CaexfileRoleClassLib, SystemUnitClassTypeSupportedRoleClass, RoleFamilyType, 
    AttributeValueRequirementTypeOrdinalScaledType, AttributeValueRequirementTypeNominalScaledType, CaexfileInterfaceClassLib, 
    InterfaceFamilyType, InterfaceClassType, MappingTypeInterfaceIdmapping
)




class JSON_AML_transformer:
    def __init__(self, input_json_data: dict, input_data_name: str = "IdentificationRoleClassLib"): # input_data_name: depends on mini_payload's RC_path
        self.input_data = input_json_data
        self.input_data_name = input_data_name
        self.new_file = self._initialize_caexfile()
    
    def _load_input_data(self) -> dict:
        with open(self.input_json_path, 'r') as f:
            return json.load(f)

    def _initialize_caexfile(self):
        # Initializing Caexfile with dynamic file name
        return Caexfile(
            superior_standard_version=[],
            file_name=self.input_data_name + ".aml"
        )
    
    def _add_internal_elements(self):
        internal_elements_data = self.input_data["internal_elements"]
        new_ih = CaexfileInstanceHierarchy(name="IH")
        new_ie = InternalElementType(name="Plant", id="1234")

        for record in internal_elements_data:
            for ie_data in record["IE"]:
                new_internal_element = InternalElementType(name=ie_data["IE_name"], id=str(uuid.uuid4()))
                self._add_role_requirements(new_internal_element, record)
                self._add_attributes(new_internal_element, record)
                self._add_external_interfaces(new_internal_element, record)
                new_ie.internal_element.append(new_internal_element)
                
                
                # Reference the System Unit Class in InternalElementType
                for rcpath_record in record.get("RCpath", []):
                    rcpath_last_component = rcpath_record.get("RC_path", "").split("/")[-1]
                    base_system_unit_path = f"{self.input_data_name}/{rcpath_last_component}"
                    new_internal_element.ref_base_system_unit_path = base_system_unit_path
                

        self._add_internal_links(new_ie)
        new_ih.internal_element.append(new_ie)
        self.new_file.instance_hierarchy.append(new_ih)

    def _add_role_requirements(self, new_internal_element, record):
        for rcpath in record["RCpath"]:
            role_req = InternalElementTypeRoleRequirements(ref_base_role_class_path=rcpath["RC_path"])
            new_internal_element.role_requirements.append(role_req)

    def _add_attributes(self, new_internal_element, record):
        for attr in record["attributes"]:
            attribute = AttributeType(name=attr["attribute_name"], value=attr["attribute_value"])
            new_internal_element.attribute.append(attribute)

    def _add_external_interfaces(self, new_internal_element, record):
        for conn in record["connections"]:
            external_interface = RoleClassTypeExternalInterface(name=conn["connection_name"], id=conn["connection_id"])
            new_internal_element.external_interface.append(external_interface)

    def _add_internal_links(self, new_ie):
        internal_links_data = self.input_data["internal_links"]
        for link_data in internal_links_data:
            new_link = SystemUnitClassTypeInternalLink(name=link_data["internal_link_name"], 
                                                       ref_partner_side_a=link_data["RefPartnerSideA"], 
                                                       ref_partner_side_b=link_data["RefPartnerSideB"])
            new_ie.internal_link.append(new_link)

    def _add_role_class_lib(self):
        new_rcl = CaexfileRoleClassLib(name=self.input_data_name, id=str(uuid.uuid4()))
        role_class_hierarchy = self._build_role_class_hierarchy()

        root_children = role_class_hierarchy[self.input_data_name]
        self._create_role_family(new_rcl, root_children, role_class_hierarchy)
        self._attach_attributes_to_role_family(new_rcl)

        self.new_file.role_class_lib.append(new_rcl)

    def _build_role_class_hierarchy(self):
        role_class_hierarchy = defaultdict(list)
        for record in self.input_data['internal_elements']:
            for rcpath_record in record.get('RCpath', []):
                rcpath = rcpath_record.get('RC_path', '')
                rc_components = rcpath.split('/')
                for i in range(len(rc_components) - 1):
                    parent = rc_components[i]
                    child = rc_components[i + 1]
                    if child not in role_class_hierarchy[parent]:
                        role_class_hierarchy[parent].append(child)
        return role_class_hierarchy

    def _create_role_family(self, parent, children, role_class_hierarchy):
        for child in children:
            rc_child = RoleFamilyType(name=child, id=str(uuid.uuid4()))
            parent.role_class.append(rc_child)
            self._create_role_family(rc_child, role_class_hierarchy[child], role_class_hierarchy)

    def _attach_attributes_to_role_family(self, parent):
        for rc_child in parent.role_class:
            for record in self.input_data['internal_elements']:
                for rcpath_record in record.get("RCpath", []):
                    rcpath_last_component = rcpath_record.get("RC_path", "").split("/")[-1]
                    if rc_child.name == rcpath_last_component:
                        for attr in record["attributes"]:
                            attribute = AttributeType(name=attr["attribute_name"], value=attr["attribute_value"])
                            rc_child.attribute.append(attribute)
            self._attach_attributes_to_role_family(rc_child)

    def _add_system_unit_class_lib(self):
        new_SUC = CaexfileSystemUnitClassLib(name=self.input_data_name, id=str(uuid.uuid4()))
        self._create_system_unit_classes(new_SUC)
        self.new_file.system_unit_class_lib.append(new_SUC)

    def _create_system_unit_classes(self, new_SUC):
        for record in self.input_data['internal_elements']:
            for rcpath_record in record.get("RCpath", []):
                rcpath_last_component = rcpath_record.get("RC_path", "").split("/")[-1]
                suc = SystemUnitClassType(name=rcpath_last_component, id=str(uuid.uuid4()))
                self._add_supported_role_classes(suc, rcpath_record)
                self._add_suc_attributes(suc, record)
                self._add_suc_internal_links(suc, record)
                new_SUC.system_unit_class.append(suc)

    def _add_supported_role_classes(self, suc, rcpath_record):
        sRC = SystemUnitClassTypeSupportedRoleClass(ref_role_class_path=rcpath_record.get("RC_path"))
        suc.supported_role_class.append(sRC)

    def _add_suc_attributes(self, suc, record):
        for attr in record["attributes"]:
            attribute = AttributeType(name=attr["attribute_name"], value=attr["attribute_value"])
            suc.attribute.append(attribute)

    def _add_suc_internal_links(self, suc, record):
        for link_data in record.get("internal_links", []):
            new_link = SystemUnitClassTypeInternalLink(name=link_data["internal_link_name"], 
                                                       ref_partner_side_a=link_data["RefPartnerSideA"], 
                                                       ref_partner_side_b=link_data["RefPartnerSideB"])
            suc.internal_link.append(new_link)

    def _add_interface_class_lib(self):
        new_interface = CaexfileInterfaceClassLib(name=self.input_data_name, id=str(uuid.uuid4()))

        pp_link = InterfaceClassType(name="PP_connection")
        pr_link = InterfaceClassType(name="PR_connection")
        rr_link = InterfaceClassType(name="RR_connection")

        new_interface.interface_class.append(pp_link)
        new_interface.interface_class.append(pr_link)
        new_interface.interface_class.append(rr_link)

        self.new_file.interface_class_lib.append(new_interface)

    def transform(self):
        self._add_internal_elements()
        self._add_role_class_lib()
        self._add_system_unit_class_lib()
        self._add_interface_class_lib()

        context = XmlContext()
        xml_serializer = XmlSerializer(context=context)
        return xml_serializer.render(self.new_file)

# This class is a refactored version of the provided code.

# transformer = XLtransformer('xl_to_json.json')
# xml_output = transformer.transform()
 


# st.download_button("Download AML (.aml) File", file_name="example.aml", mime="text/xml", data=xml_output, use_container_width=True, key="download_button10")
