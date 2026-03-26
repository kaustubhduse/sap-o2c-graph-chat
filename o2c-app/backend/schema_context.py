"""
Generate schema context string for LLM prompts.
Includes table schemas, key relationships, and sample values.
"""
import logging
from database import get_table_names, get_table_schema, get_sample_values

logger = logging.getLogger(__name__)

# Key foreign-key relationships in the O2C dataset
RELATIONSHIPS = [
    ("sales_order_headers.soldToParty", "business_partners.businessPartner", "Customer who placed the sales order"),
    ("sales_order_items.salesOrder", "sales_order_headers.salesOrder", "Line items belonging to a sales order"),
    ("sales_order_items.material", "products.product", "Product ordered in a sales order item"),
    ("sales_order_schedule_lines.salesOrder", "sales_order_headers.salesOrder", "Schedule lines for sales order delivery"),
    ("outbound_delivery_items.referenceSdDocument", "sales_order_headers.salesOrder", "Sales order that this delivery fulfills"),
    ("outbound_delivery_items.deliveryDocument", "outbound_delivery_headers.deliveryDocument", "Delivery header for this item"),
    ("outbound_delivery_items.plant", "plants.plant", "Plant from which delivery is shipped"),
    ("billing_document_items.referenceSdDocument", "outbound_delivery_headers.deliveryDocument", "Delivery that this billing document bills"),
    ("billing_document_items.billingDocument", "billing_document_headers.billingDocument", "Billing header for this item"),
    ("billing_document_items.material", "products.product", "Product billed in this billing item"),
    ("billing_document_headers.soldToParty", "business_partners.businessPartner", "Customer billed"),
    ("billing_document_headers.cancelledBillingDocument", "billing_document_headers.billingDocument", "Original billing doc that was cancelled (for S1 cancellation docs)"),
    ("journal_entry_items_accounts_receivable.referenceDocument", "billing_document_headers.billingDocument", "Billing document that this journal entry accounts for"),
    ("journal_entry_items_accounts_receivable.customer", "business_partners.businessPartner", "Customer for this journal entry"),
    ("payments_accounts_receivable.customer", "business_partners.businessPartner", "Customer who made the payment"),
    ("payments_accounts_receivable.invoiceReference", "billing_document_headers.billingDocument", "Invoice/billing doc this payment references"),
    ("customer_company_assignments.customer", "business_partners.businessPartner", "Customer assigned to a company code"),
    ("customer_sales_area_assignments.customer", "business_partners.businessPartner", "Customer assigned to a sales area"),
    ("business_partner_addresses.businessPartner", "business_partners.businessPartner", "Address of the business partner"),
    ("product_descriptions.product", "products.product", "Description of the product"),
    ("product_plants.product", "products.product", "Product availability at plants"),
    ("product_plants.plant", "plants.plant", "Plant where product is available"),
    ("product_storage_locations.product", "products.product", "Storage location of a product"),
    ("product_storage_locations.plant", "plants.plant", "Plant of the storage location"),
]

# Human-readable description of each table
TABLE_DESCRIPTIONS = {
    "sales_order_headers": "Sales orders placed by customers",
    "sales_order_items": "Line items within sales orders (product, qty, amount)",
    "sales_order_schedule_lines": "Delivery schedule lines for sales order items",
    "outbound_delivery_headers": "Outbound deliveries (shipments) for sales orders",
    "outbound_delivery_items": "Line items within deliveries, links to sales orders via referenceSdDocument",
    "billing_document_headers": "Invoices/billing documents generated from deliveries",
    "billing_document_items": "Line items within billing docs, links to deliveries via referenceSdDocument",
    "billing_document_cancellations": "Cancelled billing documents (type S1)",
    "journal_entry_items_accounts_receivable": "Accounting journal entries for accounts receivable, links to billing docs via referenceDocument",
    "payments_accounts_receivable": "Customer payments received, links to customers and invoices",
    "business_partners": "Customers / business partners master data",
    "business_partner_addresses": "Addresses of business partners",
    "customer_company_assignments": "Customer assignments to company codes",
    "customer_sales_area_assignments": "Customer assignments to sales areas",
    "products": "Product master data",
    "product_descriptions": "Product text descriptions",
    "product_plants": "Product-plant assignments (availability)",
    "product_storage_locations": "Product storage location details",
    "plants": "Plant master data",
}


def build_schema_context():
    """
    Build a comprehensive schema context string for the LLM.
    Includes table names, columns, sample values, and relationships.
    """
    lines = []
    lines.append("=== DATABASE SCHEMA ===")
    lines.append("This is an SAP Order-to-Cash (O2C) dataset with the following tables:\n")

    for table_name in get_table_names():
        desc = TABLE_DESCRIPTIONS.get(table_name, "")
        lines.append(f"TABLE: {table_name}")
        if desc:
            lines.append(f"  Description: {desc}")

        schema = get_table_schema(table_name)
        col_parts = []
        for col in schema:
            samples = get_sample_values(table_name, col["name"], limit=2)
            sample_str = f" (e.g. {', '.join(repr(s) for s in samples)})" if samples else ""
            col_parts.append(f"    - {col['name']}{sample_str}")

        lines.append("  Columns:")
        lines.extend(col_parts)
        lines.append("")

    lines.append("=== KEY RELATIONSHIPS (Foreign Keys) ===")
    for src, tgt, desc in RELATIONSHIPS:
        lines.append(f"  {src} → {tgt}  ({desc})")

    lines.append("")
    lines.append("=== O2C FLOW ===")
    lines.append("Customer → Sales Order → Delivery → Billing Document → Journal Entry → Payment")
    lines.append("  - A sales order (soldToParty) links to a customer (businessPartner)")
    lines.append("  - Delivery items (referenceSdDocument) link back to the sales order")
    lines.append("  - Billing items (referenceSdDocument) link to the delivery document")
    lines.append("  - Journal entries (referenceDocument) link to the billing document")
    lines.append("  - Payments link to customers and invoice references")

    return "\n".join(lines)
