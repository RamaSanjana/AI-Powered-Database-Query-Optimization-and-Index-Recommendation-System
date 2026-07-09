"""
execution_plan.py
Simulated Query Execution Plan Generator.

Produces a tree of plan nodes modelled after PostgreSQL's EXPLAIN output,
showing how the database engine would process the SQL internally.
Each node carries cost estimates, row estimates, and a description.
"""

from __future__ import annotations
import re
import math
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Plan node
# ---------------------------------------------------------------------------

@dataclass
class PlanNode:
    node_type: str
    description: str
    estimated_rows: int
    startup_cost: float
    total_cost: float
    icon: str
    children: list["PlanNode"] = field(default_factory=list)

    @property
    def cost_label(self) -> str:
        return f"{self.startup_cost:.2f}..{self.total_cost:.2f}"


# ---------------------------------------------------------------------------
# Cost constants (PostgreSQL-inspired planner units)
# ---------------------------------------------------------------------------
_ROWS_BASE      = 100_000   # assumed table cardinality
_SEQ_PAGE_COST  = 1.0
_IDX_PAGE_COST  = 0.005
_CPU_TUPLE_COST = 0.01
_CPU_OP_COST    = 0.0025


# ---------------------------------------------------------------------------
# Node constructors
# ---------------------------------------------------------------------------

def _seq_scan_node(table: str, selectivity: float = 1.0) -> PlanNode:
    rows_out = max(1, int(_ROWS_BASE * selectivity))
    pages    = math.ceil(_ROWS_BASE / 100)
    total    = pages * _SEQ_PAGE_COST + _ROWS_BASE * _CPU_TUPLE_COST
    return PlanNode(
        node_type="Seq Scan",
        description=f"Seq Scan on {table}  (estimated rows={_ROWS_BASE:,})",
        estimated_rows=rows_out,
        startup_cost=0.00,
        total_cost=round(total, 2),
        icon="🔴",
    )


def _index_scan_node(table: str, column: str, selectivity: float = 0.01) -> PlanNode:
    rows_out = max(1, int(_ROWS_BASE * selectivity))
    startup  = 0.285
    total    = startup + rows_out * (_IDX_PAGE_COST + _CPU_TUPLE_COST)
    return PlanNode(
        node_type="Index Scan",
        description=f"Index Scan using idx_{table}_{column} on {table}",
        estimated_rows=rows_out,
        startup_cost=round(startup, 2),
        total_cost=round(total, 2),
        icon="🟢",
    )


def _bitmap_index_scan_node(table: str, column: str) -> PlanNode:
    rows_out = max(1, int(_ROWS_BASE * 0.05))
    startup  = 0.00
    total    = rows_out * _IDX_PAGE_COST * 5
    return PlanNode(
        node_type="Bitmap Index Scan",
        description=f"Bitmap Index Scan on idx_{table}_{column}",
        estimated_rows=rows_out,
        startup_cost=round(startup, 2),
        total_cost=round(total, 2),
        icon="🟣",
    )


def _filter_node(child: PlanNode, condition: str) -> PlanNode:
    rows_out = max(1, int(child.estimated_rows * 0.1))
    total    = child.total_cost + rows_out * _CPU_OP_COST
    node = PlanNode(
        node_type="Filter",
        description=f"Filter: {condition}",
        estimated_rows=rows_out,
        startup_cost=round(child.startup_cost, 2),
        total_cost=round(total, 2),
        icon="🔵",
    )
    node.children.append(child)
    return node


def _hash_node(child: PlanNode) -> PlanNode:
    """Hash build step (inner side of Hash Join)."""
    total = child.total_cost + child.estimated_rows * _CPU_TUPLE_COST
    node = PlanNode(
        node_type="Hash",
        description=f"Build hash table from {child.estimated_rows:,} rows",
        estimated_rows=child.estimated_rows,
        startup_cost=round(child.total_cost, 2),
        total_cost=round(total, 2),
        icon="🟡",
    )
    node.children.append(child)
    return node


def _hash_join_node(left: PlanNode, right: PlanNode, condition: str) -> PlanNode:
    rows_out = max(1, int(math.sqrt(left.estimated_rows * right.estimated_rows)))
    startup  = right.total_cost
    total    = startup + left.total_cost + rows_out * _CPU_TUPLE_COST
    inner    = _hash_node(right)
    node = PlanNode(
        node_type="Hash Join",
        description=f"Hash Join  —  join cond: {condition}",
        estimated_rows=rows_out,
        startup_cost=round(startup, 2),
        total_cost=round(total, 2),
        icon="🟠",
    )
    node.children = [left, inner]
    return node


