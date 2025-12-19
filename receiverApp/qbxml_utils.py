from lxml import etree

QBXML_VERSION = "13.0"
NS = "" # QBXML often doesn't use a namespace in the body, but let's be flexible

def build_qbxml_request(request_body: str, on_error: str = "stopOnError") -> str:
    """Wraps a request body in the standard QBXML envelope."""
    root = etree.Element("QBXML")
    msgs_rq = etree.SubElement(root, "QBXMLMsgsRq", onError=on_error)
    # Parse the inner body if it's a string, or just append if it's an element
    # For simplicity, we assume request_body is a valid XML string fragment
    try:
        # We wrap in a dummy tag to parse, then append children
        fragment = etree.fromstring(f"<ROOT>{request_body}</ROOT>")
        for child in fragment:
            msgs_rq.append(child)
    except etree.XMLSyntaxError:
        # Fallback for simple single tags
        pass
    
    return f'<?xml version="1.0" encoding="utf-8"?>\n<?qbxml version="{QBXML_VERSION}"?>\n' + etree.tostring(root, pretty_print=True).decode()

def create_customer_query() -> str:
    """Creates a basic CustomerQueryRq."""
    return '<CustomerQueryRq requestID="1"><ActiveStatus>All</ActiveStatus></CustomerQueryRq>'

def create_customer_add(name: str, company: str, email: str = "") -> str:
    """Creates a CustomerAddRq."""
    xml = f'''
    <CustomerAddRq requestID="2">
        <CustomerAdd>
            <Name>{name}</Name>
            <CompanyName>{company}</CompanyName>
            <Email>{email}</Email>
        </CustomerAdd>
    </CustomerAddRq>
    '''
    return xml.strip()

def parse_qbxml_response(response_xml: str) -> dict:
    """
    Parses a QBXML response and extracts key info.
    Returns a dict with 'status_code', 'status_message', 'detail'.
    """
    try:
        # Remove processing instruction if present to avoid lxml issues sometimes
        if response_xml.strip().startswith("<?xml"):
             response_xml = response_xml.split("?>", 2)[-1]
        
        root = etree.fromstring(response_xml)
        # Find the response element (it usually ends in Rs)
        # We just look for the first child of QBXMLMsgsRs
        msgs_rs = root.find("QBXMLMsgsRs")
        if msgs_rs is not None and len(msgs_rs) > 0:
            first_response = msgs_rs[0]
            return {
                "tag": first_response.tag,
                "status_code": first_response.get("statusCode"),
                "status_message": first_response.get("statusMessage"),
                "status_severity": first_response.get("statusSeverity"),
            }
    except Exception as e:
        return {"error": str(e)}
    return {}
