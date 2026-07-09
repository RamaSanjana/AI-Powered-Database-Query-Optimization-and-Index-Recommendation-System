"""
recommendations.py
Index Recommendation Engine.

Analyses a SQL query's filter and join columns to produce concrete
CREATE INDEX statements along with benefit explanations.
"""

from __future__ import annotations
import re


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_table_column_pairs(query: str) -> list[tuple[str, str]]:
    """
    Return (table, column) tuples from WHERE and ON conditions.
    Handles simple patterns like:
        table.column = value
        table.column = other_table.column
        column = value   (no explicit table qualifier)
    """
    pairs: list[tuple[str, str]] = []

    # From table aliases – build a best-effort alias→table map
    alias_map: dict[str, str] = {}
    alias_pattern = re.finditer(
        r"\b(?:FROM|JOIN)\s+([\w.]+)\s+(?:AS\s+)?([\w]+)",
        query,
        re.IGNORECASE,
    )
    for m in alias_pattern:
        table_name = m.group(1).split(".")[-1].lower()
        alias      = m.group(2).lower()
        alias_map[alias] = table_name

    # ON conditions:  a.col = b.col
    for m in re.finditer(r"\bON\b\s+([\w.]+)\s*=\s*([\w.]+)", query, re.IGNORECASE):
        for grp in (m.group(1), m.group(2)):
            parts = grp.split(".")
            if len(parts) == 2:
                tbl = alias_map.get(parts[0].lower(), parts[0].lower())
                col = parts[1].lower()
                pairs.append((tbl, col))

    # WHERE conditions: col = value or table.col = value
    where_m = re.search(
        r"\bWHERE\b(.+?)(?:\bGROUP\b|\bORDER\b|\bHAVING\b|\bLIMIT\b|$)",
        query,
        re.IGNORECASE | re.DOTALL,
    )
    if where_m:
        clause = where_m.group(1)
        for m in re.finditer(
            r"([\w]+\.[\w]+|[\w]+)\s*(?:=|>|<|>=|<=|!=|LIKE|IN|BETWEEN)",
            clause,
            re.IGNORECASE,
        ):
            raw = m.group(1)
            parts = raw.split(".")
            if len(parts) == 2:
                tbl = alias_map.get(parts[0].lower(), parts[0].lower())
                col = parts[1].lower()
            else:
                # No table qualifier — try to find FROM table
                from_m = re.search(r"\bFROM\s+([\w]+)", query, re.IGNORECASE)
                tbl = from_m.group(1).lower() if from_m else "table"
                col = parts[0].lower()

            # Skip obvious non-column tokens
            if col not in ("and", "or", "not", "null", "true", "false", "is", "1", "0"):
                pairs.append((tbl, col))

    # Deduplicate while preserving order
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for p in pairs:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


