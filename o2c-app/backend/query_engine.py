"""
Query engine: orchestrates the NL → SQL → Execute → Format pipeline.
"""
import json
import logging
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, MAX_SQL_RETRIES
from database import run_query
from schema_context import build_schema_context
from guardrails import check_guardrail
from prompts import SQL_GENERATION_PROMPT, RESPONSE_FORMATTING_PROMPT, SQL_ERROR_RETRY_PROMPT

logger = logging.getLogger(__name__)

# Cache schema context (built once)
_schema_context = None


def _get_schema():
    global _schema_context
    if _schema_context is None:
        _schema_context = build_schema_context()
    return _schema_context


def _call_llm(prompt):
    """Call Groq API and return text response."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set. Please add it to the .env file.")

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return response.choices[0].message.content.strip()


def _generate_sql(question):
    """Generate SQL from a natural language question."""
    schema = _get_schema()
    prompt = SQL_GENERATION_PROMPT.format(
        schema_context=schema,
        question=question,
    )
    sql = _call_llm(prompt)

    # Clean up: remove markdown backticks if present
    if sql.startswith("```"):
        lines = sql.split("\n")
        sql = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        )
    sql = sql.strip().rstrip(";") + ";"

    return sql


def _format_results(question, sql, results):
    """Format SQL results into a natural language answer."""
    # Truncate results for the prompt if too many
    display_results = results[:20]
    results_str = json.dumps(display_results, indent=2, default=str)

    prompt = RESPONSE_FORMATTING_PROMPT.format(
        question=question,
        sql=sql,
        row_count=len(results),
        results=results_str,
    )
    return _call_llm(prompt)


def _retry_sql(question, error_msg):
    """Attempt to fix a broken SQL query."""
    schema = _get_schema()
    prompt = SQL_ERROR_RETRY_PROMPT.format(
        error=error_msg,
        question=question,
        schema_context=schema,
    )
    sql = _call_llm(prompt)

    if sql.startswith("```"):
        lines = sql.split("\n")
        sql = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        )
    sql = sql.strip().rstrip(";") + ";"
    return sql


def process_query(question):
    """
    Full pipeline: guardrail → SQL → execute → format.
    Returns a dict with the response.
    """
    # Step 1: Guardrail
    is_allowed, rejection_msg = check_guardrail(question)
    if not is_allowed:
        return {
            "answer": rejection_msg,
            "sql": None,
            "data": None,
            "status": "rejected",
        }

    # Step 2: Generate SQL
    try:
        sql = _generate_sql(question)
        logger.info(f"Generated SQL: {sql}")
    except Exception as e:
        logger.error(f"SQL generation failed: {e}")
        return {
            "answer": f"Sorry, I couldn't understand your question. Could you rephrase it? (Error: {e})",
            "sql": None,
            "data": None,
            "status": "error",
        }

    # Step 3: Execute SQL (with retry on error)
    results = None
    last_error = None
    for attempt in range(1 + MAX_SQL_RETRIES):
        try:
            results = run_query(sql)
            last_error = None
            break
        except ValueError as e:
            last_error = str(e)
            logger.warning(f"SQL attempt {attempt + 1} failed: {last_error}")
            if attempt < MAX_SQL_RETRIES:
                try:
                    sql = _retry_sql(question, last_error)
                    logger.info(f"Retry SQL: {sql}")
                except Exception as retry_err:
                    logger.error(f"Retry generation failed: {retry_err}")
                    break

    if last_error:
        return {
            "answer": f"I understood your question but couldn't execute the query. Error: {last_error}",
            "sql": sql,
            "data": None,
            "status": "error",
        }

    # Step 4: Format response
    try:
        answer = _format_results(question, sql, results)
    except Exception as e:
        logger.error(f"Response formatting failed: {e}")
        # Fallback: return raw data
        answer = f"Found {len(results)} results. Here are the first few:\n"
        for row in results[:5]:
            answer += f"  • {row}\n"

    return {
        "answer": answer,
        "sql": sql,
        "data": results[:20],  # return limited data for frontend
        "status": "success",
    }
