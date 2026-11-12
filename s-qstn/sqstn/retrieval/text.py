def text_for(row: dict) -> str:
    return f"{row['query']} Tool: {row['tool']} Data: {row['raw_data_type']}"
