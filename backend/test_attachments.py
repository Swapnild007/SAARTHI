import base64
import csv
import io

from backend.attachments import inspect_attachment, build_tabular_dataset


def _csv_data(rows):
    text = io.StringIO()
    writer = csv.writer(text)
    writer.writerows(rows)
    return base64.b64encode(text.getvalue().encode()).decode()


def test_csv_preserves_bounded_analysis_rows():
    rows = [["region", "sales"]] + [[f"R{i}", i] for i in range(250)]
    item = inspect_attachment({
        "name": "sales.csv",
        "type": "text/csv",
        "data": _csv_data(rows),
    })
    dataset = build_tabular_dataset(item)
    assert dataset["columns"] == ["region", "sales"]
    assert dataset["row_count"] == 250
    assert len(dataset["rows"]) == 250
