"""
Guardrails: ensure queries are relevant to the SAP O2C dataset.
Uses keyword matching first, then LLM classification as fallback.
"""
import logging
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

# Keywords that indicate on-topic queries
ON_TOPIC_KEYWORDS = [
    "sales order", "sales_order", "salesorder", "order",
    "billing", "invoice", "bill",
    "delivery", "shipment", "shipped", "delivered",
    "payment", "paid", "pay", "clearing",
    "journal", "accounting", "journal entry",
    "customer", "business partner", "client",
    "product", "material", "item",
    "plant", "warehouse", "storage",
    "sap", "o2c", "order to cash", "order-to-cash",
    "document", "flow", "trace", "track",
    "revenue", "amount", "net amount", "total",
    "cancelled", "cancellation", "blocked",
    "incomplete", "missing", "broken",
    "billed", "unbilled", "overdue",
    "top", "highest", "lowest", "most", "average",
    "count", "how many", "list", "show", "find", "which",
    "company code", "fiscal year", "currency",
    "distribution", "division", "organization",
    "incoterms", "payment terms",
]

# Patterns that clearly indicate off-topic
OFF_TOPIC_PATTERNS = [
    "write me a", "write a poem", "write a story", "creative writing",
    "tell me a joke", "sing a song", "make up",
    "capital of", "president of", "who invented",
    "recipe for", "how to cook",
    "weather", "stock price", "crypto",
    "play a game", "tic tac toe",
    "translate to", "what language",
    "meaning of life", "who are you", "what are you",
    "help me with my homework",
]


def _keyword_check(query):
    """
    Fast keyword-based classification.
    Returns: 'on_topic', 'off_topic', or 'uncertain'
    """
    q = query.lower().strip()

    # Check off-topic patterns first
    for pattern in OFF_TOPIC_PATTERNS:
        if pattern in q:
            return "off_topic"

    # Check on-topic keywords
    for keyword in ON_TOPIC_KEYWORDS:
        if keyword in q:
            return "on_topic"

    return "uncertain"


def _llm_classify(query):
    """
    Use Groq to classify whether a query is about the SAP O2C dataset.
    Returns True if on-topic, False if off-topic.
    """
    if not GROQ_API_KEY:
        # If no API key, default to allowing (keyword check already passed)
        return True

    try:
        client = Groq(api_key=GROQ_API_KEY)

        prompt = f"""You are a classifier for a SAP Order-to-Cash (O2C) data system.
The system has tables about: sales orders, deliveries, billing documents, 
journal entries, payments, customers, products, and plants.

Determine if the following user query is asking about this business dataset 
or if it's an unrelated/off-topic question.

User query: "{query}"

Reply with exactly one word: ON_TOPIC or OFF_TOPIC"""

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_completion_tokens=10,
        )
        result = response.choices[0].message.content.strip().upper()
        return "ON_TOPIC" in result
    except Exception as e:
        logger.warning(f"LLM classification failed: {e}, defaulting to on_topic")
        return True


def check_guardrail(query):
    """
    Check if a query passes the guardrail.
    Returns (is_allowed: bool, rejection_message: str or None)
    """
    result = _keyword_check(query)

    if result == "off_topic":
        return False, (
            "This system is designed to answer questions related to the "
            "SAP Order-to-Cash dataset only. Please ask about sales orders, "
            "deliveries, billing documents, payments, customers, or products."
        )

    if result == "on_topic":
        return True, None

    # Uncertain — use LLM
    is_on_topic = _llm_classify(query)
    if not is_on_topic:
        return False, (
            "This system is designed to answer questions related to the "
            "provided dataset only. I can help with questions about sales orders, "
            "deliveries, billing, payments, customers, products, and plants."
        )

    return True, None
