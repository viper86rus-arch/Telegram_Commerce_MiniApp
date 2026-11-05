"""
==============================================================================
Модуль базы данных: Telegram_Commerce_MiniApp (SQLite Engine)
==============================================================================
Автор: V1PER (viper86rus-arch)
GitHub: https://github.com/viper86rus-arch/Telegram_Commerce_MiniApp
Лицензия: MIT License (2026)
Назначение: Автономное хранилище каталога товаров, категорий и транзакций
           заказов в реляционной базе данных SQLite (Zero-Pip / Standard Library).
==============================================================================
"""

import sqlite3
import os
import json
import logging
import uuid
from typing import List, Dict, Any, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("StoreDB")

# Путь к базе данных по умолчанию
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "store.db")


# ==============================================================================
# 1. ИНИЦИАЛИЗАЦИЯ СХЕМЫ ДАННЫХ
# ==============================================================================

def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Создает соединение с SQLite и активирует режим строк-словарей."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Инициализирует таблицы каталога, заказов и позиций корзины."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Таблица категорий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                icon TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            );
        """)

        # Таблица товаров
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                category_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price INTEGER NOT NULL,
                old_price INTEGER DEFAULT NULL,
                badge TEXT DEFAULT NULL,
                image_url TEXT NOT NULL,
                in_stock INTEGER DEFAULT 1,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
            );
        """)

        # Таблица заказов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                total_amount INTEGER NOT NULL,
                status TEXT DEFAULT 'NEW',
                notes TEXT DEFAULT ''
            );
        """)

        # Таблица позиций заказа
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                unit_price INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                subtotal INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE
            );
        """)

        conn.commit()
    logger.info("Схема базы данных SQLite успешно проверена/инициализирована.")
    seed_demo_catalog(db_path)


# ==============================================================================
# 2. ПЕРВИЧНОЕ НАПОЛНЕНИЕ ДЕМО-КАТАЛОГА (SEED)
# ==============================================================================

def seed_demo_catalog(db_path: str = DEFAULT_DB_PATH) -> None:
    """Заполняет витрину эталонными товарами, если база данных пуста."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM categories;")
        if cursor.fetchone()["count"] > 0:
            return  # База уже содержит данные

        logger.info("Заполнение демо-каталога технологическими товарами...")

        categories = [
            ("all", "Все товары", "⚡", 0),
            ("hardware", "Железо и серверы", "🖥️", 1),
            ("gadgets", "Гаджеты и девайсы", "📱", 2),
            ("accessories", "Аксессуары", "🎧", 3),
            ("software", "Лицензии и ключи", "🔑", 4),
        ]
        cursor.executemany(
            "INSERT INTO categories (id, name, icon, sort_order) VALUES (?, ?, ?, ?);",
            categories
        )

        products = [
            (
                "p-101", "hardware", "Мини-сервер CyberNode X1",
                "Компактный бесшумный микросервер для домашних и офисных задач. 8 ядер, 32GB RAM, 1TB NVMe, пассивное охлаждение.",
                48900, 56000, "Хит продаж",
                "img/p101_server.svg"
            ),
            (
                "p-102", "hardware", "Аппаратный крипто-ключ V1-Shield",
                "Защищенный токен аутентификации FIDO2/WebAuthn с биометрическим сканером и поддержкой 63-ФЗ ЭЦП.",
                7400, 8900, "Безопасность",
                "img/p102_key.svg"
            ),
            (
                "p-103", "gadgets", "Механическая клавиатура Stealth 75",
                "Премиальная кастомная клавиатура с тактильными тихими свитчами, RGB-подсветкой и алюминиевым корпусом.",
                12900, 15500, "Новинка",
                "img/p103_keyboard.svg"
            ),
            (
                "p-104", "accessories", "Магнитная док-станция Matrix 3-in-1",
                "Беспроводная зарядная станция 25W для смартфона, смарт-часов и наушников. Премиальный черный матовый металл.",
                5900, 7200, "-18%",
                "img/p104_dock.svg"
            ),
            (
                "p-105", "accessories", "Студийные наушники Obsidian Studio",
                "Закрытые мониторные наушники с активным гибридным шумоподавлением (ANC) и детальным студийным звуком.",
                18500, 22000, "Premium",
                "img/p105_headphones.svg"
            ),
            (
                "p-106", "software", "Подписка Cloud Backup Pro (1 Год)",
                "Автоматическое зашифрованное резервное копирование серверов и баз данных объемом 2TB с защитой от Ransomware.",
                3900, None, "Сервис",
                "img/p106_cloud.svg"
            ),
        ]
        cursor.executemany(
            """INSERT INTO products (
                id, category_id, name, description, price, old_price, badge, image_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
            products
        )
        conn.commit()
    logger.info("Демо-каталог успешно сформирован (6 товаров, 5 категорий).")


