from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from sync_scripts.order_sync import create_order_to_qb, update_order_in_qb
import json
import os
from datetime import datetime

# Create a APIRouter for order routes
router = APIRouter()

def save_order_json_to_logs(shopify_order_data):
    """
    Saves the received Shopify order JSON to a file in the logs directory.
    
    Args:
        shopify_order_data: Dictionary containing Shopify order data
    """
    try:
        # Ensure logs directory exists
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Get order ID for filename, or use timestamp if not available
        order_id = shopify_order_data.get('id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"order_{order_id}_{timestamp}.json"
        filepath = os.path.join(logs_dir, filename)
        
        # Write JSON to file with pretty formatting
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(shopify_order_data, f, indent=2, ensure_ascii=False)
        
        print(f"Order JSON saved to: {filepath}")
    except Exception as e:
        print(f"Error saving order JSON to logs: {e}")

@router.post('/')
async def create_order(request: Request):
    """
    API endpoint to receive a Shopify order JSON and sync it to QuickBooks as a Sales Order.
    This is called from the main app, with a /order prefix.
    So the full endpoint is POST /order
    """
    try:
        shopify_order_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request must be JSON")

    shopify_order_json_string = json.dumps(shopify_order_data)

    # Save the received JSON to logs directory
    # Running sync IO in async route - ideally move to thread
    save_order_json_to_logs(shopify_order_data)

    # Call the sync function
    result = create_order_to_qb(shopify_order_json_string)

    if result:
        # Check for an error key in the returned dictionary
        if "error" in result:
            return JSONResponse(content={"status": "error", "response": result}, status_code=400)
        else:
            return JSONResponse(content={"status": "success", "response": result}, status_code=200)
    else:
        return JSONResponse(content={"status": "error", "message": "Failed to sync order to QuickBooks. Check sync service logs."}, status_code=500)

@router.put('/{order_id}')
async def update_order(order_id: str, request: Request):
    """
    API endpoint to receive a Shopify order JSON and update the corresponding Sales Order in QuickBooks.
    The order_id from the URL is noted, but the primary identifier used for the lookup
    is the 'id' field within the JSON payload.
    """
    try:
        shopify_order_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request must be JSON")
    
    # Basic validation to ensure the ID in the URL matches the one in the payload
    if str(shopify_order_data.get('id')) != order_id:
        raise HTTPException(status_code=400, detail=f"ID in URL ({order_id}) does not match ID in payload ({shopify_order_data.get('id')}).")

    shopify_order_json_string = json.dumps(shopify_order_data)

    # Call the update function
    result = update_order_in_qb(shopify_order_json_string)

    if result:
        if "error" in result:
            return JSONResponse(content={"status": "error", "response": result}, status_code=400)
        else:
            return JSONResponse(content={"status": "success", "response": result}, status_code=200)
    else:
        return JSONResponse(content={"status": "error", "message": "Failed to update order in QuickBooks. Check sync service logs."}, status_code=500)

@router.delete('/{order_id}')
async def delete_order(order_id: str):
    """
    Placeholder for deleting an order.
    """
    # In the future, you would call a `delete_order_in_qb` function.
    return JSONResponse(content={
        "status": "placeholder",
        "message": f"This endpoint will delete order {order_id}."
    }, status_code=501) # 501 Not Implemented

