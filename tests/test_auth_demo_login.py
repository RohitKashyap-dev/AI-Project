import pytest

from backend.api.routes.auth import login_for_access_token
from backend.schemas.auth import TokenRequest


class FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False

    async def scalar(self, stmt):
        return None

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        obj.id = 1


@pytest.mark.asyncio
async def test_demo_admin_login_creates_default_account():
    db = FakeSession()
    response = await login_for_access_token(TokenRequest(username="admin", password="password"), db=db)

    assert response.access_token
    assert db.committed is True
    assert db.added
