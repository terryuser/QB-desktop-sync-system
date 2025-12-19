import requests
import time
import sys

SERVER_URL = "http://10.100.11.57:8000"

def get_real_customers(username="admin"):
    print(f"--- Requesting Real Customer Data for user '{username}' ---")
    
    # 1. Queue the Task
    print(f"[1] Queueing CustomerQueryRq...")
    qbxml = '<CustomerQueryRq requestID="1"><MaxReturned>10</MaxReturned></CustomerQueryRq>'
    
    try:
        resp = requests.post(f"{SERVER_URL}/queue_task", json={
            "username": username,
            "request_xml": qbxml
        })
        if resp.status_code != 200:
            print(f"Error queueing task: {resp.text}")
            return
        
        task_id = resp.json().get("task_id")
        print(f"   -> Task Queued! Task ID: {task_id}")
        
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return

    # 2. Wait for Data
    print(f"[2] Waiting for QuickBooks Web Connector to pick it up...")
    print("    (Please run QB Web Connector 'Update' now)")
    
    while True:
        try:
            resp = requests.get(f"{SERVER_URL}/task_result/{task_id}")
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status")
                
                if status == "done":
                    result_xml = data.get("result")
                    print("\n[3] SUCCESS! Real Customer Data Received:")
                    print("-" * 50)
                    print(result_xml)
                    print("-" * 50)
                    break
                elif status == "sent":
                    sys.stdout.write("\r    Status: Sent to QuickBooks (Waiting for response)...")
                    sys.stdout.flush()
                else:
                    sys.stdout.write(f"\r    Status: {status}...")
                    sys.stdout.flush()
            
            time.sleep(2)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"\nError checking status: {e}")
            break

if __name__ == "__main__":
    get_real_customers()
