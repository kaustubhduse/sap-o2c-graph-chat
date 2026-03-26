/**
 * Pulls O2C document IDs from generated SQL so graph highlights match the query even when
 * the result text omits them (e.g. UNION with delivery AS id only).
 * Mirrors o2c-app/backend/nl-to-sql/utils.py (skips Plant/Product on SQL to avoid false positives).
 */

const SKIP_SQL_TYPES = new Set(['Plant', 'Product']);

const ID_RULES = [
  { type: 'SalesOrder', re: /\b(7[34]\d{4})\b/g },
  { type: 'Delivery', re: /\b(80\d{6})\b/g },
  { type: 'BillingDocument', re: /\b(9[01]\d{6})\b/g },
  { type: 'JournalEntry', re: /\b(94\d{8})\b/g },
  { type: 'Customer', re: /\b(3[12]\d{7})\b/g },
  { type: 'Payment', re: /\b(PAY[-_]?\d+)\b/gi },
];

function relevantTypesFromSql(sql) {
  const s = sql.toLowerCase();
  const t = new Set();
  if (s.includes('sales_order') || s.includes('salesorder')) t.add('SalesOrder');
  if (s.includes('delivery') || s.includes('outbound')) t.add('Delivery');
  if (s.includes('billing')) t.add('BillingDocument');
  if (s.includes('business_partner') || s.includes('customer')) t.add('Customer');
  if (s.includes('journal')) t.add('JournalEntry');
  if (s.includes('payment')) t.add('Payment');
  if (s.includes('product')) t.add('Product');
  if (s.includes('plant')) t.add('Plant');
  if (t.size === 0) return new Set(ID_RULES.map((r) => r.type));
  return t;
}

function graphKey(h) {
  if (!h) return '';
  if (typeof h === 'string') return h;
  return String(h.graphNodeId || `${h.type}:${h.id}`);
}

/**
 * @param {string} sql
 * @param {Array<{type?: string, id?: string, graphNodeId?: string}|string>} existing
 */
export function augmentHighlightsFromSql(sql, existing) {
  const list = [...(existing || [])].filter(Boolean);
  const seen = new Set(list.map(graphKey));

  const add = (type, id) => {
    if (!type || !id) return;
    const graphNodeId = `${type}:${id}`;
    if (seen.has(graphNodeId)) return;
    seen.add(graphNodeId);
    list.push({ type, id, graphNodeId });
  };

  if (!sql || typeof sql !== 'string') return list;

  const relevant = relevantTypesFromSql(sql);

  const s = sql.toLowerCase();

  for (const { type, re } of ID_RULES) {
    if (SKIP_SQL_TYPES.has(type)) continue;
    if (!relevant.has(type)) continue;
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(sql))) {
      add(type, m[1]);
    }
  }

  // Graph Payment nodes use numeric AR docs (e.g. Payment:9400000220); PAY- prefix is rare in SQL.
  if (
    relevant.has('Payment') &&
    (s.includes('payments_accounts') || s.includes('payments_ar'))
  ) {
    const re94 = /\b(94\d{8})\b/g;
    re94.lastIndex = 0;
    let m;
    while ((m = re94.exec(sql))) {
      add('Payment', m[1]);
    }
  }

  return list;
}
