import json
import requests
import os
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

# Load environment variables from .env file
load_dotenv()

base_url = os.environ.get("QB_SERVER_URL", "http://10.100.11.82:5000").rstrip('/')
SERVER_URL = base_url + "/qbxml"

def get_sales_rep_map_from_qb():
    """
    Queries QuickBooks for all Sales Reps and returns a map by initial.
    """
    xml_request = """<?xml version="1.0" encoding="utf-8"?>
                    <?qbxml version="16.0"?>
                    <QBXML>
                        <QBXMLMsgsRq onError="stopOnError">
                            <SalesRepQueryRq>
                            </SalesRepQueryRq>
                        </QBXMLMsgsRq>
                    </QBXML>"""
    try:
        print("Querying QuickBooks for Sales Rep table...")
        response = requests.post(SERVER_URL, json={"xml": xml_request}, timeout=60)
        response.raise_for_status()
        response_json = response.json()
        if "response" in response_json:
            raw_xml = response_json["response"]
            root = ET.fromstring(raw_xml)
            sales_rep_list_xml = root.findall(".//SalesRepRet")
            sales_rep_map = {
                sr.find("Initial").text: {
                    "ListID": sr.find("ListID").text,
                    "FullName": sr.find("Initial").text # FullName is not available for SalesRep, use Initial
                }
                for sr in sales_rep_list_xml if sr.find("Initial") is not None
            }
            print("Successfully built Sales Rep map from QuickBooks data.")
            return sales_rep_map
        else:
            print("Error: 'response' key not found in JSON while getting Sales Reps.")
            return {}
    except Exception as e:
        print(f"An unexpected error occurred while getting Sales Reps: {e}")
        return {}

def get_customer_type_map_from_qb():
    """
    Queries QuickBooks for all Customer Types and returns a map by name.
    """
    xml_request = """<?xml version="1.0" encoding="utf-8"?>
                    <?qbxml version="16.0"?>
                    <QBXML>
                        <QBXMLMsgsRq onError="stopOnError">
                            <CustomerTypeQueryRq>
                            </CustomerTypeQueryRq>
                        </QBXMLMsgsRq>
                    </QBXML>"""
    try:
        print("Querying QuickBooks for Customer Type table...")
        response = requests.post(SERVER_URL, json={"xml": xml_request}, timeout=60)
        response.raise_for_status()
        response_json = response.json()
        if "response" in response_json:
            raw_xml = response_json["response"]
            root = ET.fromstring(raw_xml)
            customer_type_list_xml = root.findall(".//CustomerTypeRet")
            customer_type_map = {
                ct.find("FullName").text: {
                    "ListID": ct.find("ListID").text,
                    "FullName": ct.find("FullName").text
                }
                for ct in customer_type_list_xml if ct.find("FullName") is not None
            }
            print("Successfully built Customer Type map from QuickBooks data.")
            return customer_type_map
        else:
            print("Error: 'response' key not found in JSON while getting Customer Types.")
            return {}
    except Exception as e:
        print(f"An unexpected error occurred while getting Customer Types: {e}")
        return {}

def get_currency_map_from_qb():
    """
    Queries QuickBooks for all Currencies and returns a map by FullName.
    """
    xml_request = """<?xml version="1.0" encoding="utf-8"?>
                    <?qbxml version="16.0"?>
                    <QBXML>
                        <QBXMLMsgsRq onError="stopOnError">
                            <CurrencyQueryRq>
                            </CurrencyQueryRq>
                        </QBXMLMsgsRq>
                    </QBXML>"""
    try:
        print("Querying QuickBooks for Currency table...")
        response = requests.post(SERVER_URL, json={"xml": xml_request}, timeout=60)
        response.raise_for_status()
        response_json = response.json()
        if "response" in response_json:
            raw_xml = response_json["response"]
            root = ET.fromstring(raw_xml)
            currency_list_xml = root.findall(".//CurrencyRet")
            currency_map = {
                c.find("FullName").text: {
                    "ListID": c.find("ListID").text,
                    "FullName": c.find("FullName").text
                }
                for c in currency_list_xml if c.find("FullName") is not None
            }
            print("Successfully built Currency map from QuickBooks data.")
            return currency_map
        else:
            print("Error: 'response' key not found in JSON while getting Currencies.")
            return {}
    except Exception as e:
        print(f"An unexpected error occurred while getting Currencies: {e}")
        return {}

