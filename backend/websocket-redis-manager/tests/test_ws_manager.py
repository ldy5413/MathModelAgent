import pytest
from fastapi import WebSocket
from src.core.ws_manager import WebSocketManager

@pytest.fixture
def websocket_manager():
    return WebSocketManager()

@pytest.fixture
def mock_websocket():
    class MockWebSocket:
        def __init__(self):
            self.accepted = False
            self.messages = []

        async def accept(self):
            self.accepted = True

        async def send_text(self, message: str):
            self.messages.append(message)

        async def send_json(self, message: dict):
            self.messages.append(message)

    return MockWebSocket()

def test_connect(websocket_manager, mock_websocket):
    assert len(websocket_manager.active_connections) == 0
    await websocket_manager.connect(mock_websocket)
    assert len(websocket_manager.active_connections) == 1
    assert mock_websocket.accepted is True

def test_disconnect(websocket_manager, mock_websocket):
    await websocket_manager.connect(mock_websocket)
    assert len(websocket_manager.active_connections) == 1
    await websocket_manager.disconnect(mock_websocket)
    assert len(websocket_manager.active_connections) == 0

def test_send_personal_message(websocket_manager, mock_websocket):
    await websocket_manager.connect(mock_websocket)
    await websocket_manager.send_personal_message("Hello", mock_websocket)
    assert mock_websocket.messages == ["Hello"]

def test_broadcast(websocket_manager, mock_websocket):
    await websocket_manager.connect(mock_websocket)
    await websocket_manager.broadcast("Broadcast message")
    assert mock_websocket.messages == ["Broadcast message"]