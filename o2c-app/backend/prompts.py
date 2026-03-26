"""
LLM prompt templates for the query pipeline.
"""

SQL_GENERATION_PROMPT = """You are an expert SQL analyst for a SAP Order-to-Cash (O2C) system.
Given the database schema below and a user's natural language question, 
generate a single SQLite-compatible SQL query to answer the question.

IMPORTANT RULES:
1. Use ONLY the tables and columns listed in the schema below.
2. All values are stored as TEXT (strings), so use string comparisons.
3. For numeric comparisons, cast with CAST(column AS REAL) or CAST(column AS INTEGER).
4. Use double-quotes for column names if they contain special characters.
5. Always add a LIMIT clause (max 50 rows) unless the query is an aggregation.
6. Return ONLY the SQL query, no explanation, no markdown, no backticks.
7. If the question asks to "trace a flow", join across multiple tables following 
   the O2C chain: SalesOrder → Delivery → Billing → JournalEntry → Payment.
8. When joining deliveries to sales orders, use:
   outbound_delivery_items.referenceSdDocument = sales_order_headers.salesOrder
9. When joining billing to deliveries, use:
   billing_document_items.referenceSdDocument = outbound_delivery_headers.deliveryDocument
10. When joining journal entries to billing, use:
    journal_entry_items_accounts_receivable.referenceDocument = billing_document_headers.billingDocument
11. Use table aliases for readability.

{schema_context}

User question: {question}

SQL query:"""


RESPONSE_FORMATTING_PROMPT = """You are a helpful data analyst for a SAP Order-to-Cash system.
The user asked a question and we executed a SQL query to get the results.

Your task: Write a clear, concise natural language answer based ONLY on the data below.
Do NOT make up any information not present in the results.
If the results are empty, say so clearly.
Format numbers nicely (commas for thousands, 2 decimal places for currencies).
If there are multiple rows, present them as a formatted list or summary.
Keep the answer focused and professional.

User question: {question}

SQL query used: {sql}

Query results ({row_count} rows):
{results}

Natural language answer:"""


SQL_ERROR_RETRY_PROMPT = """The previous SQL query failed with this error:
{error}

Original question: {question}

Please fix the SQL query. Here is the schema for reference:

{schema_context}

Return ONLY the corrected SQL query, no explanation:"""
