"""
Core LangChain pipeline: NL → Table Selection → SQL → Execute → Answer + Graph IDs.

Architecture:
  1. Guardrail check (keyword + LLM)
  2. Dynamic table selection (LLM picks relevant tables)
  3. Few-shot SQL generation (with selected table schemas)
  4. SQL execution via QuerySQLDataBaseTool
  5. Answer rephrasing (LLM formats results as NL)
  6. Entity ID extraction (for graph highlighting)
"""
import os
import json
import logging
from typing import Iterator
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from db import get_db, get_table_info, get_table_names
from examples import EXAMPLES
from prompts import (
    build_few_shot_prompt,
    build_sql_generation_prompt,
    ANSWER_PROMPT,
    GUARDRAIL_PROMPT,
    TABLE_SELECTION_PROMPT,
)
from utils import (
    clean_sql,
    extract_entity_ids,
    keyword_guardrail,
    get_table_descriptions_text,
)

load_dotenv()
logger = logging.getLogger(__name__)


def is_sql_result_empty(result: str | None) -> bool:
    """True when MySQL/LangChain returned no data rows (not the same as SQL error)."""
    if result is None:
        return True
    t = str(result).strip()
    if not t:
        return True
    tl = t.lower()
    if tl in ("()", "[]", "{}", "null", "none"):
        return True
    if "empty set" in tl or "(0 rows" in tl or "0 rows in set" in tl:
        return True
    if "no rows" in tl or "no result" in tl:
        return True
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    return len(lines) == 0


# ── LLM Setup ────────────────────────────────────────────────────────
_llm = None

def get_llm():
    """Get or create the ChatGroq LLM instance."""
    global _llm
    if _llm is not None:
        return _llm

    api_key = os.getenv("GROQ_API_KEY", "")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env file")

    _llm = ChatGroq(
        api_key=api_key,
        model=model,
        temperature=0.0,
    )
    logger.info(f"LLM initialized: {model}")
    return _llm


# ── Step 1: Guardrail ────────────────────────────────────────────────
REJECTION_MESSAGE = (
    "This system is designed to answer questions related to the "
    "SAP Order-to-Cash dataset only. I can help with questions about "
    "sales orders, deliveries, billing documents, payments, customers, "
    "products, and plants."
)


def check_guardrail(question: str) -> tuple[bool, str | None]:
    """
    Two-layer guardrail: keyword check → LLM classification.
    Returns (is_allowed, rejection_message_or_None).
    """
    # Fast path
    result = keyword_guardrail(question)
    if result == "off_topic":
        return False, REJECTION_MESSAGE
    if result == "on_topic":
        return True, None

    # Uncertain → ask LLM
    try:
        llm = get_llm()
        chain = GUARDRAIL_PROMPT | llm | StrOutputParser()
        response = chain.invoke({"question": question})
        if "OFF_TOPIC" in response.upper():
            return False, REJECTION_MESSAGE
        return True, None
    except Exception as e:
        logger.warning(f"LLM guardrail failed: {e}, defaulting to on_topic")
        return True, None


# ── Step 2: Dynamic Table Selection ──────────────────────────────────
def select_relevant_tables(question: str) -> list[str]:
    """
    Use LLM to identify which tables are relevant for the user's question.
    Falls back to all tables if selection fails.
    """
    all_tables = get_table_names()

    try:
        llm = get_llm()
        chain = TABLE_SELECTION_PROMPT | llm | StrOutputParser()
        response = chain.invoke({
            "table_descriptions": get_table_descriptions_text(),
            "question": question,
        })

        # Parse comma-separated table names
        selected = [t.strip() for t in response.split(",")]
        # Validate against actual tables
        valid = [t for t in selected if t in all_tables]

        if valid:
            logger.info(f"Selected tables: {valid}")
            return valid
        else:
            logger.warning(f"Table selection returned invalid tables: {selected}")
            return all_tables
    except Exception as e:
        logger.warning(f"Table selection failed: {e}, using all tables")
        return all_tables


