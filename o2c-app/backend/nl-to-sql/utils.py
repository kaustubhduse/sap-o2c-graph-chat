"""
Utility functions for the NL-to-SQL pipeline.
Includes: SQL cleaning, entity ID extraction, guardrail keyword check,
and table description builder.
"""
import re
import logging

logger = logging.getLogger(__name__)

# ── Table descriptions for dynamic selection ──────────────────────────
TABLE_DESCRIPTIONS = {
    "sales_order_headers": "Sales orders placed by customers (soldToParty, totalNetAmount, deliveryStatus, billingStatus)",
    "sales_order_items": "Line items in sales orders (material/product, quantity, netAmount, productionPlant)",
    "sales_order_schedule_lines": "Delivery schedule lines for sales order items (confirmedDeliveryDate)",
    "outbound_delivery_headers": "Outbound deliveries / shipments (goodsMovementDate, pickingStatus, shippingPoint)",
    "outbound_delivery_items": "Delivery line items linking to sales orders via referenceSdDocument (plant, quantity)",
    "billing_document_headers": "Invoices / billing documents (totalNetAmount, soldToParty, cancelledBillingDocument)",
    "billing_document_items": "Billing line items linking to deliveries via referenceSdDocument (material, netAmount)",
    "billing_document_cancellations": "Cancelled billing documents (type S1)",
    "journal_entry_items_accounts_receivable": "Accounting journal entries for AR, links to billing via referenceDocument",
    "payments_accounts_receivable": "Customer payments received, links to invoices via invoiceReference",
    "business_partners": "Customers / business partners (name, category, industry)",
    "business_partner_addresses": "Addresses of business partners (city, country, region)",
    "customer_company_assignments": "Customer to company code assignments (paymentTerms, reconciliationAccount)",
    "customer_sales_area_assignments": "Customer to sales area assignments (salesOrg, distributionChannel)",
    "products": "Product master data (productType, weight, productGroup, baseUnit)",
    "product_descriptions": "Product text descriptions (productDescription, language)",
    "product_plants": "Product-plant assignments (countryOfOrigin, profitCenter)",
    "product_storage_locations": "Product storage location details",
    "plants": "Plant master data (plantName, salesOrganization, distributionChannel)",
}


def get_table_descriptions_text():
    """Format table descriptions for the table selection prompt."""
    return "\n".join(f"- {name}: {desc}" for name, desc in TABLE_DESCRIPTIONS.items())


# ── SQL Cleaning ──────────────────────────────────────────────────────
def clean_sql(raw_sql: str) -> str:
    """
    Clean LLM-generated SQL:
    - Remove markdown code fences
    - Strip whitespace
    - Ensure single statement
    """
    sql = raw_sql.strip()

    # Remove markdown backticks
    if sql.startswith("```"):
        lines = sql.split("\n")
        sql = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        )

    # Remove leading 'sql' keyword if present
    sql = sql.strip()
    if sql.lower().startswith("sql\n"):
        sql = sql[4:]
    if sql.lower().startswith("sql "):
        sql = sql[4:]

    sql = sql.strip().rstrip(";") + ";"
    return sql


# ── Entity ID Extraction for Graph Highlighting ──────────────────────
# Patterns for known O2C entity IDs
ID_PATTERNS = {
    "SalesOrder":       re.compile(r"\b(7[34]\d{4})\b"),
    "Delivery":         re.compile(r"\b(80\d{6})\b"),
    "BillingDocument":  re.compile(r"\b(9[01]\d{6})\b"),
    "Customer":         re.compile(r"\b(3[12]\d{7})\b"),
    "JournalEntry":     re.compile(r"\b(94\d{8})\b"),
    "Payment":          re.compile(r"\b(PAY[-_]?\d+)\b", re.IGNORECASE),
    "Product":          re.compile(r"\b(MZ[-_]\w+|TG[-_]\w+|[A-Z]{2,}-\w+)\b"),
    "Plant":            re.compile(r"\b(1[0-9]{3})\b"),
}


