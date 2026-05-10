import json
from flask import Flask
from flask_auto_ws import AutoWS


def test_append_mode(app_with_socketio):
    """Test default append mode: each item sent as an individual message."""
    app, auto_ws, socketio = app_with_socketio

    @auto_ws.stream("/numbers", mode="append")
    def number_stream(_):
        for i in range(3):
            yield {"num": i}

    client = socketio.test_client(app, namespace="/")
    # Connect to the default namespace
    client.connect()
    # The handler is registered for event 'numbers'
    client.emit("numbers", {})  # trigger the generator

    received = client.get_received("/")
    # Filter out connection‑setup messages, keep only 'numbers' events
    data_events = [event for event in received if event["name"] == "numbers"]
    assert len(data_events) == 3
    for idx, event in enumerate(data_events):
        payload = json.loads(event["args"][0])
        assert payload == {"num": idx}


def test_replace_mode(app_with_socketio):
    """Replace mode should wrap each message in a 'replace' envelope."""
    app, auto_ws, socketio = app_with_socketio

    @auto_ws.stream("/status", mode="replace")
    def status_gen(_):
        for status in ["started", "processing", "done"]:
            yield {"status": status}

    client = socketio.test_client(app, namespace="/")
    client.connect()
    client.emit("status", {})

    received = client.get_received("/")
    data_events = [e for e in received if e["name"] == "status"]
    assert len(data_events) == 3
    for i, event in enumerate(data_events):
        envelope = json.loads(event["args"][0])
        assert envelope["type"] == "replace"
        assert envelope["content"] == {"status": ["started", "processing", "done"][i]}


def test_full_mode(app_with_socketio):
    """Full mode sends the entire list as one message."""
    app, auto_ws, socketio = app_with_socketio

    @auto_ws.stream("/full", mode="full")
    def all_data(_):
        return [1, 2, 3, 4]  # iterable (list is fine)

    client = socketio.test_client(app, namespace="/")
    client.connect()
    client.emit("full", {})

    received = client.get_received("/")
    full_events = [e for e in received if e["name"] == "full"]
    assert len(full_events) == 1
    envelope = json.loads(full_events[0]["args"][0])
    assert envelope["type"] == "full"
    assert envelope["content"] == [1, 2, 3, 4]


def test_escape_characters_handled(app_with_socketio):
    """Ensure that escape characters (e.g., newlines, tabs) survive JSON serialisation."""
    app, auto_ws, socketio = app_with_socketio

    special_string = 'Line1\nLine2\tTab\rReturn\\Backslash"Quote'

    @auto_ws.stream("/escapes")
    def escape_gen(_):
        yield {"text": special_string}

    client = socketio.test_client(app, namespace="/")
    client.connect()
    client.emit("escapes", {})

    received = client.get_received("/")
    data_events = [e for e in received if e["name"] == "escapes"]
    assert len(data_events) == 1
    payload = json.loads(data_events[0]["args"][0])
    assert payload["text"] == special_string


def test_custom_ws_library():
    """
    Demonstration of plugging a custom WebSocket handler.
    This test creates a mock handler that simply records messages.
    """

    class MockWS:
        def __init__(self):
            self.handlers = {}
            self.sent = []

        def on(self, event, handler):
            self.handlers[event] = handler

        def emit(self, event, data):
            self.sent.append((event, data))

    app = Flask(__name__)
    mock = MockWS()
    auto_ws = AutoWS(app, ws_library=mock)

    @auto_ws.stream("/custom")
    def custom_gen():
        yield 42

    # Simulate a WebSocket call
    mock.handlers["custom"]()
    assert len(mock.sent) == 1
    assert mock.sent[0][0] == "custom"
    assert json.loads(mock.sent[0][1]) == 42
