"""
Few-shot examples for the NL-to-SQL pipeline.
These examples teach the LLM how to write correct SQL for SAP O2C domain queries.
Each example includes: input (natural language), query (correct SQL).
"""

EXAMPLES = [
    # ── Customer → Order queries ──────────────────────────────────────
    {
        "input": "Which customer has placed the most sales orders?",
        "query": (
            "SELECT soh.soldToParty, bp.businessPartnerFullName, "
            "COUNT(*) AS order_count "
            "FROM sales_order_headers soh "
            "JOIN business_partners bp ON soh.soldToParty = bp.businessPartner "
            "GROUP BY soh.soldToParty, bp.businessPartnerFullName "
            "ORDER BY order_count DESC LIMIT 5;"
        ),
    },
    {
        "input": "Show me all sales orders for customer 320000083",
        "query": (
            "SELECT salesOrder, salesOrderType, creationDate, totalNetAmount, "
            "transactionCurrency, overallDeliveryStatus "
            "FROM sales_order_headers "
            "WHERE soldToParty = '320000083' "
            "ORDER BY creationDate DESC;"
        ),
    },
    {
        "input": "What is the total order value per customer?",
        "query": (
            "SELECT soh.soldToParty, bp.businessPartnerFullName, "
            "SUM(CAST(soh.totalNetAmount AS DECIMAL(15,2))) AS total_value, "
            "soh.transactionCurrency "
            "FROM sales_order_headers soh "
            "JOIN business_partners bp ON soh.soldToParty = bp.businessPartner "
            "GROUP BY soh.soldToParty, bp.businessPartnerFullName, soh.transactionCurrency "
            "ORDER BY total_value DESC;"
        ),
    },
    {
        "input": "List all products ordered in sales order 740599",
        "query": (
            "SELECT soi.material, pd.productDescription, soi.requestedQuantity, "
            "soi.requestedQuantityUnit, soi.netAmount "
            "FROM sales_order_items soi "
            "LEFT JOIN product_descriptions pd ON soi.material = pd.product AND pd.language = 'EN' "
            "WHERE soi.salesOrder = '740599';"
        ),
    },

    # ── Delivery → Billing queries ────────────────────────────────────
    {
        "input": "Which sales orders have been delivered but not yet billed?",
        "query": (
            "SELECT DISTINCT soh.salesOrder, soh.soldToParty, soh.totalNetAmount, "
            "soh.overallDeliveryStatus, soh.overallOrdReltdBillgStatus "
            "FROM sales_order_headers soh "
            "WHERE soh.overallDeliveryStatus = 'C' "
            "AND soh.overallOrdReltdBillgStatus != 'C';"
        ),
    },
    {
        "input": "Trace the full flow of billing document 91150186",
        "query": (
            "SELECT 'BillingDoc' AS step, bdh.billingDocument AS id, "
            "bdh.totalNetAmount AS amount, bdh.billingDocumentDate AS doc_date "
            "FROM billing_document_headers bdh "
            "WHERE bdh.billingDocument = '91150186' "
            "UNION ALL "
            "SELECT 'Delivery' AS step, odi.deliveryDocument AS id, "
            "NULL AS amount, odh.creationDate AS doc_date "
            "FROM billing_document_items bdi "
            "JOIN outbound_delivery_items odi ON bdi.referenceSdDocument = odi.deliveryDocument "
            "JOIN outbound_delivery_headers odh ON odi.deliveryDocument = odh.deliveryDocument "
            "WHERE bdi.billingDocument = '91150186' "
            "UNION ALL "
            "SELECT 'SalesOrder' AS step, odi2.referenceSdDocument AS id, "
            "soh.totalNetAmount AS amount, soh.creationDate AS doc_date "
            "FROM billing_document_items bdi2 "
            "JOIN outbound_delivery_items odi2 ON bdi2.referenceSdDocument = odi2.deliveryDocument "
            "JOIN sales_order_headers soh ON odi2.referenceSdDocument = soh.salesOrder "
            "WHERE bdi2.billingDocument = '91150186';"
        ),
    },
    {
        "input": "Which products are associated with the highest number of billing documents?",
        "query": (
            "SELECT bdi.material, pd.productDescription, "
            "COUNT(DISTINCT bdi.billingDocument) AS billing_count "
            "FROM billing_document_items bdi "
            "LEFT JOIN product_descriptions pd ON bdi.material = pd.product AND pd.language = 'EN' "
            "GROUP BY bdi.material, pd.productDescription "
            "ORDER BY billing_count DESC LIMIT 10;"
        ),
    },
    {
        "input": "Show all deliveries from plant 1710",
        "query": (
            "SELECT odi.deliveryDocument, odi.referenceSdDocument, "
            "odi.actualDeliveryQuantity, odh.actualGoodsMovementDate "
            "FROM outbound_delivery_items odi "
            "JOIN outbound_delivery_headers odh ON odi.deliveryDocument = odh.deliveryDocument "
            "WHERE odi.plant = '1710' "
            "ORDER BY odh.actualGoodsMovementDate DESC;"
        ),
    },
    {
        "input": (
            "For a sales order, show customer name, order line material, delivery document, billing document, "
            "journal AR accounting document, and payment accounting document. Join like the property graph: "
            "delivery items on referenceSdDocument = sales order; billing items on referenceSdDocument = delivery document; "
            "journal AR on referenceDocument = billing document; payment on accountingDocument = journal accountingDocument. "
            "Use LEFT JOIN from sales_order_headers so billing/journal/payment can be missing."
        ),
        "query": (
            "SELECT bp.businessPartnerFullName AS customer_name, "
            "soh.salesOrder, soi.material, odh.deliveryDocument, "
            "bdh.billingDocument, jei.accountingDocument AS ar_accountingDocument, "
            "par.accountingDocument AS payment_accountingDocument "
            "FROM sales_order_headers soh "
            "LEFT JOIN business_partners bp ON soh.soldToParty = bp.businessPartner "
            "LEFT JOIN sales_order_items soi ON soh.salesOrder = soi.salesOrder "
            "LEFT JOIN outbound_delivery_items odi ON soh.salesOrder = odi.referenceSdDocument "
            "LEFT JOIN outbound_delivery_headers odh ON odi.deliveryDocument = odh.deliveryDocument "
            "LEFT JOIN billing_document_items bdi ON odh.deliveryDocument = bdi.referenceSdDocument "
            "LEFT JOIN billing_document_headers bdh ON bdi.billingDocument = bdh.billingDocument "
            "LEFT JOIN journal_entry_items_accounts_receivable jei ON bdh.billingDocument = jei.referenceDocument "
            "LEFT JOIN payments_accounts_receivable par ON jei.accountingDocument = par.accountingDocument "
            "WHERE soh.salesOrder = '740506' "
            "LIMIT 50;"
        ),
    },

    # ── Payment tracking queries ──────────────────────────────────────
    {
        "input": "Show me all payments for customer 320000083",
        "query": (
            "SELECT accountingDocument, postingDate, "
            "amountInTransactionCurrency, transactionCurrency, "
            "invoiceReference, clearingDate "
            "FROM payments_accounts_receivable "
            "WHERE customer = '320000083' "
            "ORDER BY postingDate DESC;"
        ),
    },
    {
        "input": "Which invoices have not been paid yet?",
        "query": (
            "SELECT bdh.billingDocument, bdh.soldToParty, "
            "bdh.totalNetAmount, bdh.billingDocumentDate "
            "FROM billing_document_headers bdh "
            "WHERE bdh.billingDocumentIsCancelled = '' "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM payments_accounts_receivable par "
            "  WHERE par.invoiceReference = bdh.billingDocument"
            ") "
            "ORDER BY bdh.billingDocumentDate DESC;"
        ),
    },

    # ── Journal Entry queries ─────────────────────────────────────────
    {
        "input": "Find the journal entry linked to billing document 91150187",
        "query": (
            "SELECT companyCode, fiscalYear, accountingDocument, "
            "glAccount, amountInTransactionCurrency, transactionCurrency, "
            "postingDate, customer "
            "FROM journal_entry_items_accounts_receivable "
            "WHERE referenceDocument = '91150187';"
        ),
    },

    # ── Aggregation / Analytics ───────────────────────────────────────
    {
        "input": "What is the total revenue by product?",
        "query": (
            "SELECT bdi.material, pd.productDescription, "
            "SUM(CAST(bdi.netAmount AS DECIMAL(15,2))) AS total_revenue, "
            "bdi.transactionCurrency "
            "FROM billing_document_items bdi "
            "LEFT JOIN product_descriptions pd ON bdi.material = pd.product AND pd.language = 'EN' "
            "WHERE bdi.billingDocument IN ("
            "  SELECT billingDocument FROM billing_document_headers "
            "  WHERE billingDocumentIsCancelled = ''"
            ") "
            "GROUP BY bdi.material, pd.productDescription, bdi.transactionCurrency "
            "ORDER BY total_revenue DESC;"
        ),
    },
    {
        "input": "How many sales orders are in each delivery status?",
        "query": (
            "SELECT overallDeliveryStatus, COUNT(*) AS order_count "
            "FROM sales_order_headers "
            "GROUP BY overallDeliveryStatus "
            "ORDER BY order_count DESC;"
        ),
    },

    # ── Broken / Incomplete flows ─────────────────────────────────────
    {
        "input": "Identify sales orders that have broken or incomplete flows",
        "query": (
            "SELECT soh.salesOrder, soh.soldToParty, soh.totalNetAmount, "
            "soh.overallDeliveryStatus, soh.overallOrdReltdBillgStatus, "
            "CASE "
            "  WHEN soh.overallDeliveryStatus != 'C' THEN 'Not Fully Delivered' "
            "  WHEN soh.overallOrdReltdBillgStatus != 'C' THEN 'Delivered but Not Billed' "
            "  ELSE 'Complete' "
            "END AS flow_status "
            "FROM sales_order_headers soh "
            "WHERE soh.overallDeliveryStatus != 'C' "
            "OR soh.overallOrdReltdBillgStatus != 'C' "
            "ORDER BY soh.salesOrder;"
        ),
    },
]
