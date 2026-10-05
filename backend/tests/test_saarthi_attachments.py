from backend.attachments import inspect_attachments
from backend.engine import SaarthiEngine, build_orchestration, classify


def test_saarthi_routes_dataset_request_without_manual_agent_selection():
    intent = classify("Create a dashboard from the uploaded Excel data", "chat")
    orchestration = build_orchestration("saarthi", intent, "Create a dashboard from the uploaded Excel data", {})
    assert orchestration["internal_specialist"] == "data_analyst"
    assert orchestration["entry"] == "Saarthi"


def test_uploaded_csv_is_parsed_before_generation():
    import base64

    raw = b"region,sales\nNorth,100\nSouth,200\n"
    encoded = "data:text/csv;base64," + base64.b64encode(raw).decode()
    inspected = inspect_attachments([{
        "name": "sales.csv",
        "type": "text/csv",
        "size": len(raw),
        "data": encoded,
    }])
    assert inspected[0]["kind"] == "file"
    assert inspected[0]["tabular"]["columns"] == ["region", "sales"]
    assert inspected[0]["tabular"]["rows"] == 2
