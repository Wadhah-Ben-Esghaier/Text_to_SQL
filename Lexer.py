PONCTUATION = {',', '(', ')', ';'}

def tokenize(input_str: str) -> list:
    """
    Tokenizes the input string into a list of tokens.
    """
    tokens = []
    current_token = ''
    
    for char in input_str:

        if current_token + char == "\n":
            current_token = ''

        elif char.isspace():
            if current_token:
                tokens.append(current_token)
                current_token = ''
        else:
            if char in PONCTUATION:
                if current_token:
                    tokens.append(current_token)
                    current_token = ''
                tokens.append(char)
            else:
                current_token += char
    
    if current_token:
        tokens.append(current_token)
    
    return tokens

print(tokenize("sElEcT u.id, u.email AS user_email, COUNT(o.id) total_orders \n FrOm users u \n LEFT JOIN orders o ON u.id = o.user_id AND o.status != 'CANCELLED' \n WHERE u.age >= 18 \n AND u.score <= 100.0 \n AND u.role <> 'ADMIN' \n AND u.tenant_id = '$1' \n AND u.region = :region_name \n AND u.deleted_at IS NULL \n GROUP BY u.id, u.email"))