"""
==============================================================================
Тестовый комплекс: Telegram_Commerce_MiniApp Test Suite
==============================================================================
Автор: V1PER (viper86rus-arch)
GitHub: https://github.com/viper86rus-arch/Telegram_Commerce_MiniApp
Лицензия: MIT License (2026)
Назначение: Автоматизированное регрессионное и нагрузочное тестирование
           базы данных, REST API и статических ассетов магазина.
==============================================================================
"""

import os
import sys
import json
import unittest
import urllib.request
import urllib.error
from urllib.parse import urlencode

# Добавление пути проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import threading
from http.server import ThreadingHTTPServer

import database
import server


class TestDatabaseEngine(unittest.TestCase):
    """Тестирование реляционного ядра SQLite и бизнес-логики заказов."""

    def setUp(self):
        self.test_db = os.path.join(PROJECT_ROOT, "data", "test_store.db")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        database.init_db(self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_catalog_seeding(self):
        """Проверка автоматической инициализации каталога товаров и категорий."""
        cats = database.get_categories(self.test_db)
        self.assertGreaterEqual(len(cats), 5, "Категорий должно быть не менее 5")
        
        prods = database.get_products(db_path=self.test_db)
        self.assertGreaterEqual(len(prods), 6, "Товаров в демо-каталоге должно быть не менее 6")

    def test_product_filtering_and_search(self):
        """Проверка фильтрации по категории и защищенного поиска."""
        hw_prods = database.get_products(category_id="hardware", db_path=self.test_db)
        self.assertTrue(all(p["category_id"] == "hardware" for p in hw_prods))

        search_res = database.get_products(search="CyberNode", db_path=self.test_db)
        self.assertGreaterEqual(len(search_res), 1)
        self.assertIn("CyberNode", search_res[0]["name"])

    def test_sql_injection_resilience(self):
        """Тест устойчивости к попыткам SQL Injection в строке поиска."""
        malicious_search = "' OR '1'='1' --"
        res = database.get_products(search=malicious_search, db_path=self.test_db)
        # При параметризованном запросе вернется пустой список, а не все товары
        self.assertEqual(len(res), 0)

    def test_create_order_success(self):
        """Тест успешного создания заказа и калькуляции сумм."""
        order = database.create_order(
            customer_name="Тестовый Заказчик",
            phone="+7 999 111-22-33",
            address="г. Москва",
            payment_method="Telegram Stars",
            items=[{"id": "p-101", "quantity": 1}, {"id": "p-102", "quantity": 2}],
            db_path=self.test_db
        )
        self.assertTrue(order["order_id"].startswith("ORD-2026-"))
        self.assertEqual(len(order["items"]), 2)
        expected_total = 48900 * 1 + 7400 * 2
        self.assertEqual(order["total_amount"], expected_total)

    def test_create_order_empty_rejected(self):
        """Проверка отказа при попытке оформить пустой заказ."""
        with self.assertRaises(ValueError):
            database.create_order("Тест", "+7 000", "Адрес", "Stars", items=[], db_path=self.test_db)

    def test_create_order_invalid_quantity(self):
        """Проверка безопасной фильтрации невалидных или отрицательных количеств."""
        with self.assertRaises(ValueError):
            database.create_order(
                "Тест", "+7 000", "Адрес", "Stars",
                items=[{"id": "p-101", "quantity": -5}, {"id": "p-102", "quantity": 0}],
                db_path=self.test_db
            )

    def test_csv_export_and_formula_injection_sanitization(self):
        """Тест безопасного экспорта в CSV с нейтрализацией Formula Injection (CWE-1236)."""
        database.create_order(
            customer_name="=cmd|'/C calc'!A0",
            phone="+7 999 123-45-67",
            address="@SUM(1+1)",
            payment_method="-DDE",
            items=[{"id": "p-101", "quantity": 1}],
            db_path=self.test_db
        )
        csv_path = os.path.join(PROJECT_ROOT, "tests", "test_orders_export.csv")
        try:
            database.export_orders_to_csv(filepath=csv_path, db_path=self.test_db)
            self.assertTrue(os.path.exists(csv_path))
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
            self.assertIn("'=cmd|'/C calc'!A0", content)
            self.assertIn("'@SUM(1+1)", content)
            self.assertIn("'-DDE", content)
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)


class TestAPIAndStaticAssets(unittest.TestCase):
    """Тестирование REST API эндпоинтов и целостности статических ассетов."""

    @classmethod
    def setUpClass(cls):
        """Запуск изолированного тестового HTTP-сервера на динамическом порту."""
        database.init_db()
        database.seed_demo_catalog()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), server.MiniAppRequestHandler)
        cls.port = cls.server.server_port
        cls.BASE_URL = f"http://127.0.0.1:{cls.port}"
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        """Остановка и корректное освобождение сокета тестового сервера."""
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path):
        req = urllib.request.Request(f"{self.BASE_URL}{path}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8"), resp.headers

    def test_health_check_endpoint(self):
        """Проверка эндпоинта /api/health."""
        status, body, headers = self._get("/api/health")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["author"], "V1PER (viper86rus-arch)")

    def test_categories_endpoint(self):
        """Проверка эндпоинта /api/categories."""
        status, body, _ = self._get("/api/categories")
        self.assertEqual(status, 200)
        cats = json.loads(body)
        self.assertIsInstance(cats, list)
        self.assertGreaterEqual(len(cats), 4)

    def test_products_endpoint(self):
        """Проверка эндпоинта /api/products с фильтрацией."""
        status, body, _ = self._get("/api/products?category=hardware")
        self.assertEqual(status, 200)
        prods = json.loads(body)
        self.assertIsInstance(prods, list)
        self.assertTrue(all(p["category_id"] == "hardware" for p in prods))

    def test_single_product_endpoint(self):
        """Проверка эндпоинта отдельного товара /api/products/<id>."""
        status, body, _ = self._get("/api/products/p-101")
        self.assertEqual(status, 200)
        prod = json.loads(body)
        self.assertEqual(prod["id"], "p-101")
        self.assertIn("CyberNode", prod["name"])

    def test_post_order_endpoint(self):
        """Проверка REST эндпоинта создания заказа POST /api/order."""
        payload = {
            "customer_name": "API Тестер",
            "phone": "+7 (999) 555-55-55",
            "address": "Тестовый адрес",
            "payment_method": "СБП / Карта",
            "items": [{"id": "p-103", "quantity": 1}]
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.BASE_URL}/api/order",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 201)
            res = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(res["status"], "success")
            self.assertTrue(res["order_id"].startswith("ORD-2026-"))
            self.assertEqual(res["total_amount"], 12900)

    def test_all_svg_illustrations_exist_and_served(self):
        """Проверка доступности всех 6 локальных SVG иллюстраций с правильным MIME."""
        svg_files = [
            "p101_server.svg", "p102_key.svg", "p103_keyboard.svg",
            "p104_dock.svg", "p105_headphones.svg", "p106_cloud.svg"
        ]
        for svg in svg_files:
            status, _, headers = self._get(f"/img/{svg}")
            self.assertEqual(status, 200, f"SVG {svg} должен отдавать 200")
            content_type = headers.get("Content-Type", "")
            self.assertIn("image/svg+xml", content_type, f"{svg} должен иметь MIME image/svg+xml")

    def test_local_telegram_sdk_bundled(self):
        """Проверка, что Telegram WebApp SDK отдается локально без сетевых задержек."""
        status, _, headers = self._get("/js/telegram-web-app.js")
        self.assertEqual(status, 200)
        self.assertIn("javascript", headers.get("Content-Type", "").lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