def create_customer_add_xml(customer_data, currency_map, customer_type_map, sales_rep_map):
    """
    Creates the CustomerAddRq qbXML string from Shopify customer data.
    """
    # Use default address if available, otherwise use an empty dict
    address = customer_data.get('default_address', {}) or {}

    # Determine QuickBooks Name/FullName based on the mapping document
    if address.get('company'):
        qb_name = address.get('company')
    else:
        qb_name = f"{customer_data.get('first_name', '')} {customer_data.get('last_name', '')}".strip()

    # Get currency info
    shopify_currency_code = customer_data.get('currency', 'CAD') # Default to CAD
    qb_currency = currency_map.get(shopify_currency_code)
    if not qb_currency:
        print(f"Warning: Currency code '{shopify_currency_code}' not found in map. Using CAD as default.")
        qb_currency = currency_map.get("CAD")

    # Helper to add a tag only if the value is not empty, and escape the value
    def add_tag(tag, value):
        if value:
            # Ensure value is a string before escaping
            return f"<{tag}>{escape(str(value))}</{tag}>"
        return ""

    # Construct the XML conditionally based on available data
    xml_parts = [
        "<CustomerAdd>",
        add_tag("Name", qb_name),
        add_tag("CompanyName", address.get('company')),
        add_tag("FirstName", customer_data.get('first_name')),
        add_tag("LastName", customer_data.get('last_name')),
        "<BillAddress>",
        add_tag("Addr1", address.get('address1')),
        add_tag("Addr2", address.get('address2')),
        add_tag("City", address.get('city')),
        add_tag("State", address.get('province_code')),
        add_tag("PostalCode", address.get('zip')),
        add_tag("Country", address.get('country')),
        "</BillAddress>",
        "<ShipAddress>",
        add_tag("Addr1", address.get('address1')),
        add_tag("Addr2", address.get('address2')),
        add_tag("City", address.get('city')),
        add_tag("State", address.get('province_code')),
        add_tag("PostalCode", address.get('zip')),
        add_tag("Country", address.get('country')),
        "</ShipAddress>",
        add_tag("Phone", customer_data.get('phone') or address.get('phone')),
        add_tag("Email", customer_data.get('email')),
        add_tag("Notes", customer_data.get('note')),
    ]
    
    # --- Add Refs from dynamic lookups ---
    customer_type_ref = customer_type_map.get("Shopify customers")
    if customer_type_ref:
        xml_parts.append(f"<CustomerTypeRef><ListID>{customer_type_ref['ListID']}</ListID></CustomerTypeRef>")

    sales_rep_ref = sales_rep_map.get("AS")
    if sales_rep_ref:
        xml_parts.append(f"<SalesRepRef><ListID>{sales_rep_ref['ListID']}</ListID></SalesRepRef>")

    if qb_currency:
        xml_parts.append("<CurrencyRef>")
        xml_parts.append(f"<ListID>{qb_currency['ListID']}</ListID>")
        xml_parts.append(f"<FullName>{qb_currency['FullName']}</FullName>")
        xml_parts.append("</CurrencyRef>")
        
    # Use a custom field for the Shopify ID.
    xml_parts.append("<DataExtAdd>")
    xml_parts.append("<OwnerID>0</OwnerID>")
    xml_parts.append("<DataExtName>Shopify ID</DataExtName>")
    xml_parts.append(f"<DataExtValue>{customer_data['id']}</DataExtValue>")
    xml_parts.append("</DataExtAdd>")

    xml_parts.append("</CustomerAdd>")
    
    # Filter out empty strings from the list before joining
    return "".join(filter(None, xml_parts))

def _xml_to_dict(element):
    """
    Recursively converts an XML element and its children into a dictionary.
    """
    result = {}
    for child in element:
        child_data = _xml_to_dict(child)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(child_data if child_data else child.text)
        else:
            result[child.tag] = child_data if child_data else child.text
    return result

