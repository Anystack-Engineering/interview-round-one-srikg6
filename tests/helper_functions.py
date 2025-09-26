import json
# import orders.json

def load_json_data():
    try:
        with open("E:\interview-round-one-srikg6\orders.json") as f:
            data = json.load(f)
        return data
    except Exception as e:
        return e

def assert_true(condition, message):
    if not condition:
        print("FAIL:", message)
    else:
        print("PASS:", message)