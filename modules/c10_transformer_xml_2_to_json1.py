import json
import xml.etree.ElementTree as ET
import uuid
from collections import defaultdict
import xml.etree.ElementTree as ET

class XMLtoJSONConverter_2:
    def __init__(self, suc_library):
        self.suc_library = suc_library
    
    def extract_data_from_element(self, element):
        """Extract data from a given XML element, including nested attributes."""
        data = {
            "ID": element.attrib.get("id", ""),
            "IE": [{"IE_name": element.findtext("F_PXNAME", "")}],
            "system_unit_class": self.extract_system_unit_class(element),
            "attributes": [{"attribute_name": "id", "attribute_value": element.attrib.get("id", "")}],
            "connections": []
        }
        
        # Extract attributes from nested tags starting with F_AML_ATTR
        for nested_elem in element.findall(".//*"):  # Searching all nested elements
            if nested_elem.tag.startswith("F_AML_ATTR"):
                attribute_name = nested_elem.tag[len("F_AML_ATTR_"):]
                attribute_value = nested_elem.text
                data["attributes"].append({
                    "attribute_name": attribute_name,
                    "attribute_value": attribute_value
                })
        
        # Extract RC_path
        suc_data = self.find_matching_suc(element.attrib.get("id", ""))
        if suc_data:
            data["RCpath"] = [{
                "RC_path": f"RedRoleClassLib/{suc_data['PPR_status']}RoleClass/{suc_data['SUC_Name']}"
            }]
        
        return data
    
    def extract_system_unit_class(self, element):
        """Extract system unit class from the SUC library based on the element data."""
        suc_data = self.find_matching_suc(element.attrib.get("id", ""))
        return [{"system_unit_class_name": suc_data["SUC_Name"]}] if suc_data else [{"system_unit_class_name": ""}]
    
    def find_matching_suc(self, ie_id):
        """Find matching SUC data for the given IE_ID."""
        for entry in self.suc_library['SUCLibrary']:
            for ie in entry['InternalElements']:
                if ie['IE_ID'] == ie_id:
                    return entry
        return None
    
    def extract_internal_elements(self, root):
        """Extract internal elements from the XML."""
        elements = []
        for elem in root.findall(".//N_FS_FGR"):
            elements.append(self.extract_data_from_element(elem))
        return elements
    
    def extract_internal_links(self, root):
        """Extract internal links from the XML (placeholder for now)."""
        return []
    
    def convert(self, xml_content):
        """Convert the provided XML content to a JSON structure."""
        root = ET.fromstring(xml_content)
        internal_elements = self.extract_internal_elements(root)
        internal_links = self.extract_internal_links(root)
        
        return {
            "internal_elements": internal_elements,
            "internal_links": internal_links
        }

