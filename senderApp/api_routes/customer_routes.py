from flask import Blueprint, request, jsonify
from sync_scripts.customer_sync import create_customer_to_qb, update_customer_in_qb
import json

# Create a Blueprint for customer routes
customer_bp = Blueprint('customer_routes', __name__)

@customer_bp.route('/', methods=['POST'])
def create_customer():
    """
    API endpoint to receive a Shopify customer JSON and sync it to QuickBooks.
    This is called from the main app, with a /customer prefix.
    So the full endpoint is POST /customer
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    shopify_customer_data = request.get_json()
    shopify_customer_json_string = json.dumps(shopify_customer_data)

    # Call the sync function
    result = create_customer_to_qb(shopify_customer_json_string)

    if result:
        # Check for an error key in the returned dictionary
        if "error" in result:
            return jsonify({"status": "error", "response": result}), 400
        else:
            return jsonify({"status": "success", "response": result}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to sync customer to QuickBooks. Check sync service logs."}), 500

@customer_bp.route('/<string:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    """
    API endpoint to receive a Shopify customer JSON and update the corresponding record in QuickBooks.
    The customer_id from the URL is noted, but the primary identifier used for the lookup
    is the 'id' field within the JSON payload.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    shopify_customer_data = request.get_json()
    
    # Basic validation to ensure the ID in the URL matches the one in the payload
    if str(shopify_customer_data.get('id')) != customer_id:
        return jsonify({"error": f"ID in URL ({customer_id}) does not match ID in payload ({shopify_customer_data.get('id')})."}), 400

    shopify_customer_json_string = json.dumps(shopify_customer_data)

    # Call the update function
    result = update_customer_in_qb(shopify_customer_json_string)

    if result:
        if "error" in result:
            return jsonify({"status": "error", "response": result}), 400
        else:
            return jsonify({"status": "success", "response": result}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to update customer in QuickBooks. Check sync service logs."}), 500

@customer_bp.route('/<string:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    """
    Placeholder for deleting a customer.
    """
    # In the future, you would call a `delete_customer_in_qb` function.
    return jsonify({
        "status": "placeholder",
        "message": f"This endpoint will delete customer {customer_id}."
    }), 501 # 501 Not Implemented
