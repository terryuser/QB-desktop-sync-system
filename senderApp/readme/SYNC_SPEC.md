
# Shopify - QuickBooks Desktop Sync: Specification Document

## 1. Overview

This document outlines the specification for a system that synchronizes data between a Shopify store and a QuickBooks Desktop installation. The system will handle the synchronization of customers, orders, and products from Shopify to QuickBooks, and inventory levels from QuickBooks to Shopify.

This system will be event-driven. An n8n workflow will listen for Shopify webhooks and trigger the appropriate synchronization function.

## 2. System Architecture

The system will consist of four main components:

1.  **n8n:** A workflow automation tool that will be configured to receive webhooks from Shopify for events such as new customers, orders, and products. The n8n workflow will then make an API call to the Sync Client to trigger the synchronization of a specific object.

2.  **Sync Client API (`sync_api.py`):** A Python Flask application that exposes a set of API endpoints for the n8n workflow to call. This server runs on port `5001` by default and contains the business logic for mapping and syncing data.
    *   The customer sync logic is imported from `sync_scripts/customer_sync.py`.
    *   **Endpoint:** `POST /sync/customer`

3.  **QuickBooks Server (`server.py`):** A Flask application running on the same machine as QuickBooks Desktop. It will expose a `/qbxml` endpoint to receive and process qbXML requests, acting as a bridge to the QuickBooks application. This component is already partially implemented and runs on port `5000`.

4.  **Configuration File (`config.json`):** A JSON file to store configuration settings such as API keys, server URLs, and synchronization preferences.

## 3. Data Flow and Mapping

### 3.1. Shopify Customer -> QuickBooks Customer

*   **Trigger:** n8n receives a "customer creation" webhook from Shopify.
*   **Action:** n8n calls the `/sync_customer` endpoint on the Sync Client, passing the Shopify customer data in the request body. The Sync Client then creates a corresponding customer in QuickBooks.
*   **Field Mapping:**

    | Shopify Field | QuickBooks Field | Transformation Logic & Notes |
    | :--- | :--- | :--- |
    | `id` | `ExternalGUID` | **Primary Key.** The Shopify customer ID will be stored in QuickBooks' `ExternalGUID` field to uniquely identify the customer and prevent duplicates. |
    | `first_name` | `FirstName` | Direct 1:1 mapping. |
    | `last_name` | `LastName` | Direct 1:1 mapping. |
    | `email` | `Email` | Direct 1:1 mapping. |
    | `phone` | `Phone` | Direct 1:1 mapping. The `phone` from Shopify's `default_address` can be used. |
    | `default_address.company` | `CompanyName` | The company from the customer's default address in Shopify will be used as the `CompanyName` in QuickBooks. |
    | `(calculated)` | `Name` / `FullName` | **Required & Unique.** This is the primary display name in QuickBooks. A consistent rule is needed. **Proposed Rule:** If `CompanyName` is available, use it. Otherwise, use a concatenation of `FirstName` and `LastName`. |
    | `note` | `Notes` | The customer note from Shopify can be appended to the QuickBooks `Notes` field. |
    | `tax_exempt` | `SalesTaxCodeRef` | This requires a mapping. If `tax_exempt` is `true`, a pre-configured 'exempt' tax code from QuickBooks should be used. Otherwise, a default taxable code will be applied. |
    | `currency` | `CurrencyRef` | Map Shopify's 3-letter currency code (e.g., "CAD") to the corresponding QuickBooks `CurrencyRef.ListID` and `CurrencyRef.FullName` using the `currencies.json` file. A default currency should be used if no match is found. |

    ### Address Mapping

    QuickBooks has separate `BillAddress` and `ShipAddress` blocks. Shopify's `default_address` will be mapped to both.

    | Shopify Field (`default_address`) | QuickBooks Field (`BillAddress` & `ShipAddress`) |
    | :--- | :--- |
    | `address1` | `Addr1` |
    | `address2` | `Addr2` |
    | `city` | `City` |
    | `province_code` | `State` |
    | `zip` | `PostalCode` |
    | `country` | `Country` |

### 3.2. Shopify Order -> QuickBooks Sales Order

