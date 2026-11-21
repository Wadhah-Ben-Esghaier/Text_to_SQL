from dataclasses import dataclass


# A reference to a column, optionally qualified by a table name or alias
@dataclass
class ColumnRef:
    name: str
    table: str | None = None


# An aggregate expression: COUNT(*) or SUM(column), for example
@dataclass
class Aggregate:
    function: str
    column: ColumnRef | None = None


# An item in the SELECT clause
@dataclass
class SelectItem:
    expression: ColumnRef | Aggregate
    alias: str | None = None


# A table, optionally associated with an alias
@dataclass
class TableRef:
    name: str
    alias: str | None = None


# An INNER JOIN between two tables
@dataclass
class JoinClause:
    table: TableRef
    left: ColumnRef
    right: ColumnRef


# A comparison such as CustomerId = 42
@dataclass
class Comparison:
    left: ColumnRef
    operator: str
    right: int | float | str


# A NULL condition such as Company IS NULL
@dataclass
class NullCheck:
    column: ColumnRef
    is_not: bool = False


# A condition in the HAVING clause
@dataclass
class HavingCondition:
    aggregate: Aggregate
    operator: str
    value: int | float | str


# An item in the ORDER BY clause
@dataclass
class OrderItem:
    expression: ColumnRef | Aggregate
    direction: str = "ASC"


# The complete SQL query
@dataclass
class SelectQuery:
    select_items: list[SelectItem]
    from_table: TableRef

    join: JoinClause | None = None
    where: list[Comparison | NullCheck] | None = None
    group_by: list[ColumnRef] | None = None
    having: HavingCondition | None = None
    order_by: list[OrderItem] | None = None
    limit: int | None = None