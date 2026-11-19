"""Async MongoDB-shaped test double; tests never create a relational database."""

from __future__ import annotations

import copy
import re
import uuid
from types import SimpleNamespace
from typing import Any, AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core import create_access_token, hash_password
from app.core.mongo import model_to_doc
from app.database import get_db
from app.main import app
from app.models.department import ComplaintCategory, Department
from app.models.user import User


def _value(doc: dict[str, Any], key: str) -> Any:
    return doc.get(key)


def _matches(doc: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(doc, branch) for branch in expected):
                return False
            continue
        actual = _value(doc, key)
        if isinstance(expected, dict):
            for operator, operand in expected.items():
                if operator == "$options":
                    continue
                if operator == "$in" and not (actual in operand or (isinstance(actual, list) and any(item in operand for item in actual))):
                    return False
                if operator == "$nin" and (actual in operand or (isinstance(actual, list) and any(item in operand for item in actual))):
                    return False
                if operator == "$ne" and actual == operand:
                    return False
                if operator == "$gte" and (actual is None or actual < operand):
                    return False
                if operator == "$gt" and (actual is None or actual <= operand):
                    return False
                if operator == "$lte" and (actual is None or actual > operand):
                    return False
                if operator == "$lt" and (actual is None or actual >= operand):
                    return False
                if operator == "$regex":
                    flags = re.I if expected.get("$options") == "i" else 0
                    if actual is None or re.search(operand, str(actual), flags) is None:
                        return False
            continue
        if isinstance(actual, list) and expected in actual:
            continue
        if actual != expected:
            return False
    return True


class MemoryCursor:
    def __init__(self, documents: list[dict[str, Any]]):
        self.documents = documents

    def sort(self, key: str | list[tuple[str, int]], direction: int = 1):
        fields = [(key, direction)] if isinstance(key, str) else key
        for field, order in reversed(fields):
            self.documents.sort(key=lambda item: item.get(field) or 0, reverse=order < 0)
        return self

    def skip(self, count: int):
        self.documents = self.documents[count:]
        return self

    def limit(self, count: int):
        self.documents = self.documents[:count]
        return self

    async def to_list(self, length: int | None = None):
        return copy.deepcopy(self.documents if length is None else self.documents[:length])


class MemoryCollection:
    def __init__(self):
        self.documents: list[dict[str, Any]] = []

    async def insert_one(self, document: dict[str, Any]):
        item = copy.deepcopy(document)
        item.setdefault("_id", str(uuid.uuid4()))
        self.documents.append(item)
        return SimpleNamespace(inserted_id=item["_id"])

    async def find_one(self, query: dict[str, Any], projection: dict[str, int] | None = None, sort: list[tuple[str, int]] | None = None):
        docs = [doc for doc in self.documents if _matches(doc, query)]
        if sort:
            for field, order in reversed(sort):
                docs.sort(key=lambda item: item.get(field) or 0, reverse=order < 0)
        if not docs:
            return None
        item = copy.deepcopy(docs[0])
        if projection:
            included = {key for key, value in projection.items() if value}
            item = {key: value for key, value in item.items() if key in included or key == "_id"}
        return item

    def find(self, query: dict[str, Any] | None = None):
        return MemoryCursor([doc for doc in self.documents if _matches(doc, query or {})])

    async def count_documents(self, query: dict[str, Any]):
        return sum(_matches(doc, query) for doc in self.documents)

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]):
        for doc in self.documents:
            if _matches(doc, query):
                self._apply(doc, update)
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)

    async def update_many(self, query: dict[str, Any], update: dict[str, Any]):
        count = 0
        for doc in self.documents:
            if _matches(doc, query):
                self._apply(doc, update)
                count += 1
        return SimpleNamespace(modified_count=count)

    async def create_indexes(self, indexes):
        return []

    @staticmethod
    def _apply(doc: dict[str, Any], update: dict[str, Any]):
        for key, values in update.items():
            if key == "$set":
                doc.update(copy.deepcopy(values))
            elif key == "$unset":
                for field in values:
                    doc.pop(field, None)
            elif key == "$inc":
                for field, value in values.items():
                    doc[field] = doc.get(field, 0) + value
            elif key == "$addToSet":
                for field, value in values.items():
                    current = doc.setdefault(field, [])
                    if value not in current:
                        current.append(copy.deepcopy(value))


class MemoryMongo:
    def __init__(self):
        self.collections: dict[str, MemoryCollection] = {}

    def __getattr__(self, name: str) -> MemoryCollection:
        if name.startswith("_"):
            raise AttributeError(name)
        return self.collections.setdefault(name, MemoryCollection())

    async def command(self, name: str):
        return {"ok": 1}


@pytest.fixture
def db_session() -> MemoryMongo:
    return MemoryMongo()


@pytest.fixture(autouse=True)
def _force_mock_email_provider(monkeypatch: pytest.MonkeyPatch):
    """Tests must never call live Brevo/SMTP/Resend from the developer .env."""
    monkeypatch.setenv("EMAIL_PROVIDER", "mock")
    monkeypatch.setenv("SMS_PROVIDER", "mock")
    from app.config import get_settings
    from app.services import email_service as email_service_module

    get_settings.cache_clear()
    if hasattr(email_service_module.get_email_service, "cache_clear"):
        email_service_module.get_email_service.cache_clear()
    yield
    get_settings.cache_clear()
    if hasattr(email_service_module.get_email_service, "cache_clear"):
        email_service_module.get_email_service.cache_clear()


@pytest.fixture
async def client(db_session: MemoryMongo) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def demo_user(db_session: MemoryMongo) -> User:
    user = User(email="citizen@example.com", full_name="John Doe", password_hash=hash_password("Password123!"), roles=["citizen"], is_active=True, is_verified=True, identity_verified=True, identity_provider="test_provider")
    await db_session.users.insert_one(model_to_doc(user))
    return user


@pytest.fixture
def user_token(demo_user: User) -> str:
    return create_access_token(demo_user.id, ["citizen"])


@pytest.fixture
async def demo_category(db_session: MemoryMongo) -> ComplaintCategory:
    department = Department(name="Public Works", code="PWD")
    category = ComplaintCategory(name="Pothole Repair", slug="pothole", department_id=department.id, is_active=True)
    await db_session.departments.insert_one(model_to_doc(department))
    await db_session.complaint_categories.insert_one(model_to_doc(category))
    return category
