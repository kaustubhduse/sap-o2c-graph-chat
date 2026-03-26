/**
 * Graph configuration: colors, sizes, and labels for each node type.
 */

export const NODE_COLORS = {
  Customer:        '#f472b6', // pink
  SalesOrder:      '#60a5fa', // blue
  Product:         '#34d399', // green
  Delivery:        '#fbbf24', // amber
  BillingDocument: '#a78bfa', // violet
  JournalEntry:    '#fb923c', // orange
  Payment:         '#22d3ee', // cyan
  Plant:           '#94a3b8', // slate
};

export const NODE_SIZES = {
  Customer:        4,
  SalesOrder:      3,
  Product:         2.5,
  Delivery:        2.5,
  BillingDocument: 2.5,
  JournalEntry:    2,
  Payment:         2,
  Plant:           2,
};

export const EDGE_COLORS = {
  PLACED_BY:             '#93c5fd88', // light blue
  CONTAINS_ITEM:         '#6ee7b788', // light green
  HAS_SCHEDULE_LINE:     '#93c5fd44',
  FULFILLS:              '#fcd34d88', // amber
  DELIVERED_FROM:        '#cbd5e188', // slate
  BILLS:                 '#c4b5fd88', // violet
  BILLS_PRODUCT:         '#c4b5fd44',
  BILLED_TO:             '#f9a8d488', // pink
  CANCELS:               '#fca5a588', // red
  ACCOUNTS_FOR:          '#fdba7488', // orange
  JOURNAL_FOR_CUSTOMER:  '#fdba7444',
  PAYS:                  '#67e8f988', // cyan
  PAID_BY:               '#67e8f944',
  AVAILABLE_AT:          '#cbd5e144',
  STORED_AT:             '#cbd5e144',
  HAS_ADDRESS:           '#f9a8d444',
  ASSIGNED_TO_COMPANY:   '#f9a8d444',
  ASSIGNED_TO_SALES_AREA:'#f9a8d444',
};

export const ALL_NODE_TYPES = Object.keys(NODE_COLORS);
export const ALL_EDGE_TYPES = Object.keys(EDGE_COLORS);