def _nested_loop_node(outer: PlanNode, inner: PlanNode, condition: str) -> PlanNode:
    rows_out = max(1, outer.estimated_rows * max(1, inner.estimated_rows // 100))
    total    = outer.total_cost + outer.estimated_rows * inner.total_cost
    node = PlanNode(
        node_type="Nested Loop",
        description=f"Nested Loop  —  {condition}",
        estimated_rows=rows_out,
        startup_cost=0.00,
        total_cost=round(min(total, 9_999_999), 2),
        icon="🔶",
    )
    node.children = [outer, inner]
    return node


def _sort_node(child: PlanNode, keys: str) -> PlanNode:
    rows_out = child.estimated_rows
    startup  = child.total_cost + rows_out * math.log2(max(rows_out, 2)) * _CPU_OP_COST
    total    = startup + rows_out * _CPU_TUPLE_COST
    node = PlanNode(
        node_type="Sort",
        description=f"Sort  —  key: {keys}",
        estimated_rows=rows_out,
        startup_cost=round(startup, 2),
        total_cost=round(total, 2),
        icon="🔷",
    )
    node.children.append(child)
    return node


def _hash_aggregate_node(child: PlanNode, group_keys: str) -> PlanNode:
    rows_out = max(1, child.estimated_rows // 20)
    startup  = child.total_cost
    total    = startup + child.estimated_rows * _CPU_OP_COST
    node = PlanNode(
        node_type="HashAggregate",
        description=f"Group by: {group_keys}",
        estimated_rows=rows_out,
        startup_cost=round(startup, 2),
        total_cost=round(total, 2),
        icon="🟤",
    )
    node.children.append(child)
    return node


def _aggregate_node(child: PlanNode) -> PlanNode:
    startup = child.total_cost
    total   = startup + child.estimated_rows * _CPU_OP_COST
    node = PlanNode(
        node_type="Aggregate",
        description="Compute aggregate function(s)",
        estimated_rows=1,
        startup_cost=round(startup, 2),
        total_cost=round(total, 2),
        icon="🟤",
    )
    node.children.append(child)
    return node


def _limit_node(child: PlanNode, limit_val: int) -> PlanNode:
    rows_out = min(child.estimated_rows, limit_val)
    total    = child.startup_cost + rows_out * _CPU_TUPLE_COST
    node = PlanNode(
        node_type="Limit",
        description=f"Limit  →  {limit_val} rows",
        estimated_rows=rows_out,
        startup_cost=round(child.startup_cost, 2),
        total_cost=round(total, 2),
        icon="⬛",
    )
    node.children.append(child)
    return node


def _subquery_scan_node(child: PlanNode, alias: str) -> PlanNode:
    node = PlanNode(
        node_type="SubQuery Scan",
        description=f"Scan results of subquery as: {alias}",
        estimated_rows=child.estimated_rows,
        startup_cost=child.startup_cost,
        total_cost=child.total_cost,
        icon="🔻",
    )
    node.children.append(child)
    return node


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract_tables(query: str) -> list[str]:
    hits = re.findall(
        r"\b(?:FROM|JOIN)\s+([\w]+)(?:\s+(?:AS\s+)?[\w]+)?",
        query, re.IGNORECASE,
    )
    return [h.lower() for h in hits]


def _extract_on_conditions(query: str) -> list[str]:
    return re.findall(r"\bON\b\s+([\w.]+\s*=\s*[\w.]+)", query, re.IGNORECASE)


def _extract_order_keys(query: str) -> str:
    m = re.search(
        r"\bORDER\s+BY\b\s+(.+?)(?:\bLIMIT\b|$)", query, re.IGNORECASE | re.DOTALL
    )
    return m.group(1).strip() if m else "key"


def _extract_group_keys(query: str) -> str:
    m = re.search(
        r"\bGROUP\s+BY\b\s+(.+?)(?:\bHAVING\b|\bORDER\b|\bLIMIT\b|$)",
        query, re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip() if m else ""


def _extract_limit_val(query: str) -> int:
    m = re.search(r"\bLIMIT\s+(\d+)", query, re.IGNORECASE)
    return int(m.group(1)) if m else 100


def _where_preview(query: str) -> str:
    m = re.search(
        r"\bWHERE\b\s+(.{1,50}?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|$)",
        query, re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip().replace("\n", " ") if m else "condition"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_execution_plan(query: str, analysis: dict) -> PlanNode:
    """
    Build a simulated execution plan tree.
    Returns the root PlanNode (top of the plan = last operation executed by DB).
    """
    tables      = _extract_tables(query)
    join_cnt    = analysis.get("join_count", 0)
    has_where   = analysis.get("has_where", False)
    has_idx     = bool(analysis.get("filter_columns"))
    filter_cols = analysis.get("filter_columns", [])
    has_agg     = analysis.get("has_aggregation", False)
    has_grp     = analysis.get("has_group_by", False)
    has_ord     = analysis.get("has_order_by", False)
    has_lim     = analysis.get("has_limit", False)
    sub_cnt     = analysis.get("subquery_count", 0)

    primary = tables[0] if tables else "table"

    # ---- Base scan node ----
    if has_where and has_idx and filter_cols:
        scan = _index_scan_node(primary, filter_cols[0], selectivity=0.01)
    elif has_where:
        # WHERE present but no indexed column — bitmap or seq + filter
        inner = _seq_scan_node(primary, selectivity=1.0)
        scan  = _filter_node(inner, _where_preview(query))
    else:
        scan = _seq_scan_node(primary, selectivity=1.0)

    # ---- Subquery ----
    if sub_cnt > 0:
        sub_table = tables[-1] if len(tables) > 1 else "subquery_table"
        sub_inner = _seq_scan_node(sub_table, 0.1)
        sub_inner = _filter_node(sub_inner, "subquery predicate")
        scan = _subquery_scan_node(sub_inner, "sq1")

    # ---- JOINs ----
    on_conds = _extract_on_conditions(query)
    join_tables = tables[1:] if len(tables) > 1 else []
    for i in range(join_cnt):
        jt   = join_tables[i] if i < len(join_tables) else f"t{i+2}"
        cond = on_conds[i] if i < len(on_conds) else f"{primary}.id = {jt}.{primary}_id"
        # If join table is small/indexed use Nested Loop, else Hash Join
        if has_idx and i == 0:
            right = _index_scan_node(jt, "id", selectivity=0.001)
            scan  = _nested_loop_node(scan, right, cond)
        else:
            right = _seq_scan_node(jt, 1.0)
            scan  = _hash_join_node(scan, right, cond)

    # ---- Aggregate ----
    if has_grp:
        group_keys = _extract_group_keys(query)
        scan = _hash_aggregate_node(scan, group_keys)
    elif has_agg:
        scan = _aggregate_node(scan)

    # ---- Sort ----
    if has_ord:
        scan = _sort_node(scan, _extract_order_keys(query))

    # ---- Limit ----
    if has_lim:
        scan = _limit_node(scan, _extract_limit_val(query))

    return scan   # root of plan tree


def flatten_plan(root: PlanNode) -> list[dict]:
    """Flatten the plan tree depth-first into a list of dicts for table display."""
    result: list[dict] = []

    def _walk(node: PlanNode, depth: int) -> None:
        indent = "\u00a0\u00a0\u00a0\u00a0" * depth   # non-breaking spaces for indentation
        result.append({
            "Plan Node":    indent + node.icon + " " + node.node_type,
            "Description":  node.description,
            "Est. Rows":    f"{node.estimated_rows:,}",
            "Startup Cost": f"{node.startup_cost:.2f}",
            "Total Cost":   f"{node.total_cost:.2f}",
        })
        for child in node.children:
            _walk(child, depth + 1)

    _walk(root, 0)
    return result


def get_all_nodes(root: PlanNode) -> list[PlanNode]:
    """Return all nodes in pre-order (root first) for chart building."""
    result: list[PlanNode] = []

    def _walk(node: PlanNode) -> None:
        result.append(node)
        for child in node.children:
            _walk(child)

    _walk(root)
    return result


def plan_cost_category(root: PlanNode) -> str:
    """Classify the root total cost as LOW / MEDIUM / HIGH."""
    cost = root.total_cost
    if cost > 50_000:
        return "HIGH"
    elif cost > 5_000:
        return "MEDIUM"
    return "LOW"


def plan_summary(root: PlanNode) -> dict:
    """Return a brief summary dict of the execution plan."""
    nodes = get_all_nodes(root)
    node_types = [n.node_type for n in nodes]
    return {
        "total_nodes":    len(nodes),
        "plan_root":      root.node_type,
        "has_seq_scan":   "Seq Scan" in node_types,
        "has_index_scan": "Index Scan" in node_types,
        "has_hash_join":  "Hash Join" in node_types,
        "has_nested_loop":"Nested Loop" in node_types,
        "has_sort":       "Sort" in node_types,
        "has_aggregate":  any(t in node_types for t in ("Aggregate", "HashAggregate")),
        "plan_cost":      root.total_cost,
        "cost_category":  plan_cost_category(root),
        "estimated_rows": root.estimated_rows,
    }
