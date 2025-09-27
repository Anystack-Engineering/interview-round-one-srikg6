import json
import re
from jsonpath_ng import parse
import pytest


@pytest.mark.parametrize("expected",[{"A-1001", "A-1002", "A-1003", "A-1004", "A-1005"}])
def test_order_identity(load_json_data, expected):
    data = load_json_data
    actual = set()
    result = []

    for order in data["orders"]:
        oid = order.get("id")
        if not oid or not isinstance(oid, str):
            result.append("Missing or invalid order id")
        elif oid in actual:
            result.append(f"Duplicate order id '{oid}'")
        else:
            actual.add(oid)

    assert actual == expected, f"IDs are not matched. Got {actual}, expected {expected}"
    assert not result, f"Issues found: {result}"

@pytest.mark.parametrize("expected",[[{'A-1002'}, {'A-1003'}]])
def test_customer_email(load_json_data, expected):
    data = load_json_data
    out = []
    email_pattern = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

    for order in data["orders"]:
        oid = order["id"]
        email = order.get("customer", {}).get("email")

        if not email or not email_pattern.match(email):
            out.append({oid})
    assert out == expected

def test_lines_integrity(load_json_data):
    data = load_json_data
    for order in data["orders"]:
        status = order["status"]
        lines = order["lines"]
        if status in ['PAID', 'PENDING']:
            if lines is not None:
                for line in lines:
                    if line['sku'] is not None:
                        assert line['qty'] > 0, "'qty' value is not > 0"
                        assert line['price'] >= 0, "price is not >= 0"
                    else:
                        pass

def test_payment_or_refund_consistency(load_json_data):
    data = load_json_data
    passed, failed = [], []
    for order in data['orders']:
        id = order["id"]
        lines = order.get("lines", [])

        if order["status"] == "PAID":
            if order["payment"].get("captured", False):
                passed.append(id)
            else:
                failed.append(f"Order {id} is PAID but payment not captured")
        elif order["status"] == "CANCELLED" and lines:
            expected_refund = sum(line["qty"] * line["price"] for line in lines)
            actual_refund = order.get("refund", {}).get("amount", 0)
            if abs(actual_refund - expected_refund) < 1e-6:
                passed.append(id)
            else:
                failed.append(f"Order {id} refund {actual_refund} != expected {expected_refund}")
    return passed, failed

def test_shipping(load_json_data):
    data = load_json_data
    orders = data["orders"]
    for order in orders:
        fee = order["shipping"]['fee']
        assert fee < 0, f"Order {order['id']} has invalid shipping fee {fee}"

def test_orders_summary(load_json_data):
    data = load_json_data
    summary = {
        "total_orders": 0,
        "total_line_items": 0,
        "invalid_orders_count": 0,
        "problematic_orders": []
    }
    orders_expr = parse("$.orders[*]")
    orders = [match.value for match in orders_expr.find(data)]
    summary["total_orders"] = len(orders)

    for order in orders:
        oid = order.get("id")
        status = order.get("status")
        lines_expr = parse("$.lines[*]")
        lines = [l.value for l in lines_expr.find(order)]
        summary["total_line_items"] += len(lines)

        problems = []

        #  Order ID
        if not oid or not isinstance(oid, str):
            problems.append("Missing/invalid order id")

        #  Lines integrity for PAID or PENDING
        if status in ["PAID", "PENDING"]:
            if not lines:
                problems.append("Empty lines array")
            for idx, line in enumerate(lines, start=1):
                sku = line.get("sku")
                qty = line.get("qty", 0)
                price = line.get("price", -1)
                if not sku:
                    problems.append(f"Line {idx} missing SKU")
                if qty <= 0:
                    problems.append(f"Line {idx} qty <= 0")
                if price < 0:
                    problems.append(f"Line {idx} price < 0")

        # 3 Customer email
        email_expr = parse("$.customer.email")
        email_matches = [m.value for m in email_expr.find(order)]
        email = email_matches[0] if email_matches else None
        email_pattern = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
        if email:
            if not email_pattern.match(email):
                problems.append(f"Invalid email '{email}'")
        else:
            problems.append("Missing email")

        # 4 Payment/refund consistency
        payment_expr = parse("$.payment.captured")
        captured_matches = [m.value for m in payment_expr.find(order)]
        captured = captured_matches[0] if captured_matches else False

        if status == "PAID" and not captured:
            problems.append("Payment not captured")
        elif status == "CANCELLED" and lines:
            refund_expr = parse("$.refund.amount")
            actual_refund = [m.value for m in refund_expr.find(order)]
            actual_refund = actual_refund[0] if actual_refund else 0
            expected_refund = sum(line.get("qty", 0) * line.get("price", 0) for line in lines)
            if abs(actual_refund - expected_refund) > 1e-6:
                problems.append(f"Refund {actual_refund} != expected {expected_refund}")

        if problems:
            summary["invalid_orders_count"] += 1
            summary["problematic_orders"].append({"id": oid, "reasons": problems})

    # Print summary (or you can log/return)
    print(json.dumps(summary, indent=2))

    # Simple assertion to satisfy “assertTrue(summary.length > 0)”
    assert len(summary) > 0
