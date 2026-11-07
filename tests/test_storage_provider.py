"""Provider selection and wire format tests; no network or Discord access."""
import datetime as dt
import importlib.util
import os
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    "storage_adapter_under_test", Path(__file__).resolve().parents[1] / "cloudflare_storage.py")
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)


class ProviderTests(unittest.TestCase):
    def test_existing_service_defaults_to_motor(self):
        motor = ModuleType("motor")
        motor.motor_asyncio = ModuleType("motor.motor_asyncio")
        factory = motor.motor_asyncio.AsyncIOMotorClient = Mock()
        with patch.dict(os.environ, {}, clear=True), patch.dict(sys.modules, {
            "motor": motor, "motor.motor_asyncio": motor.motor_asyncio,
        }):
            result = storage.create_client("mongodb://localhost/test")
        factory.assert_called_once_with("mongodb://localhost/test")
        self.assertIs(result, factory.return_value)

    def test_d1_configuration_never_silently_falls_back(self):
        for config in ({}, {"DATA_SERVICE_URL": "https://storage.example.test"},
                       {"DATA_SERVICE_TOKEN": "test-only-" * 4}):
            with self.subTest(config=tuple(config)), patch.dict(os.environ, {
                "DATABASE_PROVIDER": "d1", **config,
            }, clear=True):
                with self.assertRaises(ValueError):
                    storage.create_client("mongodb://localhost/test")

    def test_explicit_d1_works_without_mongodb_url(self):
        with patch.dict(os.environ, {
            "DATABASE_PROVIDER": "d1",
            "DATA_SERVICE_URL": "https://storage.example.test",
            "DATA_SERVICE_TOKEN": "test-only-" * 4,
        }, clear=True):
            client = storage.create_client()
        self.assertIsInstance(client, storage.D1Client)

    def test_unknown_provider_is_rejected(self):
        with patch.dict(os.environ, {"DATABASE_PROVIDER": "misspelled"}, clear=True):
            with self.assertRaises(ValueError):
                storage.create_client()

    def test_discord_ids_object_ids_and_datetimes_round_trip(self):
        now = dt.datetime(2026, 11, 7, 12, 34, 56, 123000, tzinfo=dt.timezone.utc)
        record = {
            "_id": storage.ObjectId("0123456789abcdef01234567"),
            "channel_id": 1568566404381155470,
            "string_id": "1568566404381155470",
            "checked_at": now,
            "enabled": True,
            "score": 2.5,
        }
        encoded = storage.encode(record)
        self.assertEqual(encoded["channel_id"], {"$numberLong": "1568566404381155470"})
        self.assertEqual(encoded["string_id"], "1568566404381155470")
        self.assertEqual(encoded["score"], {"$numberDouble": "2.5"})
        self.assertEqual(storage.decode(encoded), record)
