def authentication_token_from_email(client, email, db):
    """Return a dummy authentication header for tests.

    This is a minimal stub so conftest can import it. Real test suites
    would perform real authentication flows.
    """
    return {"Authorization": "Bearer test-token-for-" + email}
