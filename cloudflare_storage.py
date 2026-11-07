"""Bounded Mongo-style CRUD adapter for the Eutopia D1 data service.

This is a deliberate subset, not a general MongoDB driver. Unsupported operations
fail explicitly. Vendor this file unchanged from Eutopia18/eutopia-data-service.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import math
import os
import re
import secrets
import time
import uuid
from types import SimpleNamespace
from urllib.parse import urlparse

import aiohttp

try:
    from bson import ObjectId
except ImportError:
    class ObjectId(str):
        """Fallback preserving the BSON object-id type tag without pymongo."""
        def __new__(cls, value=None):
            value = value or secrets.token_hex(12)
            if not re.fullmatch(r"[0-9a-fA-F]{24}", value):
                raise ValueError("invalid ObjectId")
            return super().__new__(cls, value.lower())


def encode(value):
    """Encode document values losslessly; every Python int uses $numberLong."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, ObjectId):
        return {"$oid": str(value)}
    if isinstance(value, int):
        if not -(2**63) <= value <= 2**63 - 1:
            raise ValueError("integer outside signed BSON int64 range")
        return {"$numberLong": str(value)}
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.timezone.utc)
        return {"$date": value.astimezone(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats unsupported")
        return {"$numberDouble": repr(value)}
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return [encode(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("document keys must be strings")
        return {key: encode(item) for key, item in value.items()}
    raise TypeError("unsupported document value type: " + type(value).__name__)


def decode(value):
    if isinstance(value, list):
        return [decode(item) for item in value]
    if isinstance(value, dict):
        if set(value) in ({"$numberLong"}, {"$numberInt"}):
            return int(next(iter(value.values())))
        if set(value) == {"$numberDouble"}:
            return float(value["$numberDouble"])
        if set(value) == {"$oid"}:
            return ObjectId(value["$oid"])
        if set(value) == {"$date"}:
            return dt.datetime.fromisoformat(value["$date"].replace("Z", "+00:00"))
        return {key: decode(item) for key, item in value.items()}
    return value


class StorageError(RuntimeError):
    def __init__(self, code, status=0):
        self.code, self.status = code, status
        super().__init__(f"data service error: {code} (status {status})")


def _project(document, projection):
    if document is None or not projection:
        return document
    if not isinstance(projection, dict):
        raise NotImplementedError("projection must be a dictionary")
    if any("." in key or value not in (True, False, 0, 1) for key, value in projection.items()):
        raise NotImplementedError("only top-level inclusion/exclusion projections supported")
    included = [key for key, value in projection.items() if key != "_id" and bool(value)]
    excluded = [key for key, value in projection.items() if key != "_id" and not bool(value)]
    if included and excluded:
        raise ValueError("cannot mix inclusion and exclusion projection")
    result = {} if included else dict(document)
    if included or (set(projection) == {"_id"} and projection["_id"]):
        result = {}
        for key in included:
            if "." in key:
                raise NotImplementedError("dotted projection unsupported")
            if key in document:
                result[key] = document[key]
        if projection.get("_id", True) and "_id" in document:
            result["_id"] = document["_id"]
    else:
        for key, enabled in projection.items():
            if not enabled:
                result.pop(key, None)
    return result


class D1Client:
    def __init__(self, url, token, *, timeout=15, attempts=4):
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise ValueError("DATA_SERVICE_URL must be an HTTPS origin without credentials/query")
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token):
            raise ValueError("DATA_SERVICE_TOKEN has invalid format")
        self._url, self._token = url.rstrip("/"), token
        self._timeout, self._attempts = timeout, attempts
        self._session = None

    def __getitem__(self, name):
        return D1Database(self, name)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    def get_database(self, name):
        return self[name]

    async def aclose(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def close(self):
        if self._session and not self._session.closed:
            asyncio.get_running_loop().create_task(self._session.close())

    async def _request(self, payload):
        # Serialize once: retries retain requestId, issuedAt, generated _id, and body.
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
        if len(body) > 1500000:
            raise StorageError("body_too_large", 413)
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout), trust_env=False)
        for attempt in range(self._attempts):
            try:
                async with self._session.post(self._url + "/v1/query", data=body, headers={"Authorization": "Bearer " + self._token, "Content-Type": "application/json"}) as response:
                    raw = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        raw.extend(chunk)
                        if len(raw) > 1600000:
                            raise StorageError("response_too_large", 502)
                    try:
                        result = json.loads(raw)
                    except (ValueError, UnicodeDecodeError):
                        result = None
                    if response.status == 200:
                        if not isinstance(result, dict) or "error" in result:
                            raise StorageError("invalid_response", 502)
                        return decode(result)
                    code = result.get("error", "request_failed") if isinstance(result, dict) else "invalid_response"
                    if not isinstance(code, str) or not re.fullmatch(r"[a-z_]{1,80}", code):
                        code = "request_failed"
                    error = StorageError(code, response.status)
                    if response.status not in (408, 429, 500, 502, 503, 504):
                        raise error
                    if attempt == self._attempts - 1:
                        raise error
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == self._attempts - 1:
                    raise StorageError("network_unavailable") from None
            await asyncio.sleep(min(0.25 * 2**attempt, 2))
        raise StorageError("request_failed")


class D1Database:
    def __init__(self, client, name):
        self.client, self.name = client, name

    def __getitem__(self, name):
        return D1Collection(self.client, self.name, name)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    def get_collection(self, name):
        return self[name]


class D1Collection:
    def __init__(self, client, database, name):
        self._client, self._database, self.name = client, database, name

    async def _run(self, operation, *, write=False, **kwargs):
        payload = {"database": self._database, "collection": self.name, "operation": operation, **kwargs}
        if write:
            payload.update(requestId=uuid.uuid4().hex, issuedAt=int(time.time() * 1000))
        return await self._client._request(payload)

    def find(self, filter=None, projection=None, **kwargs):
        if kwargs:
            raise NotImplementedError("unsupported find options")
        return D1Cursor(self, filter or {}, projection)

    async def find_one(self, filter=None, projection=None, **kwargs):
        if kwargs:
            raise NotImplementedError("unsupported find_one options")
        result = await self._run("find_one", filter=encode(filter or {}))
        return _project(result["document"], projection)

    async def insert_one(self, document, **kwargs):
        if kwargs:
            raise NotImplementedError("unsupported insert options")
        if "_id" not in document:
            document["_id"] = ObjectId()
        result = await self._run("insert_one", write=True, document=encode(document))
        return SimpleNamespace(acknowledged=True, **result)

    async def update_one(self, filter, update, upsert=False, **kwargs):
        if kwargs:
            raise NotImplementedError("unsupported update options")
        result = await self._run("update_one", write=True, filter=encode(filter), update=encode(update), upsert=upsert, upsertId=encode(ObjectId()))
        return SimpleNamespace(acknowledged=True, **result)

    async def replace_one(self, filter, replacement, upsert=False, **kwargs):
        if kwargs:
            raise NotImplementedError("unsupported replace options")
        result = await self._run("replace_one", write=True, filter=encode(filter), document=encode(replacement), upsert=upsert, upsertId=encode(ObjectId()))
        return SimpleNamespace(acknowledged=True, **result)

    async def delete_one(self, filter, **kwargs):
        if kwargs:
            raise NotImplementedError("unsupported delete options")
        return SimpleNamespace(acknowledged=True, **await self._run("delete_one", write=True, filter=encode(filter)))

    async def delete_many(self, filter, **kwargs):
        if kwargs:
            raise NotImplementedError("unsupported delete options")
        return SimpleNamespace(acknowledged=True, **await self._run("delete_many", write=True, filter=encode(filter)))

    async def count_documents(self, filter, **kwargs):
        if kwargs:
            raise NotImplementedError("unsupported count options")
        return (await self._run("count_documents", filter=encode(filter)))["count"]

    async def create_index(self, *args, **kwargs):
        raise NotImplementedError("D1 indexes are managed by the data-service schema migration")


class D1Cursor:
    def __init__(self, collection, filter, projection):
        self._collection, self._filter, self._projection = collection, filter, projection
        self._cursor, self._buffer, self._done, self._started = None, [], False, False
        self._limit, self._yielded = None, 0

    def __aiter__(self):
        return self

    def limit(self, count):
        if self._started:
            raise RuntimeError("cursor already started")
        if not isinstance(count, int) or count < 0:
            raise ValueError("limit must be nonnegative")
        self._limit = count or None
        return self

    async def __anext__(self):
        if self._limit is not None and self._yielded >= self._limit:
            raise StopAsyncIteration
        if not self._buffer and not self._done:
            self._started = True
            options = {"filter": encode(self._filter), "limit": min(100, self._limit - self._yielded) if self._limit else 100}
            if self._cursor:
                options["cursor"] = self._cursor
            result = await self._collection._run("find", **options)
            self._buffer = result["documents"]
            self._cursor = result["nextCursor"]
            self._done = self._cursor is None
        if not self._buffer:
            raise StopAsyncIteration
        self._yielded += 1
        return _project(self._buffer.pop(0), self._projection)

    async def to_list(self, length=None):
        if length is not None and (not isinstance(length, int) or length < 0):
            raise ValueError("length must be nonnegative or None")
        result = []
        while length is None or len(result) < length:
            try:
                result.append(await self.__anext__())
            except StopAsyncIteration:
                break
        return result


def create_client(mongo_url=None):
    """Select D1 only when explicitly configured; Mongo remains the default."""
    provider = os.getenv("DATABASE_PROVIDER", "mongodb").strip().lower()
    if provider in ("mongo", "mongodb"):
        import motor.motor_asyncio
        return motor.motor_asyncio.AsyncIOMotorClient(mongo_url or os.getenv("MONGO_URL"))
    if provider != "d1":
        raise ValueError("DATABASE_PROVIDER must be mongodb or d1")
    url, token = os.getenv("DATA_SERVICE_URL"), os.getenv("DATA_SERVICE_TOKEN")
    if not url or not token:
        raise ValueError("D1 requires DATA_SERVICE_URL and DATA_SERVICE_TOKEN")
    return D1Client(url, token)
