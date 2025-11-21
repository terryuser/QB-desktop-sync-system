# Shopify to QuickBooks Customer Field Mapping

This document outlines the field mapping for synchronizing customer data from Shopify to QuickBooks Desktop.

## Customer Data Mapping

The following table details the correspondence between Shopify's customer fields and QuickBooks' customer fields.

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

### Unmapped Fields

The following Shopify fields do not have a direct equivalent in the provided QuickBooks customer schema and will be ignored during the sync:

*   `state` (customer state, e.g., 'disabled')
*   `verified_email`
*   `multipass_identifier`
*   `admin_graphql_api_id`
