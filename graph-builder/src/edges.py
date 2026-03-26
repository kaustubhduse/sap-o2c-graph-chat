"""
Edge construction logic.
Reads CSV data and creates relationships between Node objects.
"""
import logging
from collections import Counter
from src.utils import load_entity, safe_val, add_edge

logger = logging.getLogger(__name__)


def build_all_edges(edges, eids, nids):
    """Build every edge type from the user-provided relationship schema."""

    # -- 1. CUSTOMER & MASTER DATA ------------------------------------------

    # business_partner_addresses.businessPartner -> business_partners.businessPartner
    df = load_entity("business_partner_addresses")
    for _, r in df.iterrows():
        bp = safe_val(r.get("businessPartner"))
        aid = safe_val(r.get("addressId"))
        if bp and f"Customer:{bp}" in nids:
            add_edge(edges, eids, f"Customer:{bp}", f"Customer:{bp}",
                      "HAS_ADDRESS", {"addressId": aid or ""})

    # customer_company_assignments.customer -> business_partners.businessPartner
    df = load_entity("customer_company_assignments")
    for _, r in df.iterrows():
        c = safe_val(r.get("customer"))
        cc = safe_val(r.get("companyCode"))
        if c and f"Customer:{c}" in nids:
            add_edge(edges, eids, f"Customer:{c}", f"Customer:{c}",
                      "ASSIGNED_TO_COMPANY", {"companyCode": cc or ""})

    # customer_sales_area_assignments.customer -> business_partners.businessPartner
    df = load_entity("customer_sales_area_assignments")
    for _, r in df.iterrows():
        c = safe_val(r.get("customer"))
        if c and f"Customer:{c}" in nids:
            add_edge(edges, eids, f"Customer:{c}", f"Customer:{c}",
                      "ASSIGNED_TO_SALES_AREA",
                      {"salesOrganization": safe_val(r.get("salesOrganization")) or "",
                       "distributionChannel": safe_val(r.get("distributionChannel")) or "",
                       "division": safe_val(r.get("division")) or ""})

    # -- 2. CUSTOMER -> SALES ORDER -----------------------------------------

    # sales_order_headers.soldToParty -> business_partners.businessPartner
    df = load_entity("sales_order_headers")
    for _, r in df.iterrows():
        so = safe_val(r.get("salesOrder"))
        bp = safe_val(r.get("soldToParty"))
        if so and bp:
            add_edge(edges, eids, f"SalesOrder:{so}", f"Customer:{bp}", "PLACED_BY")

    # -- 3. SALES ORDER STRUCTURE -------------------------------------------

    # sales_order_items.salesOrder -> sales_order_headers.salesOrder
    # + sales_order_items.material -> products.product
    df = load_entity("sales_order_items")
    for _, r in df.iterrows():
        so = safe_val(r.get("salesOrder"))
        item = safe_val(r.get("salesOrderItem"))
        mat = safe_val(r.get("material"))
        if so and mat:
            add_edge(edges, eids, f"SalesOrder:{so}", f"Product:{mat}",
                      "CONTAINS_ITEM",
                      {"salesOrderItem": item or "",
                       "requestedQuantity": safe_val(r.get("requestedQuantity")) or ""})

    # sales_order_schedule_lines -> sales_order_items (self-ref on SalesOrder)
    df = load_entity("sales_order_schedule_lines")
    for _, r in df.iterrows():
        so = safe_val(r.get("salesOrder"))
        item = safe_val(r.get("salesOrderItem"))
        line = safe_val(r.get("scheduleLine"))
        if so and f"SalesOrder:{so}" in nids:
            add_edge(edges, eids, f"SalesOrder:{so}", f"SalesOrder:{so}",
                      "HAS_SCHEDULE_LINE",
                      {"salesOrderItem": item or "", "scheduleLine": line or ""})

    # -- 4. PRODUCT RELATIONSHIPS -------------------------------------------

    # product_plants.product -> products.product  AND  product_plants.plant -> plants.plant
    df = load_entity("product_plants")
    for _, r in df.iterrows():
        prod = safe_val(r.get("product"))
        plant = safe_val(r.get("plant"))
        if prod and plant:
            add_edge(edges, eids, f"Product:{prod}", f"Plant:{plant}", "AVAILABLE_AT")

    # product_storage_locations.product -> products.product (storage detail)
    df = load_entity("product_storage_locations")
    for _, r in df.iterrows():
        prod = safe_val(r.get("product"))
        plant = safe_val(r.get("plant"))
        sl = safe_val(r.get("storageLocation"))
        if prod and plant:
            add_edge(edges, eids, f"Product:{prod}", f"Plant:{plant}",
                      "STORED_AT", {"storageLocation": sl or ""})

    # -- 5. DELIVERY LAYER --------------------------------------------------

    # outbound_delivery_items.referenceSdDocument -> sales_order_headers.salesOrder
    # outbound_delivery_items.plant -> plants.plant
    df = load_entity("outbound_delivery_items")
    for _, r in df.iterrows():
        dd = safe_val(r.get("deliveryDocument"))
        ref = safe_val(r.get("referenceSdDocument"))
        plant = safe_val(r.get("plant"))
        di = safe_val(r.get("deliveryDocumentItem"))
        if dd and ref:
            add_edge(edges, eids, f"Delivery:{dd}", f"SalesOrder:{ref}",
                      "FULFILLS", {"deliveryDocumentItem": di or ""})
        if dd and plant:
            add_edge(edges, eids, f"Delivery:{dd}", f"Plant:{plant}", "DELIVERED_FROM")

    # -- 6. BILLING LAYER ---------------------------------------------------

    # billing_document_items.referenceSdDocument -> outbound_delivery_headers.deliveryDocument
    # billing_document_items.material -> products.product
    df = load_entity("billing_document_items")
    for _, r in df.iterrows():
        bd = safe_val(r.get("billingDocument"))
        ref = safe_val(r.get("referenceSdDocument"))
        mat = safe_val(r.get("material"))
        bi = safe_val(r.get("billingDocumentItem"))
        if bd and ref:
            add_edge(edges, eids, f"BillingDocument:{bd}", f"Delivery:{ref}",
                      "BILLS", {"billingDocumentItem": bi or ""})
        if bd and mat:
            add_edge(edges, eids, f"BillingDocument:{bd}", f"Product:{mat}",
                      "BILLS_PRODUCT",
                      {"billingDocumentItem": bi or "",
                       "netAmount": safe_val(r.get("netAmount")) or ""})

    # billing_document_headers.soldToParty -> business_partners.businessPartner
    df = load_entity("billing_document_headers")
    for _, r in df.iterrows():
        bd = safe_val(r.get("billingDocument"))
        bp = safe_val(r.get("soldToParty"))
        cancelled = safe_val(r.get("cancelledBillingDocument"))
        if bd and bp:
            add_edge(edges, eids, f"BillingDocument:{bd}", f"Customer:{bp}", "BILLED_TO")
        # billing_document_cancellations: S1 doc cancels an F2 doc
        if bd and cancelled:
            add_edge(edges, eids, f"BillingDocument:{bd}", f"BillingDocument:{cancelled}", "CANCELS")

    # -- 7. ACCOUNTING ------------------------------------------------------

    # journal_entry_items_AR.referenceDocument -> billing_document_headers.billingDocument
    # journal_entry_items_AR.customer -> business_partners.businessPartner
    df = load_entity("journal_entry_items_accounts_receivable")
    for _, r in df.iterrows():
        ad = safe_val(r.get("accountingDocument"))
        ref = safe_val(r.get("referenceDocument"))
        cust = safe_val(r.get("customer"))
        if ad and ref:
            add_edge(edges, eids, f"JournalEntry:{ad}", f"BillingDocument:{ref}", "ACCOUNTS_FOR")
        if ad and cust:
            add_edge(edges, eids, f"JournalEntry:{ad}", f"Customer:{cust}", "JOURNAL_FOR_CUSTOMER")

    # -- 8. PAYMENT ---------------------------------------------------------

    # payments_accounts_receivable.accountingDocument -> journal_entry_items_AR.accountingDocument
    # payments_accounts_receivable.customer -> business_partners.businessPartner
    je_ids = {nid.split(":", 1)[1] for nid in nids if nid.startswith("JournalEntry:")}

    df = load_entity("payments_accounts_receivable")
    for _, r in df.iterrows():
        ad = safe_val(r.get("accountingDocument"))
        cust = safe_val(r.get("customer"))
        if ad and ad in je_ids:
            add_edge(edges, eids, f"Payment:{ad}", f"JournalEntry:{ad}", "PAYS")
        if ad and cust:
            add_edge(edges, eids, f"Payment:{ad}", f"Customer:{cust}", "PAID_BY")

    # Log edge counts
    edge_counts = Counter(e["type"] for e in edges)
    for t, c in sorted(edge_counts.items()):
        logger.info(f"  {t}: {c}")
