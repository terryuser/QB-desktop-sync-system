import logging
import os
from spyne import Application, rpc, ServiceBase, Iterable, Integer, Unicode, Array, String
from spyne.protocol.soap import Soap11
from spyne.model.primitive import String as SpyneString
from spyne.protocol.xml import XmlDocument
from dotenv import load_dotenv

from state_manager import StateManager
from qbxml_utils import build_qbxml_request

# Load env
load_dotenv()
USERNAME = os.getenv("QBWC_USERNAME", "admin")
PASSWORD = os.getenv("QBWC_PASSWORD", "password")
COMPANY_FILE = os.getenv("QB_COMPANY_FILE", "") # Empty means open file

logger = logging.getLogger("qbwc")

class QBWebConnectorSvc(ServiceBase):
    @rpc(Unicode, _returns=Array(Unicode))
    def clientVersion(ctx, strVersion):
        """
        Input: strVersion
        Output: string[] { "message", "retVal" } or similar depending on implementation.
        Actually, QBWC expects a simple string return for version check:
        - "W:<msg>"
        - "E:<msg>"
        - "O:<ver>"
        - "" (empty string)
        Wait... looking at the docs, clientVersion returns string, but some wsdl defs say string[].
        The C# example returns string. The WSDL usually defines it as returning string.
        Let's check the standard valid return.
        Standard return is string.
        """
        logger.info(f"clientVersion called with: {strVersion}")
        # Return empty string to allow any version, or "W:Warning"
        return ""

    @rpc(Unicode, Unicode, _returns=Array(Unicode))
    def authenticate(ctx, strUserName, strPassword):
        """
        Input: strUserName, strPassword
        Output: string[] { ticket, companyFileName, waitBeforeNextUpdate, minRunEveryNSeconds }
        """
        logger.info(f"authenticate called for user: {strUserName}")
        
        if strUserName == USERNAME and strPassword == PASSWORD:
            state = StateManager()
            ticket = state.create_session(strUserName, COMPANY_FILE)
            logger.info(f"Authentication successful. Ticket: {ticket}")
            
            # Return array: [ticket, company_file, wait_seconds, min_run_seconds]
            # "none" for company file means no access, empty string means use open file
            
            # Auto-queue a demo task for testing purposes
            logger.info("Auto-queueing CustomerQueryRq for this session")
            state.queue_task_for_user(strUserName, '<CustomerQueryRq requestID="1"><MaxReturned>5</MaxReturned></CustomerQueryRq>')
            
            return [ticket, COMPANY_FILE if COMPANY_FILE else "", "", ""]
        else:
            logger.warning("Authentication failed")
            return ["", "nvu", "", ""]

    @rpc(Unicode, Unicode, Unicode, Unicode, Integer, Integer, _returns=Unicode)
    def sendRequestXML(ctx, ticket, strHCPResponse, strCompanyFileName, qbXMLCountry, qbXMLMajorVers, qbXMLMinorVers):
        """
        Input: ticket, strHCPResponse, ...
        Output: string (qbXML request)
        """
        logger.debug(f"sendRequestXML: {ticket}")
        state = StateManager()
        
        # Check session
        session = state.get_session(ticket)
        if not session or not session['is_active']:
            return ""

        state.update_session_activity(ticket)

        # Check for pending task
        task = state.get_next_pending_task(ticket)
        if task:
            task_id, request_xml = task
            logger.info(f"Sending task {task_id}")
            state.mark_task_sent(task_id)
            return build_qbxml_request(request_xml)
        
        # No tasks? Return empty string to finish session
        # OR "NoOp" to keep open (but standard practice is empty string if queue done)
        return ""

    @rpc(Unicode, Unicode, Unicode, Unicode, _returns=Integer)
    def receiveResponseXML(ctx, ticket, response, hresult, message):
        """
        Input: ticket, response (qbXML), hresult, message
        Output: integer (percentage done)
        """
        logger.info(f"receiveResponseXML: {ticket}, hresult: {hresult}")
        state = StateManager()
        
        if hresult:
            logger.error(f"Error from QB: {message} ({hresult})")
            # Possibly handle error
        
        # Store response
        state.complete_task(ticket, response)
        
        # Calculate progress
        progress = state.get_progress(ticket)

        # Check if more work? get_progress just calculates stats.
        # If we returned 100, QBWC might stop? 
        # Actually QBWC calls sendRequestXML loop until sendRequestXML returns empty.
        # This return value is just for progress bar.
        return progress

    @rpc(Unicode, _returns=Unicode)
    def closeConnection(ctx, ticket):
        logger.info(f"closeConnection: {ticket}")
        state = StateManager()
        state.close_session(ticket)
        return "OK"

    @rpc(Unicode, Unicode, Unicode, _returns=Unicode)
    def connectionError(ctx, ticket, hresult, message):
        logger.error(f"connectionError: {ticket} - {message}")
        state = StateManager()
        state.close_session(ticket)
        return "done"

    @rpc(Unicode, _returns=Unicode)
    def getLastError(ctx, ticket):
        logger.info(f"getLastError: {ticket}")
        # If we failed, returned message here
        return "Unknown Error"

    # Interactive Mode
    @rpc(Unicode, Unicode, _returns=Unicode)
    def getInteractiveURL(ctx, ticket, sessionID):
        logger.info("getInteractiveURL")
        # In a real app, generate a URL for the user
        return "http://localhost:8000/interactive"

    @rpc(Unicode, _returns=Unicode)
    def interactiveDone(ctx, ticket):
        logger.info("interactiveDone")
        return "Done"

    @rpc(Unicode, Unicode, _returns=Unicode)
    def interactiveRejected(ctx, ticket, reason):
        logger.info(f"interactiveRejected: {reason}")
        return "OK"
