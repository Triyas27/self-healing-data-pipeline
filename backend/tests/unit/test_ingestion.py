import io

from app.core.pipeline.ingestion import read_csv_rows


def test_read_from_list_passthrough_normalizes():
    rows = [{" Order_ID ": " ORD-000001 ", "customer_id": "CUST-0001"}]
    normalized = read_csv_rows(rows)
    assert normalized == [{"order_id": "ORD-000001", "customer_id": "CUST-0001"}]


def test_read_from_file_like_object_normalizes_headers_and_values():
    csv_text = " Order_ID , Customer_ID \n ORD-000001 , CUST-0001 \n"
    rows = read_csv_rows(io.StringIO(csv_text))
    assert rows == [{"order_id": "ORD-000001", "customer_id": "CUST-0001"}]


def test_read_from_file_path(tmp_path):
    csv_path = tmp_path / "batch.csv"
    csv_path.write_text("Order_ID,Customer_ID\nORD-000001,CUST-0001\n", encoding="utf-8")
    rows = read_csv_rows(csv_path)
    assert rows == [{"order_id": "ORD-000001", "customer_id": "CUST-0001"}]


def test_read_from_bytes_file_like_object():
    csv_bytes = io.BytesIO(b"Order_ID,Customer_ID\nORD-000001,CUST-0001\n")
    rows = read_csv_rows(csv_bytes)
    assert rows == [{"order_id": "ORD-000001", "customer_id": "CUST-0001"}]
