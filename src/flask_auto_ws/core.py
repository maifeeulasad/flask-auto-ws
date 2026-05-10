import json
from functools import wraps
from typing import Any, Callable, Iterable, Optional

from flask import Flask
import flask_socketio


class AutoWS:
    """
    Flask-Auto-WS: automatically convert generator/iterable returns from Flask routes
    into WebSocket streams using Flask‑SocketIO (or a custom handler).

    Modes:
        - 'append'   : send each item as a separate message (default)
        - 'replace'  : send each item with a 'replace' flag (client replaces previous content)
        - 'full'     : exhaust the generator and send the whole list as one message
    """

    def __init__(
        self,
        app: Optional[Flask] = None,
        socketio: Optional[flask_socketio.SocketIO] = None,
        ws_library: Optional[Any] = None,
    ):
        """
        :param app: Flask application instance (can be set later via init_app)
        :param socketio: existing Flask‑SocketIO instance; if None, one is created.
        :param ws_library: optional custom WebSocket library (must provide on(), emit(), etc.)
        """
        self.app = app
        self.socketio = socketio or flask_socketio.SocketIO()
        self.ws_library = ws_library or self.socketio  # default to flask-SocketIO

        if self.app:
            self.init_app(self.app)

    def init_app(self, app: Flask):
        """Initialize the Flask app and attach the SocketIO instance."""
        self.app = app
        self.socketio.init_app(app)

    def stream(self, route: str, mode: str = "append", **kwargs):
        """
        Decorator that registers a WebSocket event handler for `route`.
        The decorated function must return an iterable/generator.
        Each yielded item will be sent to the client via WebSocket.

        :param route: WebSocket namespace/event name (e.g., '/data')
        :param mode: streaming mode ('append', 'replace', 'full')
        :param kwargs: extra arguments passed to the sink function (e.g., namespace)
        """
        if mode not in ("append", "replace", "full"):
            raise ValueError("mode must be one of: 'append', 'replace', 'full'")

        # We'll use the default namespace, with the event name being the route path.
        # For cleaner usage, we map '/data' to an event 'stream_data' (or similar).
        # Alternatively, we can use a namespace that matches the route.
        event_name = route.lstrip("/").replace("/", "_")  # e.g., 'data'

        def decorator(func: Callable[..., Iterable]):
            @wraps(func)
            def sink(*args, **kwargs_sink):
                try:
                    iterator = func(*args, **kwargs_sink)
                    if mode == "full":
                        # Exhaust the generator and send all items as a single JSON array
                        all_items = list(iterator)
                        self._send_message(all_items, event=event_name, mode="full")
                    else:
                        for item in iterator:
                            self._send_message(item, event=event_name, mode=mode)
                except Exception as e:
                    # Send the error to the client as a JSON error message
                    error_msg = {"error": str(e)}
                    self._send_message(error_msg, event=event_name, mode=mode)

            # Register the sink as a WebSocket event handler
            # Use .on_event for Flask-SocketIO, .on for custom/mock
            if hasattr(self.ws_library, "on_event"):
                self.ws_library.on_event(event_name, sink)
            else:
                self.ws_library.on(event_name, sink)
            return sink

        return decorator

    def _send_message(self, data, event: str, mode: str):
        """
        Serialise and emit the data over WebSocket.
        Handles all C‑escape characters via JSON serialisation.
        """
        # Always convert to a JSON‑safe structure.
        if isinstance(data, (str, bytes)):
            # If the user yields a plain string/bytes, wrap it for consistency.
            payload = json.dumps({"data": data})
        else:
            # For any other object, we directly JSON‑dumps it.
            # This guarantees proper escape of \n, \r, \t, etc.
            payload = json.dumps(data)

        # Attach mode information for clients that care.
        if mode == "replace":
            # Wrap in an envelope: {"type": "replace", "content": ...}
            envelope = json.dumps({"type": "replace", "content": json.loads(payload)})
        elif mode == "full":
            envelope = json.dumps({"type": "full", "content": json.loads(payload)})
        else:  # append
            envelope = payload

        # Emit over the default SocketIO connection.
        # Using the same event name the client subscribed to.
        self.ws_library.emit(event, envelope)