# ==============================================================================
# 3. МЕТОДЫ ЧТЕНИЯ КАТАЛОГА (READ API)
# ==============================================================================

def get_categories(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Возвращает список всех категорий каталога."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, icon, sort_order FROM categories ORDER BY sort_order ASC;")
        return [dict(row) for row in cursor.fetchall()]


def get_products(category_id: Optional[str] = None, search: Optional[str] = None, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Возвращает список товаров с опциональной фильтрацией по категории и поисковому запросу."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM products WHERE in_stock = 1"
        params: List[Any] = []

        if category_id and category_id != "all":
            query += " AND category_id = ?"
            params.append(category_id)

        if search and search.strip():
            query += " AND (name LIKE ? OR description LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        query += " ORDER BY id ASC;"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_product(product_id: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Получает детальную информацию об одном товаре."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?;", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# ==============================================================================
# 4. ТРАНЗАКЦИОННОЕ СОЗДАНИЕ ЗАКАЗА (ORDER MUTATION)
# ==============================================================================

def create_order(
    customer_name: str,
    phone: str,
    address: str,
    payment_method: str,
    items: List[Dict[str, Any]],
    notes: str = "",
    db_path: str = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    """Транзакционно оформляет заказ, рассчитывает итоговые суммы и фиксирует позиции."""
    if not items:
        raise ValueError("Невозможно оформить пустой заказ.")

    # Генерация красивого номера заказа: ORD-2026-XXXX
    order_suffix = uuid.uuid4().hex[:6].upper()
    order_id = f"ORD-2026-{order_suffix}"

    total_amount = 0
    calculated_items = []

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Валидация позиций по актуальным ценам из БД
        for item in items:
            product_id = item.get("id")
            try:
                quantity = int(item.get("quantity", 1))
            except (ValueError, TypeError):
                continue

            if quantity <= 0:
                continue

            cursor.execute("SELECT id, name, price FROM products WHERE id = ?;", (product_id,))
            prod = cursor.fetchone()
            if not prod:
                continue

            unit_price = prod["price"]
            subtotal = unit_price * quantity
            total_amount += subtotal

            calculated_items.append({
                "product_id": prod["id"],
                "product_name": prod["name"],
                "unit_price": unit_price,
                "quantity": quantity,
                "subtotal": subtotal
            })

        if not calculated_items:
            raise ValueError("Ни один из выбранных товаров не найден в базе данных.")

        # Вставка записи заказа
        cursor.execute("""
            INSERT INTO orders (
                order_id, customer_name, phone, address, payment_method, total_amount, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, 'NEW', ?);
        """, (order_id, customer_name, phone, address, payment_method, total_amount, notes))

        # Вставка элементов заказа
        for item in calculated_items:
            cursor.execute("""
                INSERT INTO order_items (
                    order_id, product_id, product_name, unit_price, quantity, subtotal
                ) VALUES (?, ?, ?, ?, ?, ?);
            """, (
                order_id, item["product_id"], item["product_name"],
                item["unit_price"], item["quantity"], item["subtotal"]
            ))

        conn.commit()

    logger.info(f"Заказ {order_id} успешно оформлен на сумму {total_amount} руб. Клиент: {customer_name}")
    return {
        "order_id": order_id,
        "total_amount": total_amount,
        "customer_name": customer_name,
        "phone": phone,
        "address": address,
        "payment_method": payment_method,
        "items": calculated_items
    }
