"""Restrict access to the protected vehicle app before opening the database."""

from hashlib import sha256
from hmac import compare_digest
from time import monotonic

import streamlit as st

SESSION_TTL = 12 * 60 * 60
RETRY_DELAY = 20
SESSION_KEY = "veiculos_access_session"


def secret(name):
    try:
        value = st.secrets.get(name)
    except FileNotFoundError:
        return None
    return value if isinstance(value, str) and value else None


def session_active(password):
    session = st.session_state.get(SESSION_KEY)
    return bool(password and session and session["expires_at"] > monotonic()
                and compare_digest(session["revision"], sha256(password.encode("utf-8")).digest()))


def require_access(password):
    if not password or len(password) < 20:
        st.error("O acesso ao Controle de Veículos ainda não foi configurado.")
        st.stop()

    revision = sha256(password.encode("utf-8")).digest()
    now = monotonic()
    if session_active(password):
        if st.button("Sair", key="veiculos_access_logout"):
            st.session_state.pop(SESSION_KEY)
            st.rerun()
        return

    st.session_state.pop(SESSION_KEY, None)
    st.title("Controle de Veículos")
    st.caption("Acesso da equipe 10 Sul")
    with st.form("veiculos_access", clear_on_submit=True):
        attempt = st.text_input("Senha de acesso", type="password", max_chars=256)
        submitted = st.form_submit_button("Entrar", type="primary")
    if submitted:
        if st.session_state.get("veiculos_access_retry_at", 0) > now:
            st.error("Aguarde alguns segundos antes de tentar novamente.")
        elif compare_digest(sha256(attempt.encode("utf-8")).digest(), revision):
            st.session_state[SESSION_KEY] = {"revision": revision, "expires_at": now + SESSION_TTL}
            st.session_state.pop("veiculos_access_retry_at", None)
            st.rerun()
        else:
            st.session_state["veiculos_access_retry_at"] = now + RETRY_DELAY
            st.error("Senha de acesso inválida.")
    st.stop()
