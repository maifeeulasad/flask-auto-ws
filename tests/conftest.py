import pytest
from flask import Flask
from flask_auto_ws import AutoWS


@pytest.fixture
def app_with_socketio():
    """
    Create a fresh Flask app and AutoWS instance.
    Returns (app, auto_ws, socketio) so tests can add routes.
    """
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test"
    auto_ws = AutoWS(app)
    # Give test access to socketio instance
    socketio = auto_ws.socketio
    return app, auto_ws, socketio
