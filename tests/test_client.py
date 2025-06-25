"""
Tests for the Tansive client.
"""

from tansive.skillset_sdk import TansiveClient


def test_client_initialization():
    """Test that the client can be initialized with a socket path."""
    client = TansiveClient("/tmp/tangent.sock")
    assert isinstance(client, TansiveClient)
