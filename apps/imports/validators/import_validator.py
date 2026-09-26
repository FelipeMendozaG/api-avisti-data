from apps.imports.exceptions import ImportValidationError


def validate_records(records, required_columns=None):
    if not records:
        raise ImportValidationError("El archivo no contiene registros.", {"file": "empty"})

    required_columns = required_columns or []
    missing_columns = [column for column in required_columns if column not in records[0]]
    if missing_columns:
        raise ImportValidationError("Faltan columnas requeridas.", {"columns": missing_columns})

    invalid_rows = []
    for index, record in enumerate(records, start=2):
        if not isinstance(record, dict) or not any(value not in (None, "") for value in record.values()):
            invalid_rows.append(index)
            continue
        missing_values = [column for column in required_columns if record.get(column) in (None, "")]
        if missing_values:
            invalid_rows.append({"row": index, "columns": missing_values})

    if invalid_rows:
        raise ImportValidationError("Hay filas inválidas.", {"rows": invalid_rows})

    return records