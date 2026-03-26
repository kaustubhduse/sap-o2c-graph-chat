"""
Prompt templates for the NL-to-SQL LangChain pipeline.
Separates system prompts, few-shot formatting, answer rephrasing,
and guardrail classification.
"""
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)

# ── Few-shot example formatter ────────────────────────────────────────
EXAMPLE_PROMPT = ChatPromptTemplate.from_messages([
    ("human", "{input}"),
    ("ai", "{query}"),
])


def build_few_shot_prompt(examples):
    """
    Build a FewShotChatMessagePromptTemplate from a list of examples.
    Each example is a dict with 'input' and 'query'.
    """
    return FewShotChatMessagePromptTemplate(
        example_prompt=EXAMPLE_PROMPT,
        examples=examples,
        input_variables=["input"],
    )


# ── SQL Generation system prompt ─────────────────────────────────────
SQL_SYSTEM_PROMPT = """You are an expert MySQL analyst for a SAP Order-to-Cash (O2C) system.

Given the database schema and a user's question, generate a single, correct MySQL query.

CRITICAL RULES:
1. ONLY use tables and columns that exist in the schema below.
2. NEVER hallucinate column or table names.
3. Use backticks for table and column names containing special characters.
4. For numeric comparisons, CAST string columns to DECIMAL or INTEGER.
5. Always add LIMIT 50 unless the query is an aggregation with GROUP BY.
6. Return ONLY the raw SQL query — no explanation, no markdown, no backticks.
7. For tracing flows across the O2C chain, prefer **LEFT JOIN** starting from the anchor table
   (usually `sales_order_headers soh`), unless the user explicitly requires every step to exist.
   Use **LEFT JOIN sales_order_items** (not INNER JOIN) when tracing from the header so delivery/billing
   gaps do not drop the whole order. INNER JOINs through delivery → billing → journal → payment often
   return **zero rows** when any step is missing; LEFT JOIN keeps rows and shows NULLs for missing steps.
   Join keys (same as the property graph):
   - outbound_delivery_items.referenceSdDocument = sales_order_headers.salesOrder
   - billing_document_items.referenceSdDocument = outbound_delivery_headers.deliveryDocument (same as delivery doc id)
   - journal_entry_items_accounts_receivable.referenceDocument = billing_document_headers.billingDocument
   - payments_accounts_receivable.accountingDocument = journal_entry_items_accounts_receivable.accountingDocument
   (Payment also links to billing via `invoiceReference` = billing document when not joining through journal.)
8. **Customer name vs id:** If the user asks for "customer name", "sold-to name", or "customer",
   JOIN `business_partners bp` ON `soh.soldToParty = bp.businessPartner` and SELECT
   `bp.businessPartnerFullName` (and optionally `bp.businessPartner`). Never return only `soldToParty`
   as the "name" — that is the customer **number**.
9. Optional: `LEFT JOIN outbound_delivery_headers odh ON odi.deliveryDocument = odh.deliveryDocument` and
   `LEFT JOIN billing_document_headers bdh ON bdi.billingDocument = bdh.billingDocument` when you need header fields.
10. Use table aliases for readability.
11. When filtering by ID values, always treat them as strings (quote them).

{table_info}
"""


def build_sql_generation_prompt(few_shot_prompt):
    """Build the full SQL generation prompt with few-shot examples."""
    return ChatPromptTemplate.from_messages([
        ("system", SQL_SYSTEM_PROMPT),
        few_shot_prompt,
        MessagesPlaceholder("history", optional=True),
        ("human", "{input}"),
    ])


# ── Answer Rephrasing prompt ─────────────────────────────────────────
ANSWER_PROMPT = PromptTemplate.from_template(
    """You are a helpful data analyst for a SAP Order-to-Cash system.
Given the user's question, the SQL query that was run, and the results,
write a clear, concise natural language answer.

RULES:
- Base your answer ONLY on the data in the results — never fabricate data.
- If results are empty or only whitespace, say clearly that **the query executed but returned 0 rows**,
  and briefly explain that long INNER JOIN chains often cause this when billing/journal/payment is missing.
  Tell the user they can use **View SQL** to inspect the query. Do NOT claim the database failed.
- Format numbers nicely (commas for thousands, 2 decimal places for currencies).
- If there are multiple rows, summarize or present as a formatted list.
- Mention specific IDs (sales orders, billing docs, customers) when relevant.
- Keep it professional and focused.

Question: {question}
SQL Query: {query}
SQL Result: {result}

Answer:"""
)


# ── Guardrail Classification prompt ──────────────────────────────────
GUARDRAIL_PROMPT = PromptTemplate.from_template(
    """You are a classifier for a SAP Order-to-Cash (O2C) data query system.
The system has tables about: sales orders, deliveries, billing documents,
journal entries, payments, customers/business partners, products, and plants.

Determine if the following user query is asking about this business dataset
or if it's an unrelated/off-topic question.

User query: "{question}"

Reply with exactly one word: ON_TOPIC or OFF_TOPIC"""
)


# ── Table Selection prompt ────────────────────────────────────────────
TABLE_SELECTION_PROMPT = PromptTemplate.from_template(
    """Given the following user question about an SAP Order-to-Cash system,
identify which database tables are most relevant to answer this question.

Available tables and their descriptions:
{table_descriptions}

User question: {question}

Return ONLY a comma-separated list of relevant table names. No explanation.
Example: sales_order_headers, sales_order_items, business_partners"""
)
