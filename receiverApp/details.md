# QuickBooks Web Connector (QBWC) Service Implementation Guide

This document outlines the required structure and logic for developing a web service capable of interacting with QuickBooks Desktop via the QuickBooks Web Connector (QBWC), drawing primarily from the QBWC Programmer's Guide.

---

## 1. Reference Implementation Examples

The QuickBooks Web Connector (QBWC) Programmer’s Guide provides detailed blueprints for implementing the necessary SOAP interfaces, emphasizing that the development should follow a WSDL-first approach for reliable interoperability,. While the document confirms that **any platform or language supporting standard SOAP** can be used (e.g., Python), the concrete examples provided within the guide are in C-sharp and Java.

### A. C-sharp (.NET) Implementation

The document explicitly states that examples within the guide are written in C-sharp. Developers using .NET are instructed to generate the service skeleton using the SDK tool `wsdl.exe` with the `/server` switch against the standard QBWC WSDL.

This process results in an abstract class (`QBWebConnectorSvc`) containing abstract methods for each required callback, which a developer must then inherit from and implement,.

**Mandatory Callback Methods Demonstrated:**

The C-sharp examples show the implementation logic for the required methods that the QBWC client will call,:

| Callback Method | Core C\# Logic (Summary) | Source Reference |
| :--- | :--- | :--- |
| **`authenticate`** | Validates `strUserName`/`strPassword` (often hardcoded in the sample). Generates a session GUID for the ticket (`authReturn`). Returns `""` (empty string) in `authReturn` to connect to the currently open company file, or `"nvu"` if credentials fail validation,,. |,, |
| **`clientVersion`** | Checks the `strVersion` of the QBWC. Returns `W:` for a warning (to prompt the user) or `E:` for an error (to cancel the update) if the version is incompatible,. |, |
| **`sendRequestXML`** | Returns a string containing the next **qbXML request message set** from a queue (`req`) based on a session counter (`Session["counter"]`),. Returns an empty string (`""`) when work is complete. |, |
| **`receiveResponseXML`** | Processes the `response` (qbXML/qbposXML response). If no `hresult` error is present, it calculates the percentage of work completed (`(count*100)/total`) and returns an integer (0-100). Returns a negative integer (e.g., `-101`) upon error, triggering a `getLastError` call,. |, |
| **`connectionError`** | Called if QBWC fails to establish a connection to QuickBooks. Returns `"DONE"` to stop the session, or an empty string (`""`) to retry the connection with the currently open company file. |,, |
| **`getLastError`** | Returns a message string to the user, typically after the web service returns a negative value from `receiveResponseXML`,. |, |
| **`closeConnection`** | Called by QBWC to signify the update session is finished. Returns a status message (e.g., "OK"),. | |

### B. Java and Apache Axis Implementation

The guide also specifies implementation using Java and the Apache Axis framework. Developers use the `wsdl2java` tool with the `-server-side` and `-skeletonDeploy` flags to create the necessary server framework, including the implementation file (`QBWebConnectorSvcSoapImpl.java`),. This Java file contains the method signatures that must be populated with the specific service logic,.

---

## 2. Logic for Implementing Modify QuickBooks Desktop Data

The process for modifying or exchanging data with QuickBooks Desktop is managed through the continuous cycle between `sendRequestXML` and `receiveResponseXML`,.

### A. Data Modification (Write Operations)

1.  **Request Generation:** When QBWC successfully establishes a session, it calls the web service's `sendRequestXML` method,.
2.  **Sending qbXML:** To modify data (e.g., adding an invoice or updating a customer record), the web service must return a string containing the complete, valid **qbXML request message set** (or qbposXML for QBPOS),.
3.  **HCP Response:** The very first `sendRequestXML` call in a session contains the `strHCPResponse` parameter, which holds the results of the HostQuery, CompanyQuery, and PreferencesQuery, which the service can use to construct subsequent requests,.

### B. Critical Error Recovery Mechanism

Since the communication happens over the internet, connections can fail at any time. The web service must implement robust error recovery, especially for data modification requests:

*   **Error Recovery Attributes:** Developers must use the **QuickBooks error recovery mechanism** provided in the SDK, utilizing the `NewMessageSetID` and `OldMessageSetID` attributes on the `QBXMLMsgsRq` tag,.
*   **Request Persistence:** The application should **store the update request message** until the corresponding response has been fully processed. This allows the service to re-send the request using the error recovery mechanism after a communication failure to determine the status of the data write,.
*   **State Detection:** The web service must actively maintain state information (tied to the session `ticket`) to detect when an unexpected or out-of-sequence call occurs (e.g., receiving `authenticate` when `receiveResponseXML` was expected), indicating a communication failure that requires error recovery,,.

---

## 3. Task List for Python Conversion

To develop a Python SOAP server compatible with QBWC, the logic demonstrated in the C-sharp and Java examples must be translated into Python code that adheres to the SOAP requirements.

| Task Category | Python Development Task List | Source Rationale |
| :--- | :--- | :--- |
| **A. Setup and Tooling** | **1. Select Python SOAP Library:** Choose a library capable of handling WSDL definition and acting as a SOAP server. | The service must be built on a platform supporting standard SOAP,. |
| | **2. WSDL-First Implementation:** Use the chosen library to generate the service skeleton based on the QBWC WSDL (which is available at the IDN web site),,. | This is strongly recommended for ensuring interoperability with the QBWC client. |
| | **3. Define Web Service Class:** Create a Python class that implements the seven required callback methods (`authenticate`, `sendRequestXML`, `receiveResponseXML`, `connectionError`, `getLastError`, `closeConnection`, and optionally `clientVersion`). | All callbacks must be implemented to support the communication flow. |
| **B. Logic Translation** | **4. Implement `authenticate` Logic:** The Python method must return a `list` (representing the string array). Element `` must be the session ticket (GUID), and Element `` must dictate the connection state (`""`, `"nvu"`, or `"none"`),. | This structure is mandatory for QBWC to proceed or stop the session. |
| | **5. Implement Session State Management:** Replace the C# `Session` object tracking (e.g., `Session["counter"]` used in samples) with a persistent, non-stateless mechanism (like a database or persistent cache keyed by the session `ticket`) to track the progress of requests for each user. | The web imposes a stateless model, requiring the service to manage state independently. |
| | **6. Request Queuing (`sendRequestXML`):** Implement logic to retrieve the next qbXML string from the queue, return it, and advance the state counter. Return `""` when the queue is exhausted,. | This sends requests for processing by QuickBooks. |
| | **7. Response Processing (`receiveResponseXML`):** Translate the logic to process the incoming qbXML response, update internal data status, and return an integer between **0 and 100** (or a negative value for errors). | Returning 100 signals completion; less than 100 continues the process. |
| **C. Deployment Requirements**| **8. Configure HTTPS:** The final, production deployment of the Python service must use the HTTP protocol over SSL (HTTPS) to maintain a secure exchange of financial data over the Internet,. | Using HTTP is only allowed for development purposes using "localhost",. |
| | **9. Ensure Namespace Compliance:** All communication must use the required namespace `http://developer.intuit.com/`,. | This ensures QBWC can correctly interpret the web service. |