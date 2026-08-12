import pytest
import streamlit as st
import hashlib
from services.auth_service import login, logout, require_admin, is_admin_authenticated

# Mock Streamlit session state and secrets for tests
class MockSessionState(dict):
    pass

@pytest.fixture(autouse=True)
def mock_streamlit(monkeypatch):
    monkeypatch.setattr(st, "session_state", MockSessionState())
    test_hash = hashlib.sha256("test_pass".encode('utf-8')).hexdigest()
    
    class MockSecrets(dict):
        def __init__(self):
            super().__init__()
            self["admin"] = {
                "ADMIN_USERNAME": "admin",
                "ADMIN_PASSWORD_HASH": test_hash
            }
            
    monkeypatch.setattr(st, "secrets", MockSecrets())
    
    # Mock st.error to avoid side effects
    monkeypatch.setattr(st, "error", lambda x: None)

def test_public_user_cannot_synthesize():
    st.session_state.clear() # Not logged in
    
    assert not is_admin_authenticated()
    
    with pytest.raises(PermissionError, match="Admin authorization required to perform this action."):
        require_admin()

def test_login_success():
    st.session_state.clear()
    
    assert login("admin", "test_pass") == True
    assert st.session_state["is_admin"] == True
    assert is_admin_authenticated() == True
    
    # require_admin should not raise an error
    require_admin()

def test_login_failure():
    st.session_state.clear()
    
    assert login("admin", "wrong_pass") == False
    assert st.session_state.get("is_admin") is None
    
    with pytest.raises(PermissionError):
        require_admin()

def test_logout():
    st.session_state["is_admin"] = True
    logout()
    
    assert st.session_state["is_admin"] == False
    assert not is_admin_authenticated()
