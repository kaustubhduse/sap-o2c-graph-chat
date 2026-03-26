"""
Data Joiners for SAP O2C Pipeline.

Creates enriched, joined datasets from normalized entity DataFrames:
  - sales_orders_full:       Headers + Items + Schedule Lines
  - deliveries_full:         Delivery Headers + Items
  - billing_documents_full:  Billing Headers + Items
  - products_full:           Products + Descriptions
  - customers_full:          Business Partners + Addresses + Assignments
  - o2c_flow:                End-to-end Order→Delivery→Billing→JournalEntry→Payment chain
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def _safe_merge(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: str | list[str],
    how: str = "left",
    suffixes: tuple[str, str] = ("", "_right"),
    label: str = "",
) -> pd.DataFrame:
    """Merge two DataFrames with logging of match statistics."""
    if left.empty or right.empty:
        logger.warning(f"  [{label}] Skipped — one or both sides empty")
        return left

    result = left.merge(right, on=on, how=how, suffixes=suffixes)
    matched = result[right.columns[0]].notna().sum() if how == "left" else len(result)
    logger.info(
        f"  [{label}] Merged: {len(left)} × {len(right)} → {len(result)} rows "
        f"({matched} matched)"
    )
    return result


def join_sales_orders(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Join Sales Order Headers + Items + Schedule Lines.
    Result: one row per schedule line (finest granularity).
    """
    logger.info("Building [sales_orders_full]...")

    headers = data.get("sales_order_headers", pd.DataFrame())
    items = data.get("sales_order_items", pd.DataFrame())
    schedule = data.get("sales_order_schedule_lines", pd.DataFrame())

    if headers.empty:
        logger.warning("  No sales_order_headers data — skipping")
        return pd.DataFrame()

    # Headers + Items (one-to-many on salesOrder)
    result = _safe_merge(
        items, headers,
        on="salesOrder", how="left",
        suffixes=("_item", "_header"),
        label="items ← headers",
    )

    # + Schedule Lines (one-to-many on salesOrder + salesOrderItem)
    if not schedule.empty:
        result = _safe_merge(
            result, schedule,
            on=["salesOrder", "salesOrderItem"], how="left",
            suffixes=("", "_sched"),
            label="+ schedule_lines",
        )

    logger.info(f"  [sales_orders_full] Final: {len(result)} rows, {len(result.columns)} cols")
    return result