# ── Step 3-4: SQL Generation + Execution ─────────────────────────────
def generate_and_execute(question: str, max_retries: int = 2):
    """
    Generate SQL from question, execute it, and return (sql, result_str).
    Includes retry logic on SQL errors.
    """
    db = get_db()
    llm = get_llm()

    # Select relevant tables
    relevant_tables = select_relevant_tables(question)
    table_info = get_table_info(relevant_tables)

    # Build few-shot prompt
    few_shot = build_few_shot_prompt(EXAMPLES)
    full_prompt = build_sql_generation_prompt(few_shot)

    # SQL generation chain
    sql_chain = full_prompt | llm | StrOutputParser()

    # Execute tool
    execute_tool = QuerySQLDataBaseTool(db=db)

    # Generate SQL
    raw_sql = sql_chain.invoke({
        "input": question,
        "table_info": table_info,
    })
    sql = clean_sql(raw_sql)
    logger.info(f"Generated SQL: {sql}")

    # Execute with retry
    last_error = None
    for attempt in range(1 + max_retries):
        try:
            result = execute_tool.invoke(sql.rstrip(";"))
            logger.info(f"SQL executed successfully (attempt {attempt + 1})")
            return sql, result
        except Exception as e:
            last_error = str(e)
            logger.warning(f"SQL attempt {attempt + 1} failed: {last_error}")

            if attempt < max_retries:
                # Ask LLM to fix the SQL
                fix_prompt = (
                    f"The following MySQL query failed:\n{sql}\n\n"
                    f"Error: {last_error}\n\n"
                    f"Schema:\n{table_info}\n\n"
                    f"Original question: {question}\n\n"
                    f"Generate a corrected MySQL query. Return ONLY the SQL, nothing else."
                )
                try:
                    fixed_raw = llm.invoke(fix_prompt).content
                    sql = clean_sql(fixed_raw)
                    logger.info(f"Retry SQL: {sql}")
                except Exception as retry_err:
                    logger.error(f"SQL retry generation failed: {retry_err}")
                    break

    raise ValueError(f"SQL execution failed after {max_retries + 1} attempts: {last_error}")


# ── Step 5: Answer Rephrasing ────────────────────────────────────────
def format_answer(question: str, sql: str, result: str) -> str:
    """Use LLM to convert SQL results into a natural language answer."""
    llm = get_llm()
    chain = ANSWER_PROMPT | llm | StrOutputParser()
    return chain.invoke({
        "question": question,
        "query": sql,
        "result": result,
    })


def format_answer_stream(question: str, sql: str, result: str) -> Iterator[str]:
    """Stream answer text chunks from the LLM."""
    llm = get_llm()
    chain = ANSWER_PROMPT | llm | StrOutputParser()
    yield from chain.stream({
        "question": question,
        "query": sql,
        "result": result,
    })


