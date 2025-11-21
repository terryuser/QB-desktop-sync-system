import requests
import xml.etree.ElementTree as ET
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

base_url = os.environ.get("QB_SERVER_URL", "http://10.100.11.82:5000").rstrip('/')
SERVER_URL = base_url + "/qbxml"

def get_all_customer_types():
    """
    Sends a CustomerTypeQueryRq to QuickBooks to get all customer types and returns the raw XML response.
    """
    xml_request = """<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="16.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <CustomerTypeQueryRq>
        </CustomerTypeQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
    return _send_qb_request(xml_request, "all customer types")

def get_customer_type_by_name(name):
    """
    Sends a CustomerTypeQueryRq to QuickBooks to get a specific customer type by name and returns the raw XML response.
    """
    xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="16.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <CustomerTypeQueryRq>
            <FullName>{name}</FullName>
        </CustomerTypeQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
    return _send_qb_request(xml_request, f"customer type '{name}'")

def _send_qb_request(xml_request, request_type):
    """Helper function to send a request to the QBXML server."""
    try:
        print(f"Sending request to {SERVER_URL} to get {request_type}...")
        response = requests.post(SERVER_URL, json={"xml": xml_request}, timeout=60)
        response.raise_for_status()
        response_json = response.json()

        if "response" in response_json:
            raw_xml = response_json["response"]
            print(f"Received data for {request_type}.")
            return raw_xml
        else:
            print(f"Error: 'response' key not found in JSON for {request_type}.")
            print("Full server response:", response_json)
            return None

    except requests.RequestException as e:
        print(f"HTTP Error for {request_type}: {e}")
        if e.response is not None:
            print("Server response:", e.response.text)
        else:
            print("No server response body available.")
    except Exception as e:
        print(f"An unexpected error occurred for {request_type}: {e}")
    return None

def parse_and_save_customer_types_to_json(xml_data, json_output_path):
    """
    Parses the XML response and saves the customer type information to a JSON file.
    """
    if not xml_data:
        print("No XML data to parse.")
        return False

    try:
        root = ET.fromstring(xml_data)
        customer_type_list_xml = root.findall(".//CustomerTypeRet")

        if not customer_type_list_xml:
            print("No customer types found in the QuickBooks response.")
            # Create an empty file if no types are found
            with open(json_output_path, "w") as f:
                json.dump([], f)
            print(f"Saved empty list to {json_output_path}")
            return True

        customer_types = []
        for ct_xml in customer_type_list_xml:
            customer_type_data = {
                "ListID": ct_xml.find("ListID").text if ct_xml.find("ListID") is not None else None,
                "TimeCreated": ct_xml.find("TimeCreated").text if ct_xml.find("TimeCreated") is not None else None,
                "TimeModified": ct_xml.find("TimeModified").text if ct_xml.find("TimeModified") is not None else None,
                "EditSequence": ct_xml.find("EditSequence").text if ct_xml.find("EditSequence") is not None else None,
                "Name": ct_xml.find("Name").text if ct_xml.find("Name") is not None else None,
                "FullName": ct_xml.find("FullName").text if ct_xml.find("FullName") is not None else None,
                "IsActive": ct_xml.find("IsActive").text if ct_xml.find("IsActive") is not None else None,
                "Sublevel": ct_xml.find("Sublevel").text if ct_xml.find("Sublevel") is not None else None,
            }
            customer_types.append(customer_type_data)

        # Ensure output directory exists
        output_dir = os.path.dirname(json_output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(json_output_path, "w") as f:
            json.dump(customer_types, f, indent=2)
        
        print(f"Successfully saved customer type list to {json_output_path}")
        return True

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
    except Exception as e:
        print(f"An error occurred during parsing: {e}")
    return False


if __name__ == "__main__":
    # Example 1: Get all customer types and save to a file
    all_customer_types_xml = get_all_customer_types()
    if all_customer_types_xml:
        success = parse_and_save_customer_types_to_json(all_customer_types_xml, os.path.join("json", "customer_types.json"))
        if not success:
            print("Failed to create customer types JSON file.")
    else:
        print("Failed to retrieve customer type information from QuickBooks.")

    print("\n" + "="*20 + "\n")

    # Example 2: Get a specific customer type by name and print the result
    specific_customer_type_xml = get_customer_type_by_name("Retail")
    if specific_customer_type_xml:
        root = ET.fromstring(specific_customer_type_xml)
        ct_node = root.find(".//CustomerTypeRet")
        if ct_node:
            name = ct_node.find("Name").text
            list_id = ct_node.find("ListID").text
            print("Found specific customer type:")
            print(f"  Name: {name}")
            print(f"  ListID: {list_id}")
        else:
            print("Could not find the specified customer type.")
    else:
        print("Failed to retrieve specific customer type information.")