def _composite_candidate(query: str) -> tuple[str, list[str]] | None:
    """
    If there is one table in FROM and multiple WHERE columns, suggest a
    composite index.
    """
    from_m = re.search(r"\bFROM\s+([\w]+)", query, re.IGNORECASE)
    if not from_m:
        return None

    table = from_m.group(1)
    where_m = re.search(
        r"\bWHERE\b(.+?)(?:\bGROUP\b|\bORDER\b|\bHAVING\b|\bLIMIT\b|$)",
        query,
        re.IGNORECASE | re.DOTALL,
    )
    if not where_m:
        return None

    cols = re.findall(
        r"([\w]+)\s*(?:=|>|<|>=|<=)",
        where_m.group(1),
        re.IGNORECASE,
    )
    cols = [c.lower() for c in cols
            if c.lower() not in ("and", "or", "not", "null", "true", "false")]
    if len(cols) >= 2:
        return (table.lower(), cols)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_index_recommendations(query: str, analysis: dict) -> list[dict]:
    """
    Generate concrete CREATE INDEX recommendations.

    Parameters
    ----------
    query    : str  — original SQL query
    analysis : dict — output of analyzer.analyze_query()

    Returns
    -------
    list of index recommendation dicts:
        index_name, ddl, reason, estimated_improvement, index_type
    """
    recs: list[dict] = []
    pairs = _extract_table_column_pairs(query)

    for tbl, col in pairs:
        idx_name = f"idx_{tbl}_{col}"
        ddl = f"CREATE INDEX {idx_name}\n    ON {tbl}({col});"
        recs.append({
            "index_name": idx_name,
            "ddl": ddl,
            "reason": (
                f"Column `{col}` on table `{tbl}` is used in a filter or join condition. "
                "Adding a B-tree index allows the planner to seek directly to matching rows."
            ),
            "estimated_improvement": "Up to 10–100× faster for selective queries",
            "index_type": "B-tree (default)",
        })

    # Composite index suggestion
    composite = _composite_candidate(query)
    if composite:
        tbl, cols = composite
        col_str  = ", ".join(cols)
        idx_name = f"idx_{tbl}_{'_'.join(cols)}"
        ddl = f"CREATE INDEX {idx_name}\n    ON {tbl}({col_str});"
        # Only add if not already covered by individual indexes
        if idx_name not in {r["index_name"] for r in recs}:
            recs.append({
                "index_name": idx_name,
                "ddl": ddl,
                "reason": (
                    f"Multiple columns ({col_str}) are filtered together in the WHERE clause. "
                    "A composite index can satisfy the entire WHERE clause in a single B-tree seek."
                ),
                "estimated_improvement": "Up to 50× faster than individual single-column indexes",
                "index_type": "Composite B-tree",
            })

    # Covering index suggestion for SELECT * queries
    if analysis.get("select_star") and pairs:
        tbl = pairs[0][0]
        filter_col = pairs[0][1]
        idx_name = f"idx_{tbl}_{filter_col}_covering"
        recs.append({
            "index_name": idx_name,
            "ddl": (
                f"-- Replace SELECT * with specific columns first, then:\n"
                f"CREATE INDEX {idx_name}\n"
                f"    ON {tbl}({filter_col}) INCLUDE (col1, col2, col3);"
            ),
            "reason": (
                "A covering index stores the filter column plus the projected columns, "
                "allowing index-only scans without touching the table heap."
            ),
            "estimated_improvement": "Index-only scan: up to 100× faster than heap scan",
            "index_type": "Covering index (INCLUDE)",
        })

    # Full-text index suggestion for LIKE patterns
    issue_codes = {i["code"] for i in analysis.get("issues", [])}
    warn_codes  = {w["code"] for w in analysis.get("warnings", [])}
    if "LEADING_WILDCARD" in (issue_codes | warn_codes):
        recs.append({
            "index_name": "fts_index_suggestion",
            "ddl": (
                "-- For contains-style searches, use full-text search:\n"
                "-- PostgreSQL:\n"
                "CREATE INDEX idx_fts ON your_table USING gin(to_tsvector('english', column_name));\n\n"
                "-- MySQL:\n"
                "ALTER TABLE your_table ADD FULLTEXT INDEX idx_fts (column_name);"
            ),
            "reason": (
                "Leading wildcards (LIKE '%value') cannot use B-tree indexes. "
                "Full-text indexes (GIN/GiST in PostgreSQL, FULLTEXT in MySQL) support "
                "efficient contains-style searches."
            ),
            "estimated_improvement": "Enables sub-millisecond full-text lookups on large tables",
            "index_type": "Full-text (GIN / FULLTEXT)",
        })

    return recs


BEST_PRACTICES: list[str] = [
    "Avoid `SELECT *` — always specify the columns you need.",
    "Index columns that appear in WHERE, JOIN ON, and ORDER BY clauses.",
    "Use composite indexes when multiple columns are filtered together — column order matters.",
    "Avoid functions on indexed columns in WHERE (e.g. `UPPER(col) = …`) — they disable index use.",
    "Prefer `EXISTS` over `IN` for correlated subqueries against large tables.",
    "Use `LIMIT` / `FETCH FIRST` to avoid unbounded result sets.",
    "Avoid leading wildcards (`LIKE '%value'`) — use full-text search instead.",
    "Partition large tables by date or tenant to reduce scan size.",
    "Run `EXPLAIN ANALYZE` (PostgreSQL) or `EXPLAIN FORMAT=JSON` (MySQL) to verify index use.",
    "Re-run `ANALYZE` / `UPDATE STATISTICS` after bulk loads to refresh query-planner statistics.",
    "Use connection pooling (PgBouncer, ProxySQL) to reduce connection overhead.",
    "Consider read replicas to offload reporting queries from the primary database.",
]
