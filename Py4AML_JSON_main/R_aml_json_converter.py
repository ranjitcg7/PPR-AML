# aml_converter.py

import json
from xsdata.formats.dataclass.context import XmlContext
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.serializers import JsonSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig
from aml_base import Caexfile

def json_optimizer(aml_dict: dict):
    for key, value in aml_dict.copy().items():
        if value is None or value == "" or value == "Null" or value == "None":
            del aml_dict[key]
        elif isinstance(value, list):
            if value:
                new_value_list = []
                for entry in value:
                    if isinstance(entry, str):
                        pass
                    elif isinstance(entry, dict):
                        new_value_list.append(json_optimizer(entry))
            else:
                del aml_dict[key]
        elif isinstance(value, dict):
            value = json_optimizer(value)
    return aml_dict

def convert_aml_to_json(aml_object, indent=None):
    config = SerializerConfig(pretty_print=False, ignore_default_attributes=True)
    json_serializer = JsonSerializer(context=XmlContext(), config=config, indent=indent)
    
    aml_json_string = json_serializer.render(aml_object)
    aml_dict = json.loads(aml_json_string)
    optimized_aml_dict = json_optimizer(aml_dict)

    return json.dumps(optimized_aml_dict, indent=indent)