def create_customer_to_qb(shopify_customer_json_string):
    """
    Main function to sync a single Shopify customer to QuickBooks.
    Receives Shopify customer data as a JSON string.
    Returns a dictionary of the created customer from QuickBooks.
    """
    try:
        shopify_customer_data = json.loads(shopify_customer_json_string)
    except json.JSONDecodeError:
        print("Error: Invalid JSON string provided for Shopify customer data.")
        return None

    # Get all necessary mappings from QuickBooks
    currency_map = get_currency_map_from_qb()
    customer_type_map = get_customer_type_map_from_qb()
    sales_rep_map = get_sales_rep_map_from_qb()

    if not currency_map:
        print("Warning: Currency map is empty. Currency-related fields might be missing.")
    if not customer_type_map:
        print("Warning: Customer Type map is empty. CustomerTypeRef will not be set.")
    if not sales_rep_map:
        print("Warning: Sales Rep map is empty. SalesRepRef will not be set.")

    customer_add_xml = create_customer_add_xml(shopify_customer_data, currency_map, customer_type_map, sales_rep_map)
    
    xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
                    <?qbxml version="16.0"?>
                    <QBXML>
                        <QBXMLMsgsRq onError="stopOnError">
                            <CustomerAddRq>
                                {customer_add_xml}
                            </CustomerAddRq>
                        </QBXMLMsgsRq>
                    </QBXML>"""

    try:
        print(f"Sending request to sync customer {shopify_customer_data.get('id')} to QuickBooks...")
        response = requests.post(SERVER_URL, json={"xml": xml_request}, timeout=60)
        response.raise_for_status()
        response_json = response.json()
        
        if "response" in response_json:
            raw_xml = response_json["response"]
            root = ET.fromstring(raw_xml)
            
            # Check for errors in the response
            status_code_node = root.find(".//*[@statusCode]")
            if status_code_node is not None and status_code_node.get("statusCode") != "0":
                status_message = status_code_node.get("statusMessage")
                print(f"QuickBooks Error: {status_message}")
                return {"error": status_message, "statusCode": status_code_node.get("statusCode")}

            customer_ret_element = root.find(".//CustomerRet")
            if customer_ret_element is not None:
                customer_ret_dict = _xml_to_dict(customer_ret_element)
                print("Successfully created customer in QuickBooks:")
                print(json.dumps(customer_ret_dict, indent=2))
                return customer_ret_dict
            else:
                print("CustomerRet not found in QuickBooks response.")
                return {"error": "CustomerRet not found in response."}
        else:
            print("Error: 'response' key not found in server response.")
            return {"error": "Invalid server response."}

    except requests.RequestException as e:
        print(f"HTTP Error: {e}")
        if e.response is not None:
            print("Server response:", e.response.text)
        else:
            print("No server response body available.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return None

def get_customer_by_shopify_id(shopify_id):
    """
    Finds a customer in QuickBooks by their Shopify ID custom field.
    Returns a dictionary with ListID and EditSequence if found, otherwise None.
    """
    xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="16.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <CustomerQueryRq>
            <DataExtRet>
                <OwnerID>0</OwnerID>
                <DataExtName>Shopify ID</DataExtName>
                <DataExtValue>{shopify_id}</DataExtValue>
            </DataExtRet>
        </CustomerQueryRq>
    </QBXMLMsgsRq>
</QBXML>"""
    try:
        print(f"Querying QuickBooks for customer with Shopify ID: {shopify_id}...")
        response = requests.post(SERVER_URL, json={"xml": xml_request}, timeout=60)
        response.raise_for_status()
        response_json = response.json()

        if "response" in response_json:
            raw_xml = response_json["response"]
            root = ET.fromstring(raw_xml)
            customer_ret = root.find(".//CustomerRet")
            if customer_ret is not None:
                list_id = customer_ret.find("ListID").text
                edit_sequence = customer_ret.find("EditSequence").text
                print(f"Found customer in QB. ListID: {list_id}, EditSequence: {edit_sequence}")
                return {"ListID": list_id, "EditSequence": edit_sequence}
            else:
                print("Customer with that Shopify ID not found in QuickBooks.")
                return None
    except Exception as e:
        print(f"An error occurred while querying for customer by Shopify ID: {e}")
        return None

