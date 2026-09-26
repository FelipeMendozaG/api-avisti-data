from django.conf import settings
from django.db import connection

from apps.imports.exceptions import ImportRepositoryError


class ImportRepository:
    def execute(self, source, json_string):
        procedure_name = settings.STORED_PROCEDURES[source]
        try:
            with connection.cursor() as cursor:
                cursor.callproc(procedure_name, [json_string])
                result = self._read_result(cursor)
                while cursor.nextset():
                    result = self._read_result(cursor)
                return result
        except Exception as exc:
            raise ImportRepositoryError("No se pudo ejecutar el procedimiento almacenado.") from exc

    def execute_excel(self, data_source, file_name, loaded_by, json_string):
        procedure_name = settings.STORED_PROCEDURES["excel"]
        try:
            with connection.cursor() as cursor:
                output_values = cursor.callproc(
                    procedure_name,
                    [data_source, file_name, loaded_by, json_string, 0, ""],
                )
                result = self._read_result(cursor)
                while cursor.nextset():
                    result = self._read_result(cursor)

                if not isinstance(result, dict):
                    result = {"result_set": result}
                escaped_procedure_name = procedure_name.replace("`", "``")
                cursor.execute(
                    f"SELECT @`_{escaped_procedure_name}_4`, @`_{escaped_procedure_name}_5`"
                )
                output_values = cursor.fetchone() or (None, None)
                result.update(
                    {
                        "load_id": output_values[0],
                        "status": output_values[1],
                    }
                )
                return result
        except Exception as exc:
            raise ImportRepositoryError("No se pudo ejecutar el procedimiento almacenado de Excel.") from exc

    @staticmethod
    def _read_result(cursor):
        if not cursor.description:
            return {}
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]