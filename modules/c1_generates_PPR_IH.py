import json
import pandas as pd
from typing import Dict, List
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore

from payload import final_payload

# Given code provided by the user
class customTreeItem:
    def __init__(self, name, id):
        self.name = name
        self.id = id

    def __repr__(self):
        return f"TreeItem('{self.name}', '{self.id}')"

class GenerateTrees:
    def __init__(self, cred_file='DBkey.json'):
        cred = credentials.Certificate(cred_file)

        # check if the app is already initialized to avoid ValueError: The default Firebase app already exists.
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()

    def fetch_payload(self):
        doc_ref = self.db.collection("utils").document("extracted_IH_payload")
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None
    
    # New search_ppr function as requested
    def search_ppr(self):
        payload = self.fetch_payload()
        products = []
        processes = []
        resources = []
        
        for item in payload['IH_assets']:
            if item['PPR_status'] == 'PRODUCT':
                products.append({'Name': item['Name'], 'ID': item['ID']})
            elif item['PPR_status'] == 'PROCESS':
                processes.append({'Name': item['Name'], 'ID': item['ID']})
            elif item['PPR_status'] == 'RESOURCE':
                resources.append({'Name': item['Name'], 'ID': item['ID']})
        
        return products, processes, resources
    
    def create_trees(self, products, processes, resources):
        product_tree = []
        process_tree = []
        resource_tree = []

        for item in products:
            tree_item = customTreeItem(item['Name'], item['ID'])
            product_tree.append(tree_item)

        for item in processes:
            tree_item = customTreeItem(item['Name'], item['ID'])
            process_tree.append(tree_item) 

        for item in resources:
            tree_item = customTreeItem(item['Name'], item['ID'])
            resource_tree.append(tree_item) 

        return product_tree, process_tree, resource_tree

    def ppr_tree(self):
        products, processes, resources = self.search_ppr()
        return self.create_trees(products, processes, resources)


# pprs = GenerateTrees()

# products, processes, resources = pprs.ppr_tree()

# print(products)
# print(processes)
# print(resources)
