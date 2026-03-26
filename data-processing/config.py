"""
Configuration for SAP O2C Data Preprocessing Pipeline.

Defines paths, entity schemas (primary keys, column types, nested fields),
and normalization rules for all 19 entity types.
"""

from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "sap-o2c-data"
OUTPUT_DIR = BASE_DIR / "output"
ENTITIES_OUTPUT_DIR = OUTPUT_DIR / "entities"
JOINED_OUTPUT_DIR = OUTPUT_DIR / "joined"

# ─── All entity directory names ──────────────────────────────────────────────
ENTITY_NAMES = [
    "sales_order_headers",
    "sales_order_items",
    "sales_order_schedule_lines",
    "outbound_delivery_headers",
    "outbound_delivery_items",
    "billing_document_headers",
    "billing_document_items",
    "billing_document_cancellations",
    "journal_entry_items_accounts_receivable",
    "payments_accounts_receivable",
    "business_partners",
    "business_partner_addresses",
    "customer_company_assignments",
    "customer_sales_area_assignments",
    "products",
    "product_descriptions",
    "product_plants",
    "product_storage_locations",
    "plants",
]

# ─── Entity Schemas ──────────────────────────────────────────────────────────
# Each entity defines:
#   primary_keys  : list of columns forming the unique key
#   datetime_cols : columns to parse as datetime
#   numeric_cols  : columns to cast to float64
#   bool_cols     : columns to cast to bool
#   nested_cols   : dict-type columns to flatten (e.g. time objects)
#   str_cols      : columns to keep as string (default for unlisted cols)

