"""
Node construction logic.
Reads CSV data and creates Node objects.
"""
import logging
from src.utils import load_entity, safe_val, extract_props, add_node

logger = logging.getLogger(__name__)

def build_customer_nodes(nodes, ids):
    """Customer nodes from business_partners.csv"""
    df = load_entity("business_partners")
    pcols = ["customer", "businessPartnerCategory", "businessPartnerFullName",
             "businessPartnerGrouping", "businessPartnerIsBlocked",
             "organizationBPName1", "organizationBPName2"]
    for _, r in df.iterrows():
        bp = safe_val(r.get("businessPartner"))
        if not bp:
            continue
        label = safe_val(r.get("businessPartnerFullName")) or bp
        add_node(nodes, ids, f"Customer:{bp}", "Customer", label, extract_props(r, pcols))
    logger.info(f"  Customer nodes: {sum(1 for n in nodes if n['type']=='Customer')}")


def build_sales_order_nodes(nodes, ids):
    """SalesOrder nodes from sales_order_headers.csv"""
    df = load_entity("sales_order_headers")
    pcols = ["salesOrderType", "salesOrganization", "distributionChannel",
             "organizationDivision", "soldToParty", "creationDate",
             "totalNetAmount", "transactionCurrency", "overallDeliveryStatus",
             "requestedDeliveryDate", "customerPaymentTerms",
             "incotermsClassification", "incotermsLocation1"]
    for _, r in df.iterrows():
        so = safe_val(r.get("salesOrder"))
        if not so:
            continue
        add_node(nodes, ids, f"SalesOrder:{so}", "SalesOrder", f"SO-{so}", extract_props(r, pcols))
    logger.info(f"  SalesOrder nodes: {sum(1 for n in nodes if n['type']=='SalesOrder')}")


def build_product_nodes(nodes, ids):
    """Product nodes from products.csv (enriched with descriptions)."""
    df = load_entity("products")
    desc_df = load_entity("product_descriptions")
    desc_map = {}
    if not desc_df.empty:
        for _, r in desc_df.iterrows():
            p, d = safe_val(r.get("product")), safe_val(r.get("productDescription"))
            if p and d:
                desc_map[p] = d
    pcols = ["productType", "crossPlantStatus", "creationDate",
             "productGroup", "baseUnit", "grossWeight", "weightUnit"]
    for _, r in df.iterrows():
        prod = safe_val(r.get("product"))
        if not prod:
            continue
        label = desc_map.get(prod, prod)
        p = extract_props(r, pcols)
        if prod in desc_map:
            p["productDescription"] = desc_map[prod]
        add_node(nodes, ids, f"Product:{prod}", "Product", label, p)
    logger.info(f"  Product nodes: {sum(1 for n in nodes if n['type']=='Product')}")


def build_delivery_nodes(nodes, ids):
    """Delivery nodes from outbound_delivery_headers.csv"""
    df = load_entity("outbound_delivery_headers")
    pcols = ["creationDate", "actualGoodsMovementDate",
             "overallGoodsMovementStatus", "overallPickingStatus",
             "shippingPoint", "deliveryBlockReason"]
    for _, r in df.iterrows():
        dd = safe_val(r.get("deliveryDocument"))
        if not dd:
            continue
        add_node(nodes, ids, f"Delivery:{dd}", "Delivery", f"DLV-{dd}", extract_props(r, pcols))
    logger.info(f"  Delivery nodes: {sum(1 for n in nodes if n['type']=='Delivery')}")


def build_billing_nodes(nodes, ids):
    """BillingDocument nodes from billing_document_headers.csv"""
    df = load_entity("billing_document_headers")
    pcols = ["billingDocumentType", "billingDocumentDate", "creationDate",
             "billingDocumentIsCancelled", "cancelledBillingDocument",
             "totalNetAmount", "transactionCurrency", "companyCode",
             "soldToParty"]
    for _, r in df.iterrows():
        bd = safe_val(r.get("billingDocument"))
        if not bd:
            continue
        add_node(nodes, ids, f"BillingDocument:{bd}", "BillingDocument", f"INV-{bd}", extract_props(r, pcols))
    logger.info(f"  BillingDocument nodes: {sum(1 for n in nodes if n['type']=='BillingDocument')}")


def build_journal_nodes(nodes, ids):
    """JournalEntry nodes from journal_entry_items_accounts_receivable.csv
       Grouped by accountingDocument (one node per unique document)."""
    df = load_entity("journal_entry_items_accounts_receivable")
    pcols = ["companyCode", "fiscalYear", "postingDate", "documentDate",
             "accountingDocumentType", "transactionCurrency",
             "amountInTransactionCurrency"]
    seen = set()
    for _, r in df.iterrows():
        ad = safe_val(r.get("accountingDocument"))
        if not ad or ad in seen:
            continue
        seen.add(ad)
        add_node(nodes, ids, f"JournalEntry:{ad}", "JournalEntry", f"JE-{ad}", extract_props(r, pcols))
    logger.info(f"  JournalEntry nodes: {sum(1 for n in nodes if n['type']=='JournalEntry')}")


def build_payment_nodes(nodes, ids):
    """Payment nodes from payments_accounts_receivable.csv
       Grouped by accountingDocument."""
    df = load_entity("payments_accounts_receivable")
    pcols = ["companyCode", "fiscalYear", "postingDate", "documentDate",
             "amountInTransactionCurrency", "transactionCurrency",
             "clearingDate"]
    seen = set()
    for _, r in df.iterrows():
        ad = safe_val(r.get("accountingDocument"))
        if not ad or ad in seen:
            continue
        seen.add(ad)
        add_node(nodes, ids, f"Payment:{ad}", "Payment", f"PAY-{ad}", extract_props(r, pcols))
    logger.info(f"  Payment nodes: {sum(1 for n in nodes if n['type']=='Payment')}")


def build_plant_nodes(nodes, ids):
    """Plant nodes from plants.csv"""
    df = load_entity("plants")
    pcols = ["plantName", "valuationArea", "plantCustomer", "plantSupplier"]
    for _, r in df.iterrows():
        p = safe_val(r.get("plant"))
        if not p:
            continue
        label = safe_val(r.get("plantName")) or p
        add_node(nodes, ids, f"Plant:{p}", "Plant", label, extract_props(r, pcols))
    logger.info(f"  Plant nodes: {sum(1 for n in nodes if n['type']=='Plant')}")
