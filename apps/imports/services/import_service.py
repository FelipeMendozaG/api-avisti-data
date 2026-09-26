import json


class ImportService:
    def __init__(self, repository):
        self.repository = repository

    def process(self, records, source):
        json_string = json.dumps(records, ensure_ascii=False)
        result = self.repository.execute(source, json_string)
        return self._build_result(records, result)

    def process_excel(self, records, data_source, file_name, loaded_by):
        json_string = json.dumps(records, ensure_ascii=False)
        result = self.repository.execute_excel(data_source, file_name, loaded_by, json_string)
        return self._build_result(records, result)

    @staticmethod
    def _build_result(records, result):
        return {
            "records_received": len(records),
            "records_processed": result.get("records_processed", len(records)) if isinstance(result, dict) else len(records),
            "records_rejected": result.get("records_rejected", 0) if isinstance(result, dict) else 0,
            "procedure_result": result,
        }