*   **Trigger:** n8n receives an "order creation" webhook from Shopify.
*   **Action:** n8n calls the `/sync_order` endpoint on the Sync Client, passing the Shopify order data. The Sync Client then creates a corresponding Sales Order in QuickBooks.
*   **Field Mapping:**
    *   Shopify `order.id` -> QuickBooks `ExternalGUID`
    *   Shopify `order.customer.id` -> Link to the corresponding QuickBooks Customer (using `CustomerRef`).
    *   Shopify `order.created_at` -> QuickBooks `TxnDate`
    *   Shopify `order.name` -> QuickBooks `RefNumber`
    *   Shopify `order.line_items` -> QuickBooks `SalesOrderLineAdd`
        *   Shopify `line_item.sku` -> QuickBooks `ItemRef.FullName`
        *   Shopify `line_item.quantity` -> QuickBooks `Quantity`
        *   Shopify `line_item.price` -> QuickBooks `Rate`
    *   Shopify `order.shipping_address` -> QuickBooks `ShipAddress`
    *   Shopify `order.total_tax` -> QuickBooks `SalesTaxCodeRef` (will need a mapping in `config.json`)
    *   Shopify `order.shipping_lines` -> Add as a line item in the Sales Order.

### 3.3. Shopify Product -> QuickBooks Item

*   **Trigger:** n8n receives a "product creation" webhook from Shopify.
*   **Action:** n8n calls the `/sync_product` endpoint on the Sync Client, passing the Shopify product data. The Sync Client then creates a corresponding Item in QuickBooks.
*   **Field Mapping:**
    *   Shopify `product.id` / `variant.id` -> QuickBooks `ExternalGUID`
    *   Shopify `variant.sku` -> QuickBooks `Name` (must be unique)
    *   Shopify `product.title` + `variant.title` -> QuickBooks `SalesAndPurchase.Desc`
    *   Shopify `variant.price` -> QuickBooks `SalesAndPurchase.Price`
    *   **Income Account:** A default income account from `config.json` will be used.
    *   **Asset Account:** A default asset account from `config.json` will be used.

### 3.4. QuickBooks Inventory -> Shopify Inventory

*   **Trigger:** Scheduled task within n8n or a manual trigger.
*   **Action:** The n8n workflow will call a `/sync_inventory` endpoint on the Sync Client. The Sync Client will query QuickBooks for inventory levels of all synced items and update the corresponding inventory levels in Shopify via the Shopify API.
*   **Field Mapping:**
    *   QuickBooks `Item.Name` -> Shopify `variant.sku`
    *   QuickBooks `QuantityOnHand` -> Shopify `inventory_level.available`

## 4. Synchronization Logic

*   **Unique Identification:** To prevent duplicates, the system will use the Shopify object ID and store it in the `ExternalGUID` field in QuickBooks. For items, the SKU will be the primary key.
*   **Event-Driven Sync:** The synchronization is initiated by events from Shopify, ensuring near real-time data transfer.
*   **Updated Records:** Updates to customers and products in Shopify will trigger their respective webhooks and be reflected in QuickBooks.
*   **Inventory Sync:** Inventory sync remains a one-way, scheduled process from QuickBooks to Shopify, initiated by n8n.

## 5. Error Handling and Logging

*   The Sync Client will implement robust error handling for API connection issues, data validation errors, and QuickBooks processing errors. It will return appropriate HTTP status codes to n8n.
*   The n8n workflow will be responsible for handling retries and notifications based on the responses from the Sync Client.
*   All sync operations, successes, and failures will be logged to a file (`sync_client.log`) with detailed timestamps and error messages.

## 6. Configuration (`config.json`)

The `config.json` file will contain:

```json
{
  "shopify": {
    "api_key": "YOUR_SHOPIFY_API_KEY",
    "password": "YOUR_SHOPIFY_APP_PASSWORD",
    "store_name": "your-store-name"
  },
  "quickbooks": {
    "server_url": "http://<your_server_ip>:5000/qbxml",
    "default_income_account": "Sales",
    "default_asset_account": "Inventory Asset",
    "tax_mapping": {
      "GST": "GST"
    }
  }
}
```

## 7. Future Enhancements

*   **Two-way Product Sync:** Allow creating/updating products in QuickBooks and syncing them to Shopify.
*   **UI/Dashboard:** A simple web interface to monitor sync status, view logs, and trigger manual syncs.
*   **More Data Types:** Syncing of refunds, payments, and other data types.
