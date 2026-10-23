import json
import pytest
from pathlib import Path
from src.facebook.session import FacebookSessionManager

def test_save_manual_cookies(tmp_path):
    state_file = tmp_path / "fb_auth.json"
    mgr = FacebookSessionManager(state_path=state_file, profile_dir=tmp_path / "profile")

    assert not mgr.has_saved_session()

    success = mgr.save_manual_cookies("100012345678", "xs_dummy_token_value")
    assert success is True
    assert mgr.has_saved_session()

    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    cookie_names = [c["name"] for c in data["cookies"]]
    assert "c_user" in cookie_names
    assert "xs" in cookie_names

def test_save_cookie_string(tmp_path):
    state_file = tmp_path / "fb_auth.json"
    mgr = FacebookSessionManager(state_path=state_file, profile_dir=tmp_path / "profile")

    cookie_header = "sb=abc; datr=def; c_user=987654321; xs=secret_session_token; wd=1920x1080"
    success = mgr.save_cookie_string(cookie_header)
    assert success is True
    assert mgr.has_saved_session()

    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    c_user_val = next(c["value"] for c in data["cookies"] if c["name"] == "c_user")
    xs_val = next(c["value"] for c in data["cookies"] if c["name"] == "xs")
    assert c_user_val == "987654321"
    assert xs_val == "secret_session_token"