ENTITY_SCHEMAS = {
    # ── Sales ─────────────────────────────────────────────────────────────
    "sales_order_headers": {
        "primary_keys": ["salesOrder"],
        "datetime_cols": [
            "creationDate", "lastChangeDateTime",
            "pricingDate", "requestedDeliveryDate",
        ],
        "numeric_cols": ["totalNetAmount"],
        "bool_cols": [],
        "nested_cols": [],
    },
    "sales_order_items": {
        "primary_keys": ["salesOrder", "salesOrderItem"],
        "datetime_cols": [],
        "numeric_cols": ["requestedQuantity", "netAmount"],
        "bool_cols": [],
        "nested_cols": [],
    },
    "sales_order_schedule_lines": {
        "primary_keys": ["salesOrder", "salesOrderItem", "scheduleLine"],
        "datetime_cols": ["confirmedDeliveryDate"],
        "numeric_cols": ["confdOrderQtyByMatlAvailCheck"],
        "bool_cols": [],
        "nested_cols": [],
    },

    # ── Delivery ──────────────────────────────────────────────────────────
    "outbound_delivery_headers": {
        "primary_keys": ["deliveryDocument"],
        "datetime_cols": [
            "actualGoodsMovementDate", "creationDate", "lastChangeDate",
        ],
        "numeric_cols": [],
        "bool_cols": [],
        "nested_cols": ["actualGoodsMovementTime", "creationTime"],
    },
    "outbound_delivery_items": {
        "primary_keys": ["deliveryDocument", "deliveryDocumentItem"],
        "datetime_cols": ["lastChangeDate"],
        "numeric_cols": ["actualDeliveryQuantity"],
        "bool_cols": [],
        "nested_cols": [],
    },

    # ── Billing ───────────────────────────────────────────────────────────
    "billing_document_headers": {
        "primary_keys": ["billingDocument"],
        "datetime_cols": [
            "creationDate", "lastChangeDateTime", "billingDocumentDate",
        ],
        "numeric_cols": ["totalNetAmount"],
        "bool_cols": ["billingDocumentIsCancelled"],
        "nested_cols": ["creationTime"],
    },
    "billing_document_items": {
        "primary_keys": ["billingDocument", "billingDocumentItem"],
        "datetime_cols": [],
        "numeric_cols": ["billingQuantity", "netAmount"],
        "bool_cols": [],
        "nested_cols": [],
    },
    "billing_document_cancellations": {
        "primary_keys": ["billingDocument"],
        "datetime_cols": [
            "creationDate", "lastChangeDateTime", "billingDocumentDate",
        ],
        "numeric_cols": ["totalNetAmount"],
        "bool_cols": ["billingDocumentIsCancelled"],
        "nested_cols": ["creationTime"],
    },

    # ── Finance ───────────────────────────────────────────────────────────
    "journal_entry_items_accounts_receivable": {
        "primary_keys": ["companyCode", "fiscalYear", "accountingDocument", "accountingDocumentItem"],
        "datetime_cols": [
            "postingDate", "documentDate", "lastChangeDateTime", "clearingDate",
        ],
        "numeric_cols": [
            "amountInTransactionCurrency", "amountInCompanyCodeCurrency",
        ],
        "bool_cols": [],
        "nested_cols": [],
    },
    "payments_accounts_receivable": {
        "primary_keys": ["companyCode", "fiscalYear", "accountingDocument", "accountingDocumentItem"],
        "datetime_cols": [
            "clearingDate", "postingDate", "documentDate",
        ],
        "numeric_cols": [
            "amountInTransactionCurrency", "amountInCompanyCodeCurrency",
        ],
        "bool_cols": [],
        "nested_cols": [],
    },

    # ── Master Data: Business Partners / Customers ────────────────────────
    "business_partners": {
        "primary_keys": ["businessPartner"],
        "datetime_cols": ["creationDate", "lastChangeDate"],
        "numeric_cols": [],
        "bool_cols": ["businessPartnerIsBlocked", "isMarkedForArchiving"],
        "nested_cols": ["creationTime"],
    },
    "business_partner_addresses": {
        "primary_keys": ["businessPartner", "addressId"],
        "datetime_cols": ["validityStartDate", "validityEndDate"],
        "numeric_cols": [],
        "bool_cols": ["poBoxIsWithoutNumber"],
        "nested_cols": [],
    },
    "customer_company_assignments": {
        "primary_keys": ["customer", "companyCode"],
        "datetime_cols": [],
        "numeric_cols": [],
        "bool_cols": ["deletionIndicator"],
        "nested_cols": [],
    },
    "customer_sales_area_assignments": {
        "primary_keys": ["customer", "salesOrganization", "distributionChannel", "division"],
        "datetime_cols": [],
        "numeric_cols": [],
        "bool_cols": ["completeDeliveryIsDefined", "slsUnlmtdOvrdelivIsAllwd"],
        "nested_cols": [],
    },

    # ── Master Data: Products ─────────────────────────────────────────────
    "products": {
        "primary_keys": ["product"],
        "datetime_cols": ["creationDate", "lastChangeDate", "lastChangeDateTime", "crossPlantStatusValidityDate"],
        "numeric_cols": ["grossWeight", "netWeight"],
        "bool_cols": ["isMarkedForDeletion"],
        "nested_cols": [],
    },
    "product_descriptions": {
        "primary_keys": ["product", "language"],
        "datetime_cols": [],
        "numeric_cols": [],
        "bool_cols": [],
        "nested_cols": [],
    },
    "product_plants": {
        "primary_keys": ["product", "plant"],
        "datetime_cols": [],
        "numeric_cols": [],
        "bool_cols": [],
        "nested_cols": [],
    },
    "product_storage_locations": {
        "primary_keys": ["product", "plant", "storageLocation"],
        "datetime_cols": [],
        "numeric_cols": [],
        "bool_cols": [],
        "nested_cols": [],
    },

    # ── Master Data: Plants ───────────────────────────────────────────────
    "plants": {
        "primary_keys": ["plant"],
        "datetime_cols": [],
        "numeric_cols": [],
        "bool_cols": ["isMarkedForArchiving"],
        "nested_cols": [],
    },
}
