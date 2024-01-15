import json
import xml.etree.ElementTree as ET
import uuid
from collections import defaultdict

class XMLtoJSONConverter:
    def __init__(self, suc_library):
        # Define XML namespace
        self.namespace = {"ns": "http://www.3ds.com/xsd/XPDMXML"}
        # Define tags to extract data from
        self.tags_to_extract = ["TransformationInst", "ResourceInst", "OperationInst"]
        # Mapping of tags to their corresponding instancing tags
        self.instancing_mapping = {
            "TransformationInst": "ProvidedPart",
            "ResourceInst": "ToolEquipment",
            "OperationInst": "HeaderOperation"
        }
        self.path_item_uuid_mapping = {}
        self.suc_library = suc_library

    def extract_ids_from_tags(self, tag_name, xml_root):
        """Extract ID values from the specified XML tag."""
        return [element.attrib["id"].split("_")[1] for element in xml_root.findall(f".//ns:{tag_name}", self.namespace)]

    def extract_name_for_ids(self, xml_root):
        """Extract Name values from the specified XML tags for the given IDs."""
        id_name_mapping = {}
        for tag in self.tags_to_extract:
            for element in xml_root.findall(f".//ns:{tag}", self.namespace):
                id_value = element.attrib["id"].split("_")[1]
                name_element = element.find("ns:Name", self.namespace)
                # If Name tag is present, update the IE_name, else use ID as default
                name_value = name_element.text if name_element is not None else id_value
                id_name_mapping[id_value] = name_value
        return id_name_mapping

    def extract_system_unit_class_name(self, xml_root):
        """Extract system_unit_class_name based on the provided mapping and the SUC library."""
        id_system_unit_class_mapping = {}
        for tag, instancing_tag in self.instancing_mapping.items():
            for element in xml_root.findall(f".//ns:{tag}", self.namespace):
                instancing_id = element.find("ns:Instancing", self.namespace).text
                corresponding_element = xml_root.find(f".//ns:{instancing_tag}[@id='{instancing_id}']", self.namespace)
                
                suc_data = self.find_matching_suc(element.attrib["id"].split("_")[1])
                if suc_data:
                    name_value = suc_data["SUC_Name"]
                else:
                    name_value = corresponding_element.find("ns:Name", self.namespace).text
                    
                id_system_unit_class_mapping[element.attrib["id"].split("_")[1]] = name_value
        return id_system_unit_class_mapping

    def find_matching_suc(self, ie_id):
        """Find matching SUC data for the given IE_ID."""
        for entry in self.suc_library['SUCLibrary']:
            for ie in entry['InternalElements']:
                if ie['IE_ID'] == ie_id:
                    return entry
        return None

    def extract_attributes(self, xml_root):
        """Extract attributes for the specified tags."""
        id_attributes_mapping = {}
        for tag, instancing_tag in self.instancing_mapping.items():
            for element in xml_root.findall(f".//ns:{tag}", self.namespace):
                instancing_id = element.find("ns:Instancing", self.namespace).text
                corresponding_element = xml_root.find(f".//ns:{instancing_tag}[@id='{instancing_id}']", self.namespace)
                attributes = []
                for child in corresponding_element:
                    if child.tag != f"{{{self.namespace['ns']}}}Name":
                        attributes.append({
                            "attribute_name": child.tag.split("}")[-1],
                            "attribute_value": child.text
                        })
                id_attributes_mapping[element.attrib["id"].split("_")[1]] = attributes
        return id_attributes_mapping

    def determine_path_item_type(self, path_item_id, xml_root):
        """Determine whether the PathItem belongs to ResourceInst or OperationInst."""
        if xml_root.find(f".//ns:ResourceInst[@id='{path_item_id}']", self.namespace) is not None:
            return "ResourceInst"
        elif xml_root.find(f".//ns:OperationInst[@id='{path_item_id}']", self.namespace) is not None:
            return "OperationInst"
        else:
            return None
        
    def extract_connections_1(self, xml_root, internal_elements_json):
        """Extract connections based on the provided instructions and the new logic."""
        internal_links = []

        # Iterate through each UsedResourceRef to identify connections
        for used_resource_ref in xml_root.findall(".//ns:UsedResourceRef", self.namespace):
            path_items = used_resource_ref.findall("ns:PathItem", self.namespace)
            
            # Determine the type for each PathItem
            path_item_types = [self.determine_path_item_type(path_item.text, xml_root) for path_item in path_items]
            
            # Determine the connection type based on the types of PathItems
            if all(item_type == "ResourceInst" for item_type in path_item_types):
                connection_name = "connected_to_RR"
            elif any(item_type == "ResourceInst" for item_type in path_item_types) and \
                 any(item_type == "OperationInst" for item_type in path_item_types):
                connection_name = "connected_to_PR"
            else:
                connection_name = "no_connection"
            
            # Generate or reuse unique IDs for each PathItem
            unique_ids = []
            for idx, path_item in enumerate(path_items):
                key = (path_item.text, connection_name)
                if key not in self.path_item_uuid_mapping:
                    self.path_item_uuid_mapping[key] = str(uuid.uuid4())
                unique_ids.append(self.path_item_uuid_mapping[key])
            
            # Create new entry in internal_links
            internal_links.append({
                "internal_link_name": f"Link_{len(internal_links) + 1}",
                "RefPartnerSideA": unique_ids[0],
                "RefPartnerSideB": unique_ids[1],
                "connection_name": connection_name
            })
            
            # Update the corresponding internal_elements entries with the generated unique IDs
            for idx, path_item in enumerate(path_items):
                matching_element = next(filter(lambda x: x["ID"] == path_item.text.split("_")[1], internal_elements_json), None)
                if matching_element:
                    if "connections" not in matching_element:
                        matching_element["connections"] = []
                    
                    # Check if connection already exists
                    connection_exists = any(conn for conn in matching_element["connections"] if conn["connection_name"] == connection_name)
                    if not connection_exists:
                        matching_element["connections"].append({
                            "connection_name": connection_name,
                            "connection_id": unique_ids[idx]
                        })

        return internal_links
         
    def extract_rc_path(self, xml_root, internal_elements_json):
        """Extract RC_path for the specified tags and update the internal elements."""
        rc_path_mapping = {
            "TransformationInst": ("ProvidedPart", "BlueRoleClassLib/ProductRoleClass/"),
            "ResourceInst": ("ToolEquipment", "BlueRoleClassLib/ResourceRoleClass/"),
            "OperationInst": ("HeaderOperation", "BlueRoleClassLib/ProcessRoleClass/")
        }
        
        for tag, (instancing_tag, prefix) in rc_path_mapping.items():
            for element in xml_root.findall(f".//ns:{tag}", self.namespace):
                id_value = element.attrib["id"].split("_")[1]
                instancing_id = element.find("ns:Instancing", self.namespace).text
                corresponding_element = xml_root.find(f".//ns:{instancing_tag}[@id='{instancing_id}']", self.namespace)
                
                # Fetch the RC path suffix from the SUC library
                suc_data = self.find_matching_suc(id_value)
                if suc_data:
                    rc_path_suffix = suc_data["SUC_Name"]
                else:
                    rc_path_suffix = corresponding_element.find("ns:Name", self.namespace).text
                    
                rc_path = prefix + rc_path_suffix
                
                # Update the corresponding internal_elements with the extracted RC_path
                matching_element = next(filter(lambda x: x["ID"] == id_value, internal_elements_json), None)
                if matching_element:
                    matching_element["RCpath"] = [{"RC_path": rc_path}]            

    def extract_connections_2(self, xml_root, internal_elements_json):
        internal_links = []

        for operation_inst in xml_root.findall(".//ns:OperationInst", self.namespace):
            operation_id = operation_inst.attrib["id"]

            transformation_instance_ref = operation_inst.find(".//ns:TransformationInstanceRef", self.namespace)
            if transformation_instance_ref is not None:
                input_item = transformation_instance_ref.find("ns:InputItem", self.namespace)
                output_item = transformation_instance_ref.find("ns:OutputItem", self.namespace)

                for path_item in [input_item, output_item]:
                    if path_item is not None:
                        # Generate or reuse unique ID for OperationInst
                        operation_key = (operation_id, "connected_to_PP")
                        if operation_key not in self.path_item_uuid_mapping:
                            self.path_item_uuid_mapping[operation_key] = str(uuid.uuid4())
                        operation_unique_id = self.path_item_uuid_mapping[operation_key]

                        # Generate or reuse unique ID for PathItem
                        path_item_key = (path_item.text, "connected_to_PP")
                        if path_item_key not in self.path_item_uuid_mapping:
                            self.path_item_uuid_mapping[path_item_key] = str(uuid.uuid4())
                        path_item_unique_id = self.path_item_uuid_mapping[path_item_key]

                        # Create new entry in internal_links
                        internal_links.append({
                            "internal_link_name": f"Link_{len(internal_links) + 1}",
                            "RefPartnerSideA": operation_unique_id,
                            "RefPartnerSideB": path_item_unique_id,
                            "connection_name": "connected_to_PP"
                        })

                        # Update the corresponding internal_elements entries with the generated unique IDs for PathItem
                        matching_element = next(filter(lambda x: x["ID"] == path_item.text.split("_")[1], internal_elements_json), None)
                        if matching_element:
                            if "connections" not in matching_element:
                                matching_element["connections"] = []
                            connection_exists = any(conn for conn in matching_element["connections"] if conn["connection_name"] == "connected_to_PP")
                            if not connection_exists:
                                matching_element["connections"].append({
                                    "connection_name": "connected_to_PP",
                                    "connection_id": path_item_unique_id
                                })

                # Update the corresponding internal_elements entries with the generated unique IDs for OperationInst
                matching_operation_element = next(filter(lambda x: x["ID"] == operation_id.split("_")[1], internal_elements_json), None)
                if matching_operation_element:
                    if "connections" not in matching_operation_element:
                        matching_operation_element["connections"] = []
                    operation_connection_exists = any(conn for conn in matching_operation_element["connections"] if conn["connection_name"] == "connected_to_PP")
                    if not operation_connection_exists:
                        matching_operation_element["connections"].append({
                            "connection_name": "connected_to_PP",
                            "connection_id": operation_unique_id
                        })

        return internal_links


    def convert(self, xml_content):
        """Convert the provided XML content to a JSON structure using the extended extraction logic."""
        # Parse the XML content
        root = ET.fromstring(xml_content)
        
        # Extract IDs for the specified tags
        extracted_ids = []
        for tag in self.tags_to_extract:
            extracted_ids.extend(self.extract_ids_from_tags(tag, root))
        
        # Create initial structure for internal_elements in the JSON based on the extracted IDs
        internal_elements_json = [{"ID": id_value} for id_value in extracted_ids]
        
        # Extract names for the IDs, system_unit_class_name, and attributes
        names_extracted = self.extract_name_for_ids(root)
        system_unit_class_names_extracted = self.extract_system_unit_class_name(root)
        attributes_extracted = self.extract_attributes(root)
        
        # Update the internal_elements in the JSON with the extracted names, system_unit_class_name, and attributes
        for element in internal_elements_json:
            id_value = element["ID"]
            element["IE"] = [{"IE_name": names_extracted[id_value]}]
            element["system_unit_class"] = [{"system_unit_class_name": system_unit_class_names_extracted[id_value]}]
            element["attributes"] = attributes_extracted[id_value]
        
        # Extract RC_path and update internal_elements
        self.extract_rc_path(root, internal_elements_json)
        
        # Extract connections and update internal_elements with connection_id
        used_resource_ref_links = self.extract_connections_1(root, internal_elements_json)
        used_resource_ref_links2 = self.extract_connections_2(root, internal_elements_json)
        # Return the JSON structure
        return {
            "internal_elements": internal_elements_json,
            "internal_links": used_resource_ref_links + used_resource_ref_links2
        }
