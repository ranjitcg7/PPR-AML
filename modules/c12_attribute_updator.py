import json
import firebase_admin
from firebase_admin import credentials, firestore

class JsonSearcher:
    def __init__(self, search_id, data_source):
        self.data = data_source
        self.search_id = search_id
        self.view_name = None
        self.asset_name = None
        print(f"Initializing JsonSearcher with search_id: {self.search_id}")  # Debug print
        print(f"Data source: {self.data}")  # Debug print
    
    def search_for_id(self, elements, parent_name=None):
        for element in elements:
            print(f"Checking element with ID: {element.get('ID')}")  # Debug print
            if element.get("ID") == self.search_id:
                print("Found matching ID!")  # Debug print
                attributes = element.get("Attribute", [])
                self.view_name = element.get("Name")
                self.asset_name = parent_name
                print(f"Attributes found: {attributes}")  # Debug print
                return [{"Name": attr["Name"], "Value": attr["Value"]} for attr in attributes]
            
            # If there are nested InternalElements, continue the search recursively
            if "InternalElement" in element:
                result = self.search_for_id(element["InternalElement"], element.get("Name"))
                if result:
                    return result
        return []
    
    def find_attributes(self):
        return self.search_for_id(self.data["InstanceHierarchy"][0]["InternalElement"])
    
    def find_name(self, name_type="both"):
        self.find_attributes()  # This will set the asset_name and view_name
        if name_type == "asset":
            return self.asset_name
        elif name_type == "view":
            return self.view_name
        elif name_type == "both":
            return {"asset_name": self.asset_name, "view_name": self.view_name}
        else:
            raise ValueError("Invalid name_type. Choose from 'asset', 'view', or 'both'.")

# The PayloadUpdater remains unchanged





class PayloadUpdater:
    def __init__(self, payload, search_id, new_attributes):
        self.payload = payload
        self.search_id = search_id
        # Filter out attributes where both Name and Value are None
        self.new_attributes = [attr for attr in new_attributes if attr["Name"] is not None or attr["Value"] is not None]
        
    def replace_attributes(self, elements):
        for element in elements:
            if element.get("ID") == self.search_id:
                # Completely overwrite the attributes
                element["Attribute"] = self.new_attributes
                return True
            
            # If there are nested InternalElements, continue the update recursively
            if "InternalElement" in element:
                updated = self.replace_attributes(element["InternalElement"])
                if updated:
                    return True
                
        return False
    
    def update_payload(self):
        updated = self.replace_attributes(self.payload["InstanceHierarchy"][0]["InternalElement"])
        if updated:
            return "Update successful!"
        else:
            raise ValueError("Failed to update the payload. Matching ID not found.")


