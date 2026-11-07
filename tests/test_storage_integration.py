import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
SNOWFLAKE = 1568566404381155470


def load_module(path, collection, provider="d1"):
    constants = ModuleType("constants")
    constants.MONGO_URL = None
    constants.DATABASE_PROVIDER = provider
    constants.GUILD_ID = 1315135745492521033
    storage = ModuleType("cloudflare_storage")
    database = SimpleNamespace(protected_channels=collection, channels=collection, profile=collection, emojis=collection, reaction_checks=collection, scheduled_posts=collection)
    storage.create_client = lambda mongo_url=None: SimpleNamespace(ignite=database, oasis=database, auto_reaction=database, allure=database)
    caches = ModuleType("caches")
    caches.emojis_cache = {}
    name = "storage_module_under_test"
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"constants": constants, "constant": constants, "cloudflare_storage": storage, "caches": caches, name: module}):
        spec.loader.exec_module(module)
    return module


class Cursor:
    def __init__(self, rows):
        self.rows = rows
    def __aiter__(self):
        async def rows():
            for row in self.rows:
                yield row
        return rows()
    async def to_list(self, length=None):
        return self.rows if length is None else self.rows[:length]


class ReactionStorageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.collection = SimpleNamespace(update_one=AsyncMock(), delete_one=AsyncMock(), create_index=AsyncMock(), insert_one=AsyncMock())
        self.module = load_module("utils/database.py", self.collection)

    async def test_cache_preserves_large_integer_key(self):
        self.collection.find = lambda: Cursor([{"channel_id": SNOWFLAKE, "emojis": ["✅"]}])
        await self.module.cache_emojis()
        self.assertEqual(self.module.get_emojis(SNOWFLAKE), ["✅"])
        self.assertIsNone(self.module.get_emojis(str(SNOWFLAKE)))

    async def test_failed_write_leaves_existing_cache_unchanged(self):
        self.module.emojis_cache[SNOWFLAKE] = ["✅"]
        self.collection.update_one.side_effect = RuntimeError("service unavailable")
        with self.assertRaises(RuntimeError):
            await self.module.upsert_emojis(SNOWFLAKE, ["🎉"])
        self.assertEqual(self.module.get_emojis(SNOWFLAKE), ["✅"])

    async def test_successful_delete_removes_cache_only_after_persisted_delete(self):
        self.module.emojis_cache[SNOWFLAKE] = ["✅"]
        self.collection.delete_one.return_value = SimpleNamespace(deleted_count=0)
        await self.module.delete_emojis(SNOWFLAKE)
        self.assertEqual(self.module.get_emojis(SNOWFLAKE), ["✅"])
        self.collection.delete_one.return_value = SimpleNamespace(deleted_count=1)
        await self.module.delete_emojis(SNOWFLAKE)
        self.assertIsNone(self.module.get_emojis(SNOWFLAKE))

    async def test_d1_does_not_try_to_create_mongodb_indexes(self):
        await self.module.ensure_reaction_check_indexes()
        self.collection.create_index.assert_not_awaited()

    async def test_mongodb_mode_retains_startup_indexes(self):
        module = load_module("utils/database.py", self.collection, provider="mongodb")
        await module.ensure_reaction_check_indexes()
        self.assertEqual(self.collection.create_index.await_count, 2)