# ── Full Pipeline ────────────────────────────────────────────────────
def process_query(question: str) -> dict:
    """
    Complete NL-to-SQL pipeline:
      guardrail → table selection → SQL gen → execute → answer → graph IDs

    Returns:
    {
        "answer": str,
        "sql": str | None,
        "data": str | None,
        "highlighted_nodes": list | None,
        "status": "success" | "rejected" | "error"
    }
    """
    # Step 1: Guardrail
    is_allowed, rejection_msg = check_guardrail(question)
    if not is_allowed:
        return {
            "answer": rejection_msg,
            "sql": None,
            "data": None,
            "highlighted_nodes": None,
            "status": "rejected",
            "result_empty": None,
        }

    # Steps 2-4: Generate + Execute SQL
    try:
        sql, result_str = generate_and_execute(question)
    except ValueError as e:
        return {
            "answer": f"I understood your question but couldn't execute the query. Error: {e}",
            "sql": None,
            "data": None,
            "highlighted_nodes": None,
            "status": "error",
            "result_empty": None,
        }
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        return {
            "answer": f"Sorry, something went wrong processing your question. Error: {e}",
            "sql": None,
            "data": None,
            "highlighted_nodes": None,
            "status": "error",
            "result_empty": None,
        }

    result_empty = is_sql_result_empty(result_str)

    # Step 5: Format answer
    if result_empty:
        logger.info("SQL returned 0 rows — using empty-result answer (still returning sql).")
        try:
            answer = format_answer(question, sql, "(no rows returned)")
        except Exception as e:
            logger.error(f"Answer formatting failed: {e}")
            answer = (
                "The query **ran successfully** but returned **no rows**. "
                "Long chains of INNER JOINs often do this when delivery, billing, journal, or payment "
                "data is missing for that case. Try asking for a simpler slice (e.g. sales order + delivery only) "
                "or use **View SQL** to adjust joins (LEFT JOIN from `sales_order_headers`)."
            )
    else:
        try:
            answer = format_answer(question, sql, result_str)
        except Exception as e:
            logger.error(f"Answer formatting failed: {e}")
            answer = f"Query returned results:\n{result_str[:500]}"

    # Step 6: Extract entity IDs for graph highlighting
    highlighted_nodes = extract_entity_ids(result_str, sql)

    return {
        "answer": answer,
        "sql": sql,
        "data": result_str,
        "highlighted_nodes": highlighted_nodes,
        "status": "success",
        "result_empty": result_empty,
    }


def process_query_stream(question: str):
    """
    Streaming variant of process_query.
    Yields dict events:
      - {"event":"status", ...}
      - {"event":"sql", "sql": ...}
      - {"event":"answer_chunk", "chunk": "..."}
      - {"event":"final", "result": {...same payload as process_query...}}
    """
    yield {"event": "status", "stage": "guardrail"}
    is_allowed, rejection_msg = check_guardrail(question)
    if not is_allowed:
        yield {
            "event": "final",
            "result": {
                "answer": rejection_msg,
                "sql": None,
                "data": None,
                "highlighted_nodes": None,
                "status": "rejected",
                "result_empty": None,
            },
        }
        return

    yield {"event": "status", "stage": "sql_generation"}
    try:
        sql, result_str = generate_and_execute(question)
    except ValueError as e:
        yield {
            "event": "final",
            "result": {
                "answer": f"I understood your question but couldn't execute the query. Error: {e}",
                "sql": None,
                "data": None,
                "highlighted_nodes": None,
                "status": "error",
                "result_empty": None,
            },
        }
        return
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        yield {
            "event": "final",
            "result": {
                "answer": f"Sorry, something went wrong processing your question. Error: {e}",
                "sql": None,
                "data": None,
                "highlighted_nodes": None,
                "status": "error",
                "result_empty": None,
            },
        }
        return

    result_empty = is_sql_result_empty(result_str)
    yield {"event": "sql", "sql": sql}
    yield {"event": "status", "stage": "answer_rephrasing"}

    answer_chunks = []
    try:
        answer_input_result = "(no rows returned)" if result_empty else result_str
        for chunk in format_answer_stream(question, sql, answer_input_result):
            if not chunk:
                continue
            answer_chunks.append(chunk)
            yield {"event": "answer_chunk", "chunk": chunk}
        answer = "".join(answer_chunks).strip()
        if not answer:
            raise ValueError("Empty streamed answer")
    except Exception as e:
        logger.error(f"Answer streaming failed: {e}")
        if result_empty:
            answer = (
                "The query ran successfully but returned no rows. "
                "Try a narrower or different identifier and inspect View SQL if needed."
            )
        else:
            answer = f"Query returned results:\n{result_str[:500]}"
        yield {"event": "answer_chunk", "chunk": answer}

    highlighted_nodes = extract_entity_ids(result_str, sql)
    yield {
        "event": "final",
        "result": {
            "answer": answer,
            "sql": sql,
            "data": result_str,
            "highlighted_nodes": highlighted_nodes,
            "status": "success",
            "result_empty": result_empty,
        },
    }
