import requests
import xml.etree.ElementTree as ET
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

base_url = os.environ.get("QB_SERVER_URL", "").rstrip('/')
SERVER_URL = base_url + "/qbxml"

def get_all_sales_reps():
    """
    Sends a SalesRepQueryRq to QuickBooks to get all sales reps and returns the raw XML response.
    """
    xml_request = """<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="16.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <SalesRepQueryRq>
        </SalesRepQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
    return _send_qb_request(xml_request, "all sales reps")

def get_sales_rep_by_initial(initial):
    """
    Sends a SalesRepQueryRq to QuickBooks to get a specific sales rep by initial and returns the raw XML response.
    """
    xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="16.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <SalesRepQueryRq>
            <Initial>{initial}</Initial>
        </SalesRepQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
    return _send_qb_request(xml_request, f"sales rep with initial '{initial}'")

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

def parse_and_save_sales_reps_to_json(xml_data, json_output_path):
    """
    Parses the XML response and saves the sales rep information to a JSON file.
    """
    if not xml_data:
        print("No XML data to parse.")
        return False

    try:
        root = ET.fromstring(xml_data)
        sales_rep_list_xml = root.findall(".//SalesRepRet")

        if not sales_rep_list_xml:
            print("No sales reps found in the QuickBooks response.")
            # Create an empty file if no reps are found
            with open(json_output_path, "w") as f:
                json.dump([], f)
            print(f"Saved empty list to {json_output_path}")
            return True

        sales_reps = []
        for sr_xml in sales_rep_list_xml:
            sales_rep_data = {
                "ListID": sr_xml.find("ListID").text if sr_xml.find("ListID") is not None else None,
                "TimeCreated": sr_xml.find("TimeCreated").text if sr_xml.find("TimeCreated") is not None else None,
                "TimeModified": sr_xml.find("TimeModified").text if sr_xml.find("TimeModified") is not None else None,
                "EditSequence": sr_xml.find("EditSequence").text if sr_xml.find("EditSequence") is not None else None,
                "Name": sr_xml.find("Name").text if sr_xml.find("Name") is not None else None,
                "FullName": sr_xml.find("FullName").text if sr_xml.find("FullName") is not None else None,
                "IsActive": sr_xml.find("IsActive").text if sr_xml.find("IsActive") is not None else None,
                "Initial": sr_xml.find("Initial").text if sr_xml.find("Initial") is not None else None,
                "IsEmployee": sr_xml.find("IsEmployee").text if sr_xml.find("IsEmployee") is not None else None,
                "IsVendor": sr_xml.find("IsVendor").text if sr_xml.find("IsVendor") is not None else None,
            }
            sales_reps.append(sales_rep_data)

        # Ensure output directory exists
        output_dir = os.path.dirname(json_output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(json_output_path, "w") as f:
            json.dump(sales_reps, f, indent=2)
        
        print(f"Successfully saved sales rep list to {json_output_path}")
        return True

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
    except Exception as e:
        print(f"An error occurred during parsing: {e}")
    return False


if __name__ == "__main__":
    # Example 1: Get all sales reps and save to a file
    all_sales_reps_xml = get_all_sales_reps()
    if all_sales_reps_xml:
        success = parse_and_save_sales_reps_to_json(all_sales_reps_xml, os.path.join("json", "sales_reps.json"))
        if not success:
            print("Failed to create sales reps JSON file.")
    else:
        print("Failed to retrieve sales rep information from QuickBooks.")

    print("\n" + "="*20 + "\n")

    # Example 2: Get a specific sales rep by initial and print the result
    specific_sales_rep_xml = get_sales_rep_by_initial("AS")
    if specific_sales_rep_xml:
        root = ET.fromstring(specific_sales_rep_xml)
        sr_node = root.find(".//SalesRepRet")
        if sr_node:
            initial = sr_node.find("Initial").text
            list_id = sr_node.find("ListID").text
            print("Found specific sales rep:")
            print(f"  Initial: {initial}")
            print(f"  ListID: {list_id}")
        else:
            print("Could not find the specified sales rep.")
    else:
        print("Failed to retrieve specific sales rep information.")