def create_customer_mod_xml(customer_data, qb_customer_ids):
    """
    Creates the CustomerModRq qbXML string from Shopify customer data.
    """
    address = customer_data.get('default_address', {}) or {}
    if address.get('company'):
        qb_name = address.get('company')
    else:
        qb_name = f"{customer_data.get('first_name', '')} {customer_data.get('last_name', '')}".strip()

    def add_tag(tag, value):
        if value:
            return f"<{tag}>{escape(str(value))}</{tag}>"
        return ""

    xml_parts = [
        "<CustomerMod>",
        f"<ListID>{qb_customer_ids['ListID']}</ListID>",
        f"<EditSequence>{qb_customer_ids['EditSequence']}</EditSequence>",
        add_tag("Name", qb_name),
        add_tag("CompanyName", address.get('company')),
        add_tag("FirstName", customer_data.get('first_name')),
        add_tag("LastName", customer_data.get('last_name')),
        "<BillAddress>",
        add_tag("Addr1", address.get('address1')),
        add_tag("Addr2", address.get('address2')),
        add_tag("City", address.get('city')),
        add_tag("State", address.get('province_code')),
        add_tag("PostalCode", address.get('zip')),
        add_tag("Country", address.get('country')),
        "</BillAddress>",
        "<ShipAddress>",
        add_tag("Addr1", address.get('address1')),
        add_tag("Addr2", address.get('address2')),
        add_tag("City", address.get('city')),
        add_tag("State", address.get('province_code')),
        add_tag("PostalCode", address.get('zip')),
        add_tag("Country", address.get('country')),
        "</ShipAddress>",
        add_tag("Phone", customer_data.get('phone') or address.get('phone')),
        add_tag("Email", customer_data.get('email')),
        add_tag("Notes", customer_data.get('note')),
        "</CustomerMod>",
    ]
    return "".join(filter(None, xml_parts))

def update_customer_in_qb(shopify_customer_json_string):
    """
    Main function to update a single Shopify customer in QuickBooks.
    """
    try:
        shopify_customer_data = json.loads(shopify_customer_json_string)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON string provided for Shopify customer data."}

    shopify_id = shopify_customer_data.get("id")
    if not shopify_id:
        return {"error": "Shopify customer ID not found in payload."}

    # Find the customer in QuickBooks to get ListID and EditSequence
    qb_customer_ids = get_customer_by_shopify_id(shopify_id)
    if not qb_customer_ids:
        return {"error": f"Customer with Shopify ID {shopify_id} not found in QuickBooks. Cannot update."}

    # Create the CustomerMod XML
    customer_mod_xml = create_customer_mod_xml(shopify_customer_data, qb_customer_ids)
    
    xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="16.0"?>
<QBXML>
    <QBXMLMsgsRq onError="stopOnError">
        <CustomerModRq>
            {customer_mod_xml}
        </CustomerModRq>
    </QBXMLMsgsRq>
</QBXML>"""

    try:
        print(f"Sending request to update customer {shopify_id} in QuickBooks...")
        response = requests.post(SERVER_URL, json={"xml": xml_request}, timeout=60)
        response.raise_for_status()
        response_json = response.json()
        
        if "response" in response_json:
            raw_xml = response_json["response"]
            root = ET.fromstring(raw_xml)
            
            status_code_node = root.find(".//*[@statusCode]")
            if status_code_node is not None and status_code_node.get("statusCode") != "0":
                status_message = status_code_node.get("statusMessage")
                print(f"QuickBooks Error on update: {status_message}")
                return {"error": status_message, "statusCode": status_code_node.get("statusCode")}

            customer_ret_element = root.find(".//CustomerRet")
            if customer_ret_element is not None:
                customer_ret_dict = _xml_to_dict(customer_ret_element)
                print("Successfully updated customer in QuickBooks.")
                return customer_ret_dict
            else:
                return {"error": "CustomerRet not found in update response."}
        else:
            return {"error": "Invalid server response on update."}

    except Exception as e:
        print(f"An unexpected error occurred during update: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    pass