def join_deliveries(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Join Delivery Headers + Items.
    Result: one row per delivery item.
    """
    logger.info("Building [deliveries_full]...")

    headers = data.get("outbound_delivery_headers", pd.DataFrame())
    items = data.get("outbound_delivery_items", pd.DataFrame())

    if items.empty:
        logger.warning("  No outbound_delivery_items data — skipping")
        return pd.DataFrame()

    result = _safe_merge(
        items, headers,
        on="deliveryDocument", how="left",
        suffixes=("_item", "_header"),
        label="items ← headers",
    )

    logger.info(f"  [deliveries_full] Final: {len(result)} rows, {len(result.columns)} cols")
    return result


def join_billing_documents(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Join Billing Document Headers + Items.
    Result: one row per billing item.
    """
    logger.info("Building [billing_documents_full]...")

    headers = data.get("billing_document_headers", pd.DataFrame())
    items = data.get("billing_document_items", pd.DataFrame())

    if items.empty:
        logger.warning("  No billing_document_items data — skipping")
        return pd.DataFrame()

    result = _safe_merge(
        items, headers,
        on="billingDocument", how="left",
        suffixes=("_item", "_header"),
        label="items ← headers",
    )

    logger.info(f"  [billing_documents_full] Final: {len(result)} rows, {len(result.columns)} cols")
    return result


def join_products(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Join Products + Descriptions (EN only for simplicity).
    Result: one row per product with description.
    """
    logger.info("Building [products_full]...")

    products = data.get("products", pd.DataFrame())
    descriptions = data.get("product_descriptions", pd.DataFrame())

    if products.empty:
        logger.warning("  No products data — skipping")
        return pd.DataFrame()

    # Filter descriptions to English only
    if not descriptions.empty and "language" in descriptions.columns:
        descriptions = descriptions[descriptions["language"] == "EN"].copy()
        descriptions = descriptions.drop(columns=["language"], errors="ignore")

    result = _safe_merge(
        products, descriptions,
        on="product", how="left",
        label="products ← descriptions",
    )

    logger.info(f"  [products_full] Final: {len(result)} rows, {len(result.columns)} cols")
    return result


def join_customers(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Join Business Partners + Addresses + Company Assignments + Sales Area Assignments.
    Result: one row per customer with address and assignment info.
    """
    logger.info("Building [customers_full]...")

    bp = data.get("business_partners", pd.DataFrame())
    addr = data.get("business_partner_addresses", pd.DataFrame())
    comp = data.get("customer_company_assignments", pd.DataFrame())

    if bp.empty:
        logger.warning("  No business_partners data — skipping")
        return pd.DataFrame()

    # BP + Addresses
    result = _safe_merge(
        bp, addr,
        on="businessPartner", how="left",
        suffixes=("", "_addr"),
        label="bp ← addresses",
    )

    # + Company assignments (join on customer = businessPartner)
    if not comp.empty:
        comp_renamed = comp.copy()
        if "customer" in comp_renamed.columns:
            comp_renamed = comp_renamed.rename(columns={"customer": "businessPartner"})
        result = _safe_merge(
            result, comp_renamed,
            on="businessPartner", how="left",
            suffixes=("", "_comp"),
            label="+ company_assignments",
        )

    logger.info(f"  [customers_full] Final: {len(result)} rows, {len(result.columns)} cols")
    return result


def join_o2c_flow(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build the end-to-end Order-to-Cash flow:
        Sales Order → Delivery → Billing → Journal Entry → Payment

    Linking logic:
        1. Delivery Items → Sales Orders via referenceSdDocument = salesOrder
        2. Billing Items → Deliveries via referenceSdDocument = deliveryDocument
        3. Billing Headers → billing items via billingDocument
        4. Journal Entries → Billing via referenceDocument = billingDocument
        5. Payments → Journal Entries via accountingDocument

    Result: one row per billing item tracing through the full chain.
    """
    logger.info("Building [o2c_flow]...")

    so_headers = data.get("sales_order_headers", pd.DataFrame())
    so_items = data.get("sales_order_items", pd.DataFrame())
    del_items = data.get("outbound_delivery_items", pd.DataFrame())
    del_headers = data.get("outbound_delivery_headers", pd.DataFrame())
    bill_headers = data.get("billing_document_headers", pd.DataFrame())
    bill_items = data.get("billing_document_items", pd.DataFrame())
    journal = data.get("journal_entry_items_accounts_receivable", pd.DataFrame())
    payments = data.get("payments_accounts_receivable", pd.DataFrame())
    bp = data.get("business_partners", pd.DataFrame())
    prod_desc = data.get("product_descriptions", pd.DataFrame())

    if bill_items.empty:
        logger.warning("  No billing_document_items — cannot build O2C flow")
        return pd.DataFrame()

    # ── Step 1: Start from billing items and link to delivery docs ────────
    # Billing Items reference deliveries via referenceSdDocument
    flow = bill_items.copy()
    flow = flow.rename(columns={
        "referenceSdDocument": "deliveryDocument",
        "referenceSdDocumentItem": "deliveryDocumentItem",
    })

    # ── Step 2: Join billing headers for invoice-level info ───────────────
    if not bill_headers.empty:
        bill_header_cols = ["billingDocument", "billingDocumentType", "billingDocumentDate",
                           "billingDocumentIsCancelled", "totalNetAmount", "soldToParty",
                           "accountingDocument", "companyCode", "fiscalYear"]
        bill_header_cols = [c for c in bill_header_cols if c in bill_headers.columns]
        flow = _safe_merge(
            flow, bill_headers[bill_header_cols],
            on="billingDocument", how="left",
            suffixes=("_item", "_header"),
            label="billing_items ← billing_headers",
        )

    # ── Step 3: Link delivery items to get salesOrder reference ───────────
    if not del_items.empty:
        del_link_cols = ["deliveryDocument", "deliveryDocumentItem",
                         "referenceSdDocument", "referenceSdDocumentItem",
                         "actualDeliveryQuantity", "plant"]
        del_link_cols = [c for c in del_link_cols if c in del_items.columns]
        flow = _safe_merge(
            flow, del_items[del_link_cols],
            on=["deliveryDocument", "deliveryDocumentItem"], how="left",
            label="+ delivery_items (for SO reference)",
        )

    # ── Step 4: Link delivery headers ─────────────────────────────────────
    if not del_headers.empty:
        del_hdr_cols = ["deliveryDocument", "overallGoodsMovementStatus",
                        "overallPickingStatus", "shippingPoint"]
        del_hdr_cols = [c for c in del_hdr_cols if c in del_headers.columns]
        if del_hdr_cols:
            flow = _safe_merge(
                flow, del_headers[del_hdr_cols],
                on="deliveryDocument", how="left",
                label="+ delivery_headers",
            )

    # ── Step 5: Link sales order headers ──────────────────────────────────
    if not so_headers.empty and "referenceSdDocument" in flow.columns:
        so_cols = ["salesOrder", "salesOrderType", "soldToParty",
                   "overallDeliveryStatus", "totalNetAmount",
                   "requestedDeliveryDate", "transactionCurrency"]
        so_cols = [c for c in so_cols if c in so_headers.columns]
        flow = flow.rename(columns={"referenceSdDocument": "salesOrder"})
        if "referenceSdDocumentItem" in flow.columns:
            flow = flow.rename(columns={"referenceSdDocumentItem": "salesOrderItem"})
        flow = _safe_merge(
            flow, so_headers[so_cols],
            on="salesOrder", how="left",
            suffixes=("", "_so"),
            label="+ sales_order_headers",
        )

    # ── Step 6: Link journal entries via accountingDocument ───────────────
    if not journal.empty and "accountingDocument" in flow.columns:
        je_cols = ["accountingDocument", "glAccount", "postingDate",
                   "amountInTransactionCurrency", "clearingDate",
                   "clearingAccountingDocument", "customer"]
        je_cols = [c for c in je_cols if c in journal.columns]
        # Use first journal entry item per accounting doc for header-level link
        je_deduped = journal[je_cols].drop_duplicates(subset=["accountingDocument"], keep="first")
        flow = _safe_merge(
            flow, je_deduped,
            on="accountingDocument", how="left",
            suffixes=("", "_je"),
            label="+ journal_entries",
        )

    # ── Step 7: Link payments via clearingAccountingDocument ──────────────
    if not payments.empty and "clearingAccountingDocument" in flow.columns:
        pmt_cols = ["accountingDocument", "amountInTransactionCurrency",
                    "postingDate", "clearingDate", "customer"]
        pmt_cols = [c for c in pmt_cols if c in payments.columns]
        pmt_deduped = payments[pmt_cols].drop_duplicates(
            subset=["accountingDocument"], keep="first"
        )
        pmt_deduped = pmt_deduped.rename(columns={
            "accountingDocument": "clearingAccountingDocument",
            "amountInTransactionCurrency": "paymentAmount",
            "postingDate": "paymentDate",
            "clearingDate": "paymentClearingDate",
            "customer": "paymentCustomer",
        })
        flow = _safe_merge(
            flow, pmt_deduped,
            on="clearingAccountingDocument", how="left",
            label="+ payments",
        )

    # ── Step 8: Enrich with customer name ─────────────────────────────────
    if not bp.empty and "soldToParty" in flow.columns:
        bp_name = bp[["businessPartner", "businessPartnerName"]].copy()
        bp_name = bp_name.rename(columns={
            "businessPartner": "soldToParty",
            "businessPartnerName": "customerName",
        })
        flow = _safe_merge(
            flow, bp_name,
            on="soldToParty", how="left",
            label="+ customer_name",
        )

    # ── Step 9: Enrich with product description ───────────────────────────
    if not prod_desc.empty and "material" in flow.columns:
        pd_en = prod_desc[prod_desc.get("language", pd.Series()) == "EN"] if "language" in prod_desc.columns else prod_desc
        if not pd_en.empty:
            pd_en = pd_en[["product", "productDescription"]].copy()
            pd_en = pd_en.rename(columns={"product": "material"})
            pd_en = pd_en.drop_duplicates(subset=["material"], keep="first")
            flow = _safe_merge(
                flow, pd_en,
                on="material", how="left",
                label="+ product_description",
            )

    logger.info(f"  [o2c_flow] Final: {len(flow)} rows, {len(flow.columns)} cols")
    return flow


def build_all_joins(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Build all joined datasets."""
    return {
        "sales_orders_full": join_sales_orders(data),
        "deliveries_full": join_deliveries(data),
        "billing_documents_full": join_billing_documents(data),
        "products_full": join_products(data),
        "customers_full": join_customers(data),
        "o2c_flow": join_o2c_flow(data),
    }
