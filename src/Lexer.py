
PONCTUATION = {',', '(', ')', ';', '.','*'}
OPERATORS = {'=', '<', '>', '<=', '>=', '<>'}

KEYWORDS = {
    'SELECT', 'DISTINCT', 'FROM', 'AS',
    'INNER', 'JOIN', 'ON',
    # Reserved to reject unsupported joins instead of treating them as aliases.
    'LEFT', 'RIGHT', 'FULL', 'OUTER', 'CROSS', 'NATURAL',
    'WHERE', 'AND', 'IS', 'NOT', 'NULL',
    'GROUP', 'BY', 'HAVING',
    'ORDER', 'ASC', 'DESC',
    'LIMIT', 'COUNT', 'SUM', 'AVG'
}

def tokenize(input_str: str) -> list:
    """
    Tokenizes the input string into a list of typed tokens.
    Each token contains its type, value, line and column.
    """
    tokens = []
    current_token = ''
    i = 0
    line = 1
    column = 1

    while i < len(input_str):
        char = input_str[i]

        # Ignore whitespace
        if char.isspace():
            if current_token:
                value = current_token
                token_type = (
                    'KEYWORD' if value.upper() in KEYWORDS
                    else 'IDENTIFIER'
                )
                tokens.append((token_type, value, line, column - len(value)))
                current_token = ''

            if char == '\n':
                line += 1
                column = 1
            else:
                column += 1

            i += 1
            continue

        # Handle strings
        if char == "'":
            if current_token:
                value = current_token
                token_type = (
                    'KEYWORD' if value.upper() in KEYWORDS
                    else 'IDENTIFIER'
                )
                tokens.append((token_type, value, line, column - len(value)))
                current_token = ''

            start_line = line
            start_column = column
            string_value = ''
            i += 1
            column += 1

            while i < len(input_str):
                char = input_str[i]

                if char == "'":
                    # Escaped quote: ''
                    if i + 1 < len(input_str) and input_str[i + 1] == "'":
                        string_value += "'"
                        i += 2
                        column += 2
                    else:
                        i += 1
                        column += 1
                        break
                else:
                    string_value += char
                    if char == '\n':
                        line += 1
                        column = 1
                    else:
                        column += 1
                    i += 1
            else:
                raise ValueError(
                    f"Unterminated string at line {start_line}, "
                    f"column {start_column}"
                )

            tokens.append(('STRING', string_value, start_line, start_column))
            continue

        # Handle punctuation
        if char in PONCTUATION:
            if current_token:
                value = current_token
                token_type = (
                    'KEYWORD' if value.upper() in KEYWORDS
                    else 'IDENTIFIER'
                )
                tokens.append((token_type, value, line, column - len(value)))
                current_token = ''

            tokens.append(('PUNCTUATION', char, line, column))
            i += 1
            column += 1
            continue

        # Handle operators (longest operator first)
        if char in {'=', '<', '>'}:
            if current_token:
                value = current_token
                token_type = (
                    'KEYWORD' if value.upper() in KEYWORDS
                    else 'IDENTIFIER'
                )
                tokens.append((token_type, value, line, column - len(value)))
                current_token = ''

            operator = char

            if i + 1 < len(input_str):      #Regarde si l'opérateur global est composé de deux opérateurs (ex <=)
                pair = char + input_str[i + 1]
                if pair in OPERATORS:               
                    operator = pair

            tokens.append(('OPERATOR', operator, line, column))
            i += len(operator)
            column += len(operator)
            continue

        # Handle numbers (including negative numbers)
        if not current_token and (
            char.isdigit()
            or (char == '-' and i + 1 < len(input_str) and input_str[i + 1].isdigit())
        ):
            start_column = column
            number = char
            i += 1
            column += 1

            while i < len(input_str) and input_str[i].isdigit():   #Regarde si c'est un nombre composé de plusieurs chiffre ou un négatif
                number += input_str[i]
                i += 1
                column += 1

            # Decimal part
            if i < len(input_str) and input_str[i] == '.':     #Regarde si c'est un nb décimal
                if i + 1 < len(input_str) and input_str[i + 1].isdigit():
                    number += '.'
                    i += 1
                    column += 1

                    while i < len(input_str) and input_str[i].isdigit():
                        number += input_str[i]
                        i += 1
                        column += 1

            tokens.append(('NUMBER', number, line, start_column))
            continue

        # Build the current token (identifier or keyword)
        if char.isalnum() or char == '_':
            current_token += char
            i += 1
            column += 1
            continue

        # Unknown character
        raise ValueError(
            f"Unexpected character {char!r} "
            f"at line {line}, column {column}"
        )

    # Flush the final token
    if current_token:
        value = current_token
        token_type = (
            'KEYWORD' if value.upper() in KEYWORDS
            else 'IDENTIFIER'
        )
        tokens.append((token_type, value, line, column - len(value)))

    tokens.append(('EOF', '', line, column))
    return tokens



