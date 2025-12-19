from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from sync_scripts.customer_sync import create_customer_to_qb, update_customer_in_qb
import json

# Create a APIRouter for customer routes
router = APIRouter()

@router.post('/')
async def create_customer(request: Request):
    """
    API endpoint to receive a Shopify customer JSON and sync it to QuickBooks.
    This is called from the main app, with a /customer prefix.
    So the full endpoint is POST /customer
    """
    try:
        shopify_customer_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request must be JSON")

    shopify_customer_json_string = json.dumps(shopify_customer_data)

    # Call the sync function
    # Note: If sync function is blocking, this might block event loop.
    # In production, run in run_in_executor or make sync function async.
    # For now, we assume it's acceptable or low volume.
    result = create_customer_to_qb(shopify_customer_json_string)

    if result:
        # Check for an error key in the returned dictionary
        if "error" in result:
            return JSONResponse(content={"status": "error", "response": result}, status_code=400)
        else:
            return JSONResponse(content={"status": "success", "response": result}, status_code=200)
    else:
        return JSONResponse(content={"status": "error", "message": "Failed to sync customer to QuickBooks. Check sync service logs."}, status_code=500)

@router.put('/{customer_id}')
async def update_customer(customer_id: str, request: Request):
    """
    API endpoint to receive a Shopify customer JSON and update the corresponding record in QuickBooks.
    The customer_id from the URL is noted, but the primary identifier used for the lookup
    is the 'id' field within the JSON payload.
    """
    try:
        shopify_customer_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request must be JSON")
    
    # Basic validation to ensure the ID in the URL matches the one in the payload
    if str(shopify_customer_data.get('id')) != customer_id:
        raise HTTPException(status_code=400, detail=f"ID in URL ({customer_id}) does not match ID in payload ({shopify_customer_data.get('id')}).")

    shopify_customer_json_string = json.dumps(shopify_customer_data)

    # Call the update function
    result = update_customer_in_qb(shopify_customer_json_string)

    if result:
        if "error" in result:
            return JSONResponse(content={"status": "error", "response": result}, status_code=400)
        else:
            return JSONResponse(content={"status": "success", "response": result}, status_code=200)
    else:
        return JSONResponse(content={"status": "error", "message": "Failed to update customer in QuickBooks. Check sync service logs."}, status_code=500)

@router.delete('/{customer_id}')
async def delete_customer(customer_id: str):
    """
    Placeholder for deleting a customer.
    """
    # In the future, you would call a `delete_customer_in_qb` function.
    return JSONResponse(content={
        "status": "placeholder",
        "message": f"This endpoint will delete customer {customer_id}."
    }, status_code=501) # 501 Not Implemented
