from Lexer import tokenize
from sql_ast import (
    ColumnRef,
    Aggregate,
    SelectItem,
    TableRef,
    JoinClause,
    Comparison,
    NullCheck,
    HavingCondition,
    OrderItem,
    SelectQuery
)


class ParserError(Exception):
    """Raised when the token sequence does not respect the SQL grammar."""

    def __init__(self, message: str, token: tuple):
        token_type, value, line, column = token

        if token_type == 'EOF':
            found = "end of query"
        else:
            found = f"{value!r} ({token_type})"

        self.line = line
        self.column = column
        self.token = token

        super().__init__(
            f"{message.rstrip('.')}. Found {found} "
            f"at line {line}, column {column}."
        )


class Parser:
    """Recursive descent parser for a restricted SQL grammar."""

    def __init__(self, tokens: list):
        if not tokens or tokens[-1][0] != 'EOF':
            raise ValueError("The token list must end with an EOF token.")

        self.tokens = tokens
        self.position = 0

    # ---------------------------------------------------------
    # Basic token navigation
    # ---------------------------------------------------------

    @property
    def current(self):
        """Return the current token without consuming it."""
        return self.tokens[self.position]

    def advance(self):
        """Consume the current token and move to the next one."""
        token = self.current

        if token[0] != 'EOF':
            self.position += 1

        return token

    def fail(self, message: str):
        """Raise a syntax error at the current token."""
        raise ParserError(message, self.current)

    # ---------------------------------------------------------
    # Token matching
    # ---------------------------------------------------------

    def check_keyword(self, keyword: str):
        """Check whether the current token is a given SQL keyword."""
        token_type, value, _, _ = self.current

        return (
            token_type == 'KEYWORD'
            and value.upper() == keyword
        )

    def match_keyword(self, keyword: str):
        """Consume a keyword if it matches."""
        if self.check_keyword(keyword):
            self.advance()
            return True

        return False

    def expect_keyword(self, keyword: str):
        """Require a specific SQL keyword."""
        if not self.match_keyword(keyword):
            self.fail(f"The keyword {keyword} was expected.")

    def match_punctuation(self, punctuation: str):
        """Consume punctuation if it matches."""
        token_type, value, _, _ = self.current

        if token_type == 'PUNCTUATION' and value == punctuation:
            self.advance()
            return True

        return False

    def expect_punctuation(self, punctuation: str):
        """Require a specific punctuation symbol."""
        if not self.match_punctuation(punctuation):
            self.fail(f"The symbol {punctuation!r} was expected.")

    def expect_identifier(self):
        """Require an identifier and return its value."""
        if self.current[0] != 'IDENTIFIER':
            self.fail("An identifier was expected.")

        return self.advance()[1]

    def expect_operator(self, allowed_operators: set):
        """Require an operator from a given set."""
        token_type, value, _, _ = self.current

        if token_type != 'OPERATOR' or value not in allowed_operators:
            self.fail("A valid comparison operator was expected.")

        return self.advance()[1]

    # ---------------------------------------------------------
    # Grammar rules
    # ---------------------------------------------------------

    def parse_query(self):
        """
        query = select_stmt, [ ";" ], EOF ;
        """
        query = self.parse_select_stmt()

        self.match_punctuation(';')

        if self.current[0] != 'EOF':
            self.fail("The end of the query was expected.")

        return query

    # ---------------------------------------------------------

    def parse_select_stmt(self):
        """
        select_stmt =
            "SELECT", [ "DISTINCT" ], select_list,
            "FROM", table_ref,
            [ inner_join ],
            [ where_clause ],
            [ group_by_clause ],
            [ having_clause ],
            [ order_by_clause ],
            [ limit_clause ] ;
        """
        self.expect_keyword('SELECT')
        distinct = self.match_keyword('DISTINCT')

        select_items = self.parse_select_list()

        self.expect_keyword('FROM')
        from_table = self.parse_table_ref()

        join = None
        where = None
        group_by = None
        having = None
        order_by = None
        limit = None

        if self.check_keyword('INNER') or self.check_keyword('JOIN'):
            join = self.parse_inner_join()

        if self.check_keyword('WHERE'):
            where = self.parse_where_clause()

        if self.check_keyword('GROUP'):
            group_by = self.parse_group_by_clause()

        if self.check_keyword('HAVING'):
            having = self.parse_having_clause()

        if self.check_keyword('ORDER'):
            order_by = self.parse_order_by_clause()

        if self.check_keyword('LIMIT'):
            limit = self.parse_limit_clause()

        return SelectQuery(
            select_items=select_items,
            from_table=from_table,
            join=join,
            where=where,
            group_by=group_by,
            having=having,
            order_by=order_by,
            limit=limit,
            distinct=distinct
        )

    # ---------------------------------------------------------

    def parse_select_list(self):
        """
        select_list = select_item, { ",", select_item } ;
        """
        items = [self.parse_select_item()]

        while self.match_punctuation(','):
            items.append(self.parse_select_item())

        return items

    # ---------------------------------------------------------

    def parse_select_item(self):
        """
        select_item =
            column_ref, [ "AS", identifier ]
            | aggregate_expr, [ "AS", identifier ] ;
        """
        if self.check_keyword('COUNT') or self.check_keyword('SUM') or self.check_keyword('AVG'):
            expression = self.parse_aggregate_expr()
        else:
            expression = self.parse_column_ref()

        alias = None

        if self.match_keyword('AS'):
            alias = self.expect_identifier()

        return SelectItem(
            expression=expression,
            alias=alias
        )

    # ---------------------------------------------------------

    def parse_table_ref(self):
        """
        table_ref = identifier, [ [ "AS" ], identifier ] ;
        """
        name = self.expect_identifier()

        alias = None

        if self.match_keyword('AS'):
            alias = self.expect_identifier()

        elif self.current[0] == 'IDENTIFIER':
            alias = self.expect_identifier()

        return TableRef(
            name=name,
            alias=alias
        )

    # ---------------------------------------------------------

    def parse_column_ref(self):
        """
        column_ref = [ identifier, "." ], identifier ;
        """
        first_identifier = self.expect_identifier()

        if self.match_punctuation('.'):
            second_identifier = self.expect_identifier()

            return ColumnRef(
                name=second_identifier,
                table=first_identifier
            )

        return ColumnRef(name=first_identifier)

    # ---------------------------------------------------------

    def parse_inner_join(self):
        """
        inner_join =
            [ "INNER" ], "JOIN", table_ref,
            "ON", column_ref, "=", column_ref ;
        """
        self.match_keyword('INNER')
        self.expect_keyword('JOIN')

        table = self.parse_table_ref()

        self.expect_keyword('ON')

        left = self.parse_column_ref()
        self.expect_operator({'='})
        right = self.parse_column_ref()

        return JoinClause(
            table=table,
            left=left,
            right=right
        )

    # ---------------------------------------------------------

    def parse_where_clause(self):
        """
        where_clause = "WHERE", condition, { "AND", condition } ;
        """
        self.expect_keyword('WHERE')

        conditions = [self.parse_condition()]

        while self.match_keyword('AND'):
            conditions.append(self.parse_condition())

        return conditions

    # ---------------------------------------------------------

    def parse_condition(self):
        """
        condition =
            column_ref, comparison_operator, literal
            | column_ref, "IS", [ "NOT" ], "NULL" ;
        """
        column = self.parse_column_ref()

        if self.match_keyword('IS'):
            is_not = self.match_keyword('NOT')
            self.expect_keyword('NULL')

            return NullCheck(
                column=column,
                is_not=is_not
            )

        operator = self.expect_operator(
            {'=', '<>', '<', '<=', '>', '>='}
        )

        value = self.parse_literal()

        return Comparison(
            left=column,
            operator=operator,
            right=value
        )

    # ---------------------------------------------------------

    def parse_group_by_clause(self):
        """
        group_by_clause =
            "GROUP", "BY", column_ref, { ",", column_ref } ;
        """
        self.expect_keyword('GROUP')
        self.expect_keyword('BY')

        columns = [self.parse_column_ref()]

        while self.match_punctuation(','):
            columns.append(self.parse_column_ref())

        return columns

    # ---------------------------------------------------------

    def parse_having_clause(self):
        """
        having_clause =
            "HAVING", aggregate_expr,
            comparison_operator, literal ;
        """
        self.expect_keyword('HAVING')

        aggregate = self.parse_aggregate_expr()

        operator = self.expect_operator(
            {'=', '<>', '<', '<=', '>', '>='}
        )

        value = self.parse_literal()

        return HavingCondition(
            aggregate=aggregate,
            operator=operator,
            value=value
        )

    # ---------------------------------------------------------

    def parse_aggregate_expr(self):
        """
        aggregate_expr =
            "COUNT", "(", ( "*" | column_ref ), ")"
            | ( "SUM" | "AVG" ), "(", column_ref, ")" ;
        """
        if self.match_keyword('COUNT'):
            function = 'COUNT'

        elif self.match_keyword('SUM'):
            function = 'SUM'

        elif self.match_keyword('AVG'):
            function = 'AVG'

        else:
            self.fail("An aggregate function was expected.")

        self.expect_punctuation('(')

        if function == 'COUNT' and self.match_punctuation('*'):
            column = None
        else:
            column = self.parse_column_ref()

        self.expect_punctuation(')')

        return Aggregate(
            function=function,
            column=column
        )

    # ---------------------------------------------------------

    def parse_order_by_clause(self):
        """
        order_by_clause =
            "ORDER", "BY", order_item, { ",", order_item } ;
        """
        self.expect_keyword('ORDER')
        self.expect_keyword('BY')

        items = [self.parse_order_item()]

        while self.match_punctuation(','):
            items.append(self.parse_order_item())

        return items

    # ---------------------------------------------------------

    def parse_order_item(self):
        """
        order_item = order_expression, [ "ASC" | "DESC" ] ;
        """
        if self.check_keyword('COUNT') or self.check_keyword('SUM') or self.check_keyword('AVG'):
            expression = self.parse_aggregate_expr()
        else:
            expression = self.parse_column_ref()

        direction = 'ASC'

        if self.match_keyword('DESC'):
            direction = 'DESC'

        else:
            self.match_keyword('ASC')

        return OrderItem(
            expression=expression,
            direction=direction
        )

    # ---------------------------------------------------------

    def parse_limit_clause(self):
        """
        limit_clause = "LIMIT", unsigned_integer ;
        """
        self.expect_keyword('LIMIT')

        token_type, value, _, _ = self.current

        if token_type != 'NUMBER' or not value.isdigit():
            self.fail("LIMIT must be followed by a non-negative integer.")

        self.advance()

        return int(value)

    # ---------------------------------------------------------

    def parse_literal(self):
        """
        literal = number | string ;
        """
        token_type, value, _, _ = self.current

        if token_type == 'STRING':
            self.advance()
            return value

        if token_type == 'NUMBER':
            self.advance()

            if '.' in value:
                return float(value)

            return int(value)

        self.fail("A number or a string literal was expected.")


# -------------------------------------------------------------
# Convenient function to parse a SQL query directly
# -------------------------------------------------------------

def parse_sql(input_str: str):
    tokens = tokenize(input_str)
    parser = Parser(tokens)

    return parser.parse_query()
