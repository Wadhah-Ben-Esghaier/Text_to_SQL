from sql_ast import (
    Aggregate,
    ColumnRef,
    Comparison,
    HavingCondition,
    JoinClause,
    NullCheck,
    OrderItem,
    SelectItem,
    SelectQuery,
    TableRef,
)


def format_ast(query: SelectQuery) -> str:
    clauses = (
        ('SELECT', ', '.join(map(_format_node, query.select_items))),
        ('FROM', query.from_table),
        ('INNER JOIN', query.join),
        ('WHERE', ' AND '.join(map(_format_node, query.where)) if query.where else None),
        ('GROUP BY', ', '.join(map(_format_node, query.group_by)) if query.group_by else None),
        ('HAVING', query.having),
        ('ORDER BY', ', '.join(map(_format_node, query.order_by)) if query.order_by else None),
        ('LIMIT', query.limit),
    )
    lines = ['Arbre syntaxique (AST)']
    lines.extend(f'  {name:<10} {_format_node(value)}' for name, value in clauses if value is not None)
    return '\n'.join(lines)


def _format_node(node) -> str:
    match node:
        case ColumnRef(name, table):
            return f'{table}.{name}' if table is not None else name
        case TableRef(name, alias):
            return f'{name} AS {alias}' if alias is not None else name
        case Aggregate(function, column):
            argument = '*' if column is None else _format_node(column)
            return f'{function}({argument})'
        case SelectItem(expression, alias):
            expression_text = _format_node(expression)
            return f'{expression_text} AS {alias}' if alias is not None else expression_text
        case JoinClause(table, left, right):
            return f'{_format_node(table)} ON {_format_node(left)} = {_format_node(right)}'
        case Comparison(left, operator, right) | HavingCondition(left, operator, right):
            return f'{_format_node(left)} {operator} {right!r}'
        case NullCheck(column, is_not):
            operator = 'IS NOT NULL' if is_not else 'IS NULL'
            return f'{_format_node(column)} {operator}'
        case OrderItem(expression, direction):
            return f'{_format_node(expression)} {direction}'
        case _:
            return str(node)


def format_results(headers: list[str], rows: list[tuple]) -> str:
    escaped_whitespace = str.maketrans({'\n': r'\n', '\r': r'\r', '\t': r'\t'})
    cells = [
        ['NULL' if value is None else str(value).translate(escaped_whitespace) for value in row]
        for row in [headers, *rows]
    ]
    widths = [max(map(len, column)) for column in zip(*cells)]
    formatted_rows = [
        ' | '.join(value.ljust(width) for value, width in zip(row, widths)).rstrip()
        for row in cells
    ]
    separator = '-+-'.join('-' * width for width in widths)
    return '\n'.join([
        f'Résultat Chinook ({len(rows)} ligne{"s" if len(rows) > 1 else ""})',
        formatted_rows[0],
        separator,
        *formatted_rows[1:],
    ])
