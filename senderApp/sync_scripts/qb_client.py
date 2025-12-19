import requests
import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base URL for the receiverApp (FastAPI + Spyne)
SERVER_URL = os.environ.get("QB_SERVER_URL", "http://localhost:8000").rstrip('/')
USERNAME = os.environ.get("QBWC_USERNAME", "admin")

def poll_task_result(task_id, timeout=60, poll_interval=2):
    """
    Polls the receiverApp for the result of a queued task.
    
    Args:
        task_id: The ID of the task to poll for.
        timeout: Maximum time to wait in seconds.
        poll_interval: Time to wait between polls in seconds.
        
    Returns:
        The result XML string if successful, or None if timed out or failed.
    """
    start_time = time.time()
    print(f"Polling for task {task_id} result (Timeout: {timeout}s)...")
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{SERVER_URL}/task_result/{task_id}")
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "done":
                    return data.get("result")
                elif status == "error":
                    print(f"Task {task_id} failed with error on server side.")
                    return None
                # If 'pending', 'sent', or 'processing', continue polling
            else:
                print(f"Error polling task status: {response.status_code} {response.text}")
        except requests.RequestException as e:
            print(f"Network error while polling: {e}")
            
        time.sleep(poll_interval)
        
    print(f"Timed out waiting for task {task_id} result.")
    return None

def send_qbxml_request(request_xml):
    """
    Queues a QBXML request on the receiverApp and waits for the response.
    
    Args:
        request_xml: The qbXML request string.
        
    Returns:
        The response XML string, or None if failed.
    """
    try:
        # 1. Queue the task
        print("Queueing task to receiverApp...")
        response = requests.post(f"{SERVER_URL}/queue_task", json={
            "username": USERNAME,
            "request_xml": request_xml
        }, timeout=10)
        response.raise_for_status()
        
        task_data = response.json()
        task_id = task_data.get("task_id")
        
        if not task_id:
            print("Failed to get task_id from queue_task response.")
            return None
            
        print(f"Task queued with ID: {task_id}")
        
        # 2. Poll for result
        result_xml = poll_task_result(task_id)
        
        if result_xml:
            return result_xml
        else:
            print("Failed to get result from QBWC.")
            return None
            
    except requests.RequestException as e:
        print(f"Error communicating with receiverApp: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in send_qbxml_request: {e}")
        return None
