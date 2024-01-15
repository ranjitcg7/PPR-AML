import firebase_admin
from firebase_admin import credentials, firestore

from payload import final_payload



class customTreeItem:
    def __init__(self, name, id):
        self.name = name
        self.id = id

    def __repr__(self):
        return f"TreeItem('{self.name}', '{self.id}')"

class Generate_Views:
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
    
    def fetch_user_interaction(self, name):
        doc_ref = self.db.collection('UserInteraction').document(name)
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None

    
    def get_IH_id(self, name='selected_IH'):
        user_interaction = self.fetch_user_interaction(name)
        if user_interaction is not None:
            ID = str(user_interaction['ID']).strip()
            return ID
        return None
    
    def search_views(self, id):
        views = []

        def search_internal_views(assets):
            nonlocal views

            if extracted_payload is not None:
                for asset in extracted_payload['IH_assets']:
                    if 'ID' in asset and asset['ID'] == id:
                        for view in asset.get("Views", []):
                            if "ViewName" in view:
                                views.append({"Name": view["ViewName"], "ID": view["ViewID"]})
        # Fetch the payload
        extracted_payload = self.fetch_payload()
        search_internal_views(extracted_payload['IH_assets'])  # Call with the correct assets

        return views
    
    def create_trees(self, tree_views):
        views_tree = []
        for item in tree_views:
            tree_item = customTreeItem(item['Name'], item['ID'])
            views_tree.append(tree_item)
        return views_tree  # Return the tree

    def ppr_tree(self, id_to_search):  # Add ID parameter
        views_as_tree = self.search_views(id_to_search)  # Pass ID to search_views
        return self.create_trees(views_as_tree)  # Pass views_as_tree to create_trees

    

# views = Generate_Views()
# id_to_search = views.get_IH_id()
# tree = views.ppr_tree(id_to_search)  
# print(tree)



