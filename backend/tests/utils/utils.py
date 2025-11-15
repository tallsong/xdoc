def get_superuser_token_headers(client):
    """Return dummy superuser token headers for tests."""
    return {"Authorization": "Bearer superuser-test-token"}
