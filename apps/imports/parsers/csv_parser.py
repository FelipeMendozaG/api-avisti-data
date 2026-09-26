import csv
import io

from django.conf import settings

from apps.imports.exceptions import ImportValidationError


class CSVParser:
    def parse(self, uploaded_file):
        self._validate_file(uploaded_file)
        delimiter = settings.IMPORT_CSV_DELIMITER
        if len(delimiter) != 1:
            raise ImportValidationError("El separador CSV debe ser un solo carácter.", {"delimiter": delimiter})

        try:
            content = uploaded_file.read().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ImportValidationError("El CSV debe utilizar encoding UTF-8.", {"file": "invalid_encoding"}) from exc

        reader = csv.DictReader(io.StringIO(content, newline=""), delimiter=delimiter)
        headers = [header.strip() if header else "" for header in (reader.fieldnames or [])]

        records = []
        for row in reader:
            records.append({header: row.get(original) for original, header in zip(reader.fieldnames, headers)})

        return records

    @staticmethod
    def _validate_file(uploaded_file):
        if not uploaded_file:
            raise ImportValidationError("Debe enviar un archivo.", {"file": "required"})
        if not uploaded_file.name.lower().endswith(".csv"):
            raise ImportValidationError("La extensión debe ser .csv.", {"file": "invalid_extension"})
        if uploaded_file.size > settings.IMPORT_MAX_FILE_SIZE_BYTES:
            raise ImportValidationError("El archivo excede el tamaño permitido.", {"file": "too_large"})