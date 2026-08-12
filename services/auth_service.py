import hashlib
import streamlit as st

def _hash_password(password: str) -> str:
    """Hashes a plaintext password using SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def is_admin_authenticated() -> bool:
    """Checks if the current session is authenticated as admin."""
    return st.session_state.get("is_admin", False)

def login(username, password) -> bool:
    """
    Validates credentials against st.secrets.
    Sets st.session_state['is_admin'] = True on success.
    """
    try:
        admin_secrets = st.secrets.get("admin", {})
        stored_user = admin_secrets.get("ADMIN_USERNAME")
        stored_hash = admin_secrets.get("ADMIN_PASSWORD_HASH")
        
        if not stored_user or not stored_hash:
            st.error("Admin secrets not configured properly in .streamlit/secrets.toml.")
            return False
            
    except Exception as e:
        st.error(f"Error reading secrets: {e}")
        return False

    if username == stored_user and _hash_password(password) == stored_hash:
        st.session_state["is_admin"] = True
        return True
    
    return False

def logout():
    """Logs out the current admin session."""
    if "is_admin" in st.session_state:
        st.session_state["is_admin"] = False

def require_admin():
    """
    Raises a PermissionError if the current session is not authenticated as admin.
    Use this to protect backend functions and expensive AI generation entry points.
    """
    if not is_admin_authenticated():
        raise PermissionError("Admin authorization required to perform this action.")
