import pandas as pd
import json
import uuid
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

class ExcelToJSONConverter:
    def __init__(self, df, suc_library):
        self.df = df
        self.suc_library = suc_library
        self.json_data_internal_elements = []
        self.json_data_internal_links = []
        
        # Initialize Firestore
        cred = credentials.Certificate('DBkey.json')
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def generate_unique_pair_id(self, id1, id2):
        return frozenset([id1, id2])
    
    def find_matching_suc(self, ie_id):
        """Find matching SUC data for the given IE_ID."""
        for entry in self.suc_library['SUCLibrary']:
            for ie in entry['InternalElements']:
                if ie['IE_ID'] == ie_id:
                    return entry
        return None

    def extract_system_unit_class(self, ie_id, denomination):
        """Extract system unit class from the SUC library based on the IE_ID."""
        suc_data = self.find_matching_suc(ie_id)
        return [{"system_unit_class_name": suc_data["SUC_Name"]}] if suc_data else [{"system_unit_class_name": denomination}]

    def convert(self):
        attribute_columns = [col for col in self.df.columns if col not in [
            'Functionally relevant', 'OU', 'User', 'Project_internal ID', 'Denomination', 
            'connected_to_RR', 'connected_to_PP', 'connected_to_PR', 'PPR_status']]

        added_connection_pairs = set()
        
        for index, row in self.df.iterrows():
            json_object_elements = {}
            ie_dict_elements = {}
            attributes_list_elements = []
            connections_list_elements = []
            rcpath_list_elements = []
            
            json_object_elements['ID'] = str(row['Project_internal ID']).replace('ID_', '')
            ie_dict_elements['IE_name'] = row['Denomination']
            json_object_elements['IE'] = [ie_dict_elements]
            
            ie_id = str(row['Project_internal ID']).replace('ID_', '')
            system_unit_class_dict_list = self.extract_system_unit_class(ie_id, row['Denomination'])
            json_object_elements['system_unit_class'] = system_unit_class_dict_list
            
            id_attribute_elements = {'attribute_name': 'id', 'attribute_value': json_object_elements['ID']}
            attributes_list_elements.append(id_attribute_elements)
            
            for attribute_col in attribute_columns:
                if pd.notna(row[attribute_col]):
                    attribute_elements = {'attribute_name': attribute_col, 'attribute_value': row[attribute_col]}
                    attributes_list_elements.append(attribute_elements)
            
            json_object_elements['attributes'] = attributes_list_elements
            
            added_connection_names = set()
            
            for col_name, col_value in row.items():
                if 'connected' in col_name:
                    if pd.notna(col_value):
                        connection_ids = str(col_value).replace('ID_', '').split(",")
                        for connection_id in connection_ids:
                            if col_name not in added_connection_names:
                                connection_elements = {'connection_name': col_name, 'connection_id': str(uuid.uuid4())}
                                connections_list_elements.append(connection_elements)
                                added_connection_names.add(col_name)
                            
            json_object_elements['connections'] = connections_list_elements
            
            ppr_status = row['PPR_status']
            if ppr_status == 'Product':
                rcpath_str = 'ProductRoleClass'
            elif ppr_status == 'Process':
                rcpath_str = 'ProcessRoleClass'
            elif ppr_status == 'Resource':
                rcpath_str = 'ResourceRoleClass'
            else:
                rcpath_str = 'UnknownRoleClass'
                
            suc_data = self.find_matching_suc(ie_id)
            suc_name = suc_data["SUC_Name"] if suc_data else ie_dict_elements["IE_name"]
            rcpath_dict_elements = {'RC_path': f'GreenRoleClassLib/{rcpath_str}/{suc_name}'}
            rcpath_list_elements.append(rcpath_dict_elements)
            json_object_elements['RCpath'] = rcpath_list_elements
            
            self.json_data_internal_elements.append(json_object_elements)

        # Logic for internal_links starts here
        index_to_internal_id = {index: elem['ID'] for index, elem in enumerate(self.json_data_internal_elements)}
        internal_id_to_connections = {elem['ID']: elem['connections'] for elem in self.json_data_internal_elements}

        for index, row in self.df.iterrows():
            current_internal_id = index_to_internal_id[index]
            
            for col_name, col_value in row.items():
                if 'connected' in col_name:
                    if pd.notna(col_value):
                        connected_ids = [x.strip() for x in str(col_value).replace('ID_', '').split(",")]
                        
                        for connected_id in connected_ids:
                            target_internal_id = index_to_internal_id[self.df[self.df['Project_internal ID'] == f'ID_{connected_id}'].index[0]]
                            
                            if any(conn['connection_name'] == col_name for conn in internal_id_to_connections[target_internal_id]):
                                id_pair = tuple(sorted([current_internal_id, target_internal_id]))
                                
                                if id_pair not in added_connection_pairs:
                                    ref_partner_side_a = [conn['connection_id'] for conn in internal_id_to_connections[current_internal_id] if conn['connection_name'] == col_name][0]
                                    ref_partner_side_b = [conn['connection_id'] for conn in internal_id_to_connections[target_internal_id] if conn['connection_name'] == col_name][0]
                                    
                                    internal_link = {
                                        'internal_link_name': f"Link_{len(self.json_data_internal_links) + 1}",
                                        'RefPartnerSideA': ref_partner_side_a,
                                        'RefPartnerSideB': ref_partner_side_b
                                    }
                                    self.json_data_internal_links.append(internal_link)
                                    added_connection_pairs.add(id_pair)

        final_json_data = {
            'internal_elements': self.json_data_internal_elements,
            'internal_links': self.json_data_internal_links
        }
        
        # Upload to Firestore
        # self.upload_to_firestore(final_json_data)

        return final_json_data
    
        
    def upload_to_firestore(self, final_json_data):
        self.db.collection('mini_payload').document('csv_to_json').set(final_json_data)

# # Usage
# df = pd.read_excel('Beispiel_Gelenk_V2_IdentificationData.xls')  # Load your Excel file here
# converter = ExcelToJSONConverter(df)
# converter.convert()  # This will also upload the data to Firestore
