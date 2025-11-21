import requests
import xml.etree.ElementTree as ET
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

base_url = os.environ.get("QB_SERVER_URL", "http://10.100.11.82:5000").rstrip('/')
SERVER_URL = base_url + "/qbxml"

def get_all_currencies():
    """
    Sends a CurrencyQueryRq to QuickBooks to get all currencies and returns the raw XML response.
    """
    xml_request = """<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="16.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <CurrencyQueryRq>
        </CurrencyQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
    return _send_qb_request(xml_request, "all currencies")

def get_currency_by_name(name):
    """
    Sends a CurrencyQueryRq to QuickBooks to get a specific currency by name and returns the raw XML response.
    """
    xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="16.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <CurrencyQueryRq>
            <Name>{name}</Name>
        </CurrencyQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
    return _send_qb_request(xml_request, f"currency '{name}'")

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

def parse_and_save_currencies_to_json(xml_data, json_output_path):
    """
    Parses the XML response and saves the currency information to a JSON file.
    """
    if not xml_data:
        print("No XML data to parse.")
        return False

    try:
        root = ET.fromstring(xml_data)
        currency_list_xml = root.findall(".//CurrencyRet")

        if not currency_list_xml:
            print("No currencies found in the QuickBooks response.")
            return False

        currencies = []
        for currency_xml in currency_list_xml:
            currency_data = {
                "Name": currency_xml.find("Name").text if currency_xml.find("Name") is not None else None,
                "FullName": currency_xml.find("FullName").text if currency_xml.find("FullName") is not None else None,
                "ListID": currency_xml.find("ListID").text if currency_xml.find("ListID") is not None else None,
                "IsActive": currency_xml.find("IsActive").text if currency_xml.find("IsActive") is not None else None,
            }
            currencies.append(currency_data)

        # Ensure output directory exists
        output_dir = os.path.dirname(json_output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(json_output_path, "w") as f:
            json.dump(currencies, f, indent=2)
        
        print(f"Successfully saved currency list to {json_output_path}")
        return True

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
    except Exception as e:
        print(f"An error occurred during parsing: {e}")
    return False


if __name__ == "__main__":
    # Example 1: Get all currencies and save to a file
    all_currencies_xml = get_all_currencies()
    if all_currencies_xml:
        success = parse_and_save_currencies_to_json(all_currencies_xml, os.path.join("json", "currencies.json"))
        if not success:
            print("Failed to create currency JSON file.")
    else:
        print("Failed to retrieve currency information from QuickBooks.")

    print("\n" + "="*20 + "\n")

    # Example 2: Get a specific currency by name and print the result
    specific_currency_xml = get_currency_by_name("US Dollar")
    if specific_currency_xml:
        # You can parse and print it, or save it to a different file
        root = ET.fromstring(specific_currency_xml)
        currency_node = root.find(".//CurrencyRet")
        if currency_node:
            name = currency_node.find("Name").text
            list_id = currency_node.find("ListID").text
            is_active = currency_node.find("IsActive").text
            print("Found specific currency:")
            print(f"  Name: {name}")
            print(f"  ListID: {list_id}")
            print(f"  IsActive: {is_active}")
        else:
            print("Could not find the specified currency.")
    else:
        print("Failed to retrieve specific currency information.")
