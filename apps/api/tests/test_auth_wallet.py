"""Wallet challenge-response login (see app/auth/providers/wallet.py).

Simulates the browser-side signature an OKX Wallet popup would produce
using a throwaway eth_account keypair — this exercises every server-side
code path (nonce issuance, signature recovery, session cookie, workspace
creation, repeat-login identity, rejection cases) without needing a real
browser extension.
"""

from datetime import datetime, timedelta, timezone

from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy import select

from app.auth.session import SESSION_COOKIE_NAME
from app.models.auth_challenge import AuthChallenge
from app.models.organization import Organization
from app.models.user import User


def _sign(message: str, private_key) -> str:
    signed = Account.sign_message(encode_defunct(text=message), private_key=private_key)
    return signed.signature.hex()


async def _login(client, address: str, private_key):
    nonce_resp = await client.post("/api/v1/auth/wallet/nonce", json={"address": address})
    assert nonce_resp.status_code == 200
    body = nonce_resp.json()

    signature = _sign(body["message"], private_key)
    return await client.post(
        "/api/v1/auth/wallet/verify",
        json={"address": address, "signature": signature, "nonce": body["nonce"]},
    )


async def test_wallet_login_creates_workspace(client, db_session):
    account = Account.create()

    resp = await _login(client, account.address, account.key)
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] is True
    assert data["user"]["wallet_address"] == account.address.lower()
    assert data["organization"]["name"]
    assert SESSION_COOKIE_NAME in resp.cookies

    result = await db_session.execute(select(User).where(User.wallet_address == account.address.lower()))
    user = result.scalar_one()
    assert user.last_login_at is not None

    result = await db_session.execute(select(Organization).where(Organization.id == user.org_id))
    assert result.scalar_one_or_none() is not None


async def test_repeat_login_reuses_workspace(client):
    account = Account.create()

    first = await _login(client, account.address, account.key)
    second = await _login(client, account.address, account.key)

    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["user"]["id"] == second.json()["user"]["id"]
    assert first.json()["organization"]["id"] == second.json()["organization"]["id"]


async def test_session_cookie_authorizes_subsequent_requests(client):
    account = Account.create()
    await _login(client, account.address, account.key)

    resp = await client.get("/api/v1/auth/session")
    assert resp.status_code == 200
    assert resp.json()["user"]["wallet_address"] == account.address.lower()


async def test_logout_clears_session(client):
    account = Account.create()
    await _login(client, account.address, account.key)

    logout_resp = await client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 204

    resp = await client.get("/api/v1/auth/session")
    assert resp.status_code == 401


async def test_wrong_signer_is_rejected(client):
    claimed = Account.create()
    actual_signer = Account.create()

    nonce_resp = await client.post("/api/v1/auth/wallet/nonce", json={"address": claimed.address})
    body = nonce_resp.json()
    signature = _sign(body["message"], actual_signer.key)

    resp = await client.post(
        "/api/v1/auth/wallet/verify",
        json={"address": claimed.address, "signature": signature, "nonce": body["nonce"]},
    )
    assert resp.status_code == 401


async def test_reused_nonce_is_rejected(client):
    account = Account.create()

    nonce_resp = await client.post("/api/v1/auth/wallet/nonce", json={"address": account.address})
    body = nonce_resp.json()
    signature = _sign(body["message"], account.key)

    payload = {"address": account.address, "signature": signature, "nonce": body["nonce"]}
    first = await client.post("/api/v1/auth/wallet/verify", json=payload)
    second = await client.post("/api/v1/auth/wallet/verify", json=payload)

    assert first.status_code == 200
    assert second.status_code == 401


async def test_expired_nonce_is_rejected(client, db_session):
    account = Account.create()

    nonce_resp = await client.post("/api/v1/auth/wallet/nonce", json={"address": account.address})
    body = nonce_resp.json()

    result = await db_session.execute(select(AuthChallenge).where(AuthChallenge.nonce == body["nonce"]))
    challenge = result.scalar_one()
    challenge.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    signature = _sign(body["message"], account.key)
    resp = await client.post(
        "/api/v1/auth/wallet/verify",
        json={"address": account.address, "signature": signature, "nonce": body["nonce"]},
    )
    assert resp.status_code == 401