def extract_entity_ids(result_str: str, sql: str) -> list:
    """
    Extract entity IDs from SQL results for graph node highlighting.
    Returns a list of dicts: [{type, id}, ...]
    """
    found = []
    seen = set()

    # Also scan the SQL to understand which entity types are involved
    sql_lower = sql.lower()
    relevant_types = set()
    # Table names use sales_order_*; columns often use salesOrder (no underscore).
    if "sales_order" in sql_lower or "salesorder" in sql_lower:
        relevant_types.add("SalesOrder")
    if "delivery" in sql_lower or "outbound" in sql_lower:
        relevant_types.add("Delivery")
    if "billing" in sql_lower:
        relevant_types.add("BillingDocument")
    if "business_partner" in sql_lower or "customer" in sql_lower:
        relevant_types.add("Customer")
    if "journal" in sql_lower:
        relevant_types.add("JournalEntry")
    if "payment" in sql_lower:
        relevant_types.add("Payment")
    if "product" in sql_lower:
        relevant_types.add("Product")
    if "plant" in sql_lower:
        relevant_types.add("Plant")

    # If no specific types detected, check all
    types_to_check = relevant_types if relevant_types else set(ID_PATTERNS.keys())

    # Literals like shipping points (e.g. 1920) must not be scanned from raw SQL as Plant IDs.
    SKIP_SQL_LITERAL_SCAN = frozenset({"Plant", "Product"})

    def add_match(entity_type: str, entity_id: str) -> None:
        key = f"{entity_type}:{entity_id}"
        if key not in seen:
            seen.add(key)
            found.append({"type": entity_type, "id": entity_id, "graphNodeId": key})

    for entity_type in types_to_check:
        pattern = ID_PATTERNS.get(entity_type)
        if not pattern:
            continue
        for match in pattern.finditer(result_str):
            add_match(entity_type, match.group(1))
        if entity_type in SKIP_SQL_LITERAL_SCAN:
            continue
        # WHERE / JOIN clauses often hold the sales order, delivery, etc. even when the
        # result set only projects other columns (UNION queries).
        for match in pattern.finditer(sql):
            add_match(entity_type, match.group(1))

    # Payment graph IDs are often numeric AR documents (same shape as journal); SQL rarely uses PAY-…
    if "Payment" in types_to_check and (
        "payments_accounts" in sql_lower or "payments_ar" in sql_lower
    ):
        for match in re.finditer(r"\b(94\d{8})\b", sql):
            add_match("Payment", match.group(1))

    return found


# ── Guardrail keyword check (fast path) ──────────────────────────────
ON_TOPIC_KEYWORDS = [
    "sales order", "order", "billing", "invoice", "delivery", "shipment",
    "payment", "paid", "customer", "partner", "product", "material",
    "plant", "warehouse", "journal", "accounting", "sap", "o2c",
    "revenue", "amount", "total", "cancelled", "blocked", "incomplete",
    "top", "highest", "lowest", "most", "average", "count", "how many",
    "list", "show", "find", "which", "trace", "flow", "track",
    "company code", "fiscal year", "currency", "schedule",
]

OFF_TOPIC_PATTERNS = [
    "write me a", "poem", "story", "joke", "song",
    "capital of", "president of", "who invented",
    "recipe", "cook", "weather", "stock price", "crypto",
    "play a game", "tic tac toe", "translate",
    "meaning of life", "who are you", "what are you",
    "homework",
]


def keyword_guardrail(query: str):
    """
    Fast keyword-based guardrail.
    Returns: 'on_topic', 'off_topic', or 'uncertain'
    """
    q = query.lower().strip()
    for pattern in OFF_TOPIC_PATTERNS:
        if pattern in q:
            return "off_topic"
    for keyword in ON_TOPIC_KEYWORDS:
        if keyword in q:
            return "on_topic"
    return "uncertain"
