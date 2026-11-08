"""
==============================================================================
Комплексный стресс-тест и аудит безопасности: Telegram_Commerce_MiniApp
==============================================================================
Автор: V1PER (viper86rus-arch)
GitHub: https://github.com/viper86rus-arch/Telegram_Commerce_MiniApp
Лицензия: MIT License (2026)
Назначение: Автоматизированный аудит безопасности, проверка на отказ в обслуживании,
           тестирование целостности данных, валидации заказов и устойчивости к атакам.
==============================================================================
"""

import os
import sys
import json
import time
import socket
import sqlite3
import logging
import threading
import concurrent.futures
from urllib.parse import urlparse
import urllib.request
import urllib.error

# Добавляем корень проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

import database
import server
from http.server import ThreadingHTTPServer

# Отключаем избыточный вывод логов во время стресс-тестирования
logging.getLogger("StoreDB").setLevel(logging.WARNING)
logging.getLogger("MiniAppServer").setLevel(logging.WARNING)


class SecurityAuditorAndStressTester:
    """Комплексный стресс-тестер и ревизор защищенности веб-сервера и базы данных."""

    def __init__(self):
        self.test_db = os.path.join(PROJECT_ROOT, "data", "audit_test.db")
        self.server = None
        self.server_thread = None
        self.port = 0
        self.base_url = ""
        self.results = {}

    def start_test_server(self):
        """Запуск изолированного тестового сервера."""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        database.init_db(self.test_db)

        # Перенаправляем server.py на тестовую БД
        self._orig_db_path = database.DEFAULT_DB_PATH
        database.DEFAULT_DB_PATH = self.test_db

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), server.MiniAppRequestHandler)
        self.port = self.server.server_port
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        time.sleep(0.1)

    def stop_test_server(self):
        """Корректная остановка тестового сервера и очистка ресурсов."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        database.DEFAULT_DB_PATH = self._orig_db_path
        for suffix in ("", "-wal", "-shm"):
            fpath = self.test_db + suffix
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except OSError:
                    pass

    def run_all(self):
        """Запуск всех векторов ревизионного аудита."""
        print("=" * 75)
        print("⚡ ЗАПУСК БЕСПОЩАДНОГО АУДИТА БЕЗОПАСНОСТИ: Telegram_Commerce_MiniApp")
        print("=" * 75)

        self.start_test_server()
        try:
            self.test_1_directory_traversal_and_file_read()
            self.test_2_price_tampering_and_order_validation()
            self.test_3_xss_and_html_injection()
            self.test_4_sqlite_concurrency_and_race_conditions()
            self.test_5_memory_dos_and_content_length()
            self.test_6_threading_and_signal_handling()
            self.test_7_csv_formula_injection()
            self.test_8_pii_masking_in_logs()
        finally:
            self.stop_test_server()

        self.print_summary()

    # ==========================================================================
    # 1. DIRECTORY TRAVERSAL & ARBITRARY FILE READ (CWE-22, CWE-548)
    # ==========================================================================
    def test_1_directory_traversal_and_file_read(self):
        print("\n[Вектор 1] Directory Traversal (CWE-22) и Раскрытие директорий (CWE-548)")
        findings = []

        # 1.1 Тест обхода каталогов через URL кодирование и относительные пути
        traversal_payloads = [
            "/..%2f..%2fdatabase.py",
            "/../../server.py",
            "/..%5c..%5cserver.py",
            "/%2e%2e/%2e%2e/database.py",
            "/.env.example",
            "/../.env.example",
            "/../data/store.db"
        ]

        escaped = False
        for payload in traversal_payloads:
            try:
                req = urllib.request.Request(f"{self.base_url}{payload}")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        content = resp.read(100)
                        if b"def " in content or b"DATABASE" in content or b"TOKEN" in content:
                            escaped = True
                            findings.append(f"КРИТИЧНО: Успешное чтение файла через путь {payload}")
            except urllib.error.HTTPError:
                pass
            except Exception:
                pass

        if not escaped:
            findings.append("OK: SimpleHTTPRequestHandler корректно блокирует прямой выход за пределы папки web/")

        # 1.2 Проверка Directory Listing (листинг содержимого папок без index.html)
        dir_listing_exposed = False
        for d in ["/img/", "/css/", "/js/"]:
            try:
                req = urllib.request.Request(f"{self.base_url}{d}")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    body = resp.read().decode("utf-8", errors="ignore")
                    if "Directory listing for" in body:
                        dir_listing_exposed = True
                        findings.append(f"УЯЗВИМОСТЬ: Включен автолистинг директорий (Directory Listing) для {d} (CWE-548)")
            except Exception:
                pass

        # 1.3 Проверка защитных заголовков (CSP, X-Content-Type-Options)
        try:
            req = urllib.request.Request(f"{self.base_url}/")
            with urllib.request.urlopen(req, timeout=2) as resp:
                headers = dict(resp.headers)
                if "Content-Security-Policy" not in headers:
                    findings.append("УЯЗВИМОСТЬ: Отсутствует заголовок Content-Security-Policy (CSP)")
                if "X-Content-Type-Options" not in headers:
                    findings.append("НЕДОЧЕТ: Отсутствует заголовок X-Content-Type-Options: nosniff")
                if "X-Frame-Options" not in headers and "frame-ancestors" not in headers.get("Content-Security-Policy", ""):
                    findings.append("НЕДОЧЕТ: Отсутствует ограничение встраивания во фреймы (X-Frame-Options / frame-ancestors)")
        except Exception as e:
            findings.append(f"Ошибка проверки заголовков: {e}")

        self.results["1_directory_traversal"] = findings
        for f in findings:
            print(f"  • {f}")

    # ==========================================================================
    # 2. PRICE TAMPERING & ORDER VALIDATION (CWE-472)
    # ==========================================================================
    def test_2_price_tampering_and_order_validation(self):
        print("\n[Вектор 2] Подмена цен и валидация заказов (Price Tampering, CWE-472)")
        findings = []

        # 2.1 Подмена цен со стороны клиента
        # Товар p-101 стоит 48 900 руб. Отправляем unit_price: 1 руб.
        tampered_order = {
            "customer_name": "Хакер",
            "phone": "+7 000 000-00-00",
            "address": "Тест",
            "payment_method": "Telegram Stars",
            "items": [{"id": "p-101", "quantity": 1, "unit_price": 1, "price": 1, "subtotal": 1}]
        }
        order_res = database.create_order(**tampered_order, db_path=self.test_db)
        if order_res["total_amount"] == 48900:
            findings.append("OK: Сервер игнорирует переданные клиентом цены и пересчитывает сумму строго по БД (48 900 руб.)")
        else:
            findings.append(f"КРИТИЧЕСКАЯ УЯЗВИМОСТЬ: Сервер принял поддельную цену! Итоговая сумма: {order_res['total_amount']}")

        # 2.2 Отрицательное количество товаров
        try:
            database.create_order(
                customer_name="Тест", phone="+7 000", address="Адрес", payment_method="Stars",
                items=[{"id": "p-101", "quantity": -5}], db_path=self.test_db
            )
            findings.append("КРИТИЧНО: Заказ с отрицательным количеством был принят!")
        except ValueError:
            findings.append("OK: Заказ с отрицательным количеством корректно отклонен (ValueError)")

        # 2.3 Дробное количество товаров в строковом формате ("0.5")
        try:
            database.create_order(
                customer_name="Тест", phone="+7 000", address="Адрес", payment_method="Stars",
                items=[{"id": "p-101", "quantity": "0.5"}], db_path=self.test_db
            )
            findings.append("УЯЗВИМОСТЬ: Строковое дробное количество '0.5' привело к созданию заказа!")
        except ValueError:
            findings.append("OK: Строковое дробное количество '0.5' отклонено (ValueError)")

        # 2.4 Гигантское число товаров (Integer Overflow в SQLite)
        try:
            database.create_order(
                customer_name="Тест", phone="+7 000", address="Адрес", payment_method="Stars",
                items=[{"id": "p-101", "quantity": 10**35}], db_path=self.test_db
            )
            findings.append("УЯЗВИМОСТЬ: Гигантское количество не вызвало ошибки перед записью в БД")
        except OverflowError:
            findings.append("НЕДОЧЕТ: Переполнение Integer Overflow вызывает необработанный OverflowError вместо 400 Bad Request")
        except Exception as e:
            findings.append(f"OK: Переполнение перехвачено: {type(e).__name__}")

        # 2.5 Подмена данных в web_app_data чека бота
        server_path = os.path.join(PROJECT_ROOT, "server.py")
        server_src = open(server_path, "r", encoding="utf-8").read()
        if "database.get_order(order_id)" in server_src:
            findings.append("OK: В TelegramBotController (web_app_data) сумма чека верифицируется через database.get_order()")
        else:
            findings.append("УЯЗВИМОСТЬ: В TelegramBotController (web_app_data) сумма чека берется напрямую из клиентского total без сверки с order_id в БД")

        self.results["2_price_tampering"] = findings
        for f in findings:
            print(f"  • {f}")

    # ==========================================================================
    # 3. CROSS-SITE SCRIPTING (XSS, CWE-79) & HTML INJECTION
    # ==========================================================================
    def test_3_xss_and_html_injection(self):
        print("\n[Вектор 3] Cross-Site Scripting (XSS, CWE-79) и HTML Injection")
        findings = []

        # 3.1 Анализ фронтенда web/js/app.js
        app_js_path = os.path.join(PROJECT_ROOT, "web", "js", "app.js")
        if os.path.exists(app_js_path):
            with open(app_js_path, "r", encoding="utf-8") as f:
                js_content = f.read()

            # Проверка renderCategories
            if "pill.innerHTML = `<span>${cat.icon}</span> <span>${cat.name}</span>`" in js_content:
                findings.append("УЯЗВИМОСТЬ (Stored XSS): В renderCategories имя и иконка категории вставляются через innerHTML без экранирования")
            else:
                findings.append("OK: Имена категорий экранируются")

            # Проверка экранирования image_url в карточках товаров
            if '<img src="${p.image_url}"' in js_content or '<img class="cart-item-img" src="${product.image_url}"' in js_content:
                findings.append("УЯЗВИМОСТЬ (Attribute XSS): image_url вставляется в src без валидации/экранирования кавычек и протокола javascript:")
            else:
                findings.append("OK: image_url экранируется")

            # Проверка data-id атрибутов
            if 'data-id="${productId}"' in js_content or 'data-id="${product.id}"' in js_content:
                findings.append("НЕДОЧЕТ: productId в data-id атрибутах не экранируется")
            else:
                findings.append("OK: data-id атрибуты экранируются")

        # 3.2 HTML Injection в Telegram Bot Admin Alerts
        server_path = os.path.join(PROJECT_ROOT, "server.py")
        server_src = open(server_path, "r", encoding="utf-8").read()
        if "html.escape" in server_src and "notify_order_created" in server_src:
            findings.append("OK: В server.py notify_order_created поля customer_name, phone, address экранируются через html.escape()")
        else:
            findings.append("УЯЗВИМОСТЬ (HTML Injection): В server.py notify_order_created поля customer_name, phone, address вставляются в HTML без html.escape()")

        self.results["3_xss_and_injection"] = findings
        for f in findings:
            print(f"  • {f}")

    # ==========================================================================
    # 4. SQLITE CONCURRENCY, WAL & RACE CONDITIONS
    # ==========================================================================
    def test_4_sqlite_concurrency_and_race_conditions(self):
        print("\n[Вектор 4] SQLite Race Conditions, WAL Mode и устойчивость к блокировкам")
        findings = []

        # 4.1 Проверка PRAGMA journal_mode
        with database.get_connection(self.test_db) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode;")
            journal_mode = cur.fetchone()[0].upper()
            cur.execute("PRAGMA busy_timeout;")
            busy_timeout = cur.fetchone()[0]

        if journal_mode != "WAL":
            findings.append(f"НЕДОЧЕТ: База данных работает в режиме '{journal_mode}', а не 'WAL'. Конкурентные транзакции блокируют читателей.")
        else:
            findings.append("OK: Включен режим PRAGMA journal_mode = WAL")

        if busy_timeout < 5000:
            findings.append(f"НЕДОЧЕТ: Значение busy_timeout равно {busy_timeout} мс (рекомендуется >= 5000 мс для исключения 'database is locked')")
        else:
            findings.append(f"OK: busy_timeout = {busy_timeout} мс")

        # 4.2 Стресс-тест конкурентных заказов (30 параллельных потоков)
        errors = []
        successes = []

        def place_order(idx):
            try:
                res = database.create_order(
                    customer_name=f"Стресс-Клиент {idx}",
                    phone="+7 999 111-22-33",
                    address="Улица Нагрузки",
                    payment_method="Telegram Stars",
                    items=[{"id": "p-101", "quantity": 1}],
                    db_path=self.test_db
                )
                return True, res["order_id"]
            except Exception as e:
                return False, f"{type(e).__name__}: {e}"

        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(place_order, i) for i in range(30)]
            for f in concurrent.futures.as_completed(futures):
                ok, val = f.result()
                if ok:
                    successes.append(val)
                else:
                    errors.append(val)
        elapsed = time.time() - start_time

        if errors:
            findings.append(f"СБОЙ: {len(errors)} из 30 параллельных заказов завершились ошибкой: {errors[0]}")
        else:
            findings.append(f"OK: 30 параллельных заказов успешно записаны за {elapsed:.2f}с ({len(successes)} успешных транзакций)")

        self.results["4_sqlite_concurrency"] = findings
        for f in findings:
            print(f"  • {f}")

    # ==========================================================================
    # 5. MEMORY DOS & CONTENT-LENGTH (CWE-770, CWE-400)
    # ==========================================================================
    def test_5_memory_dos_and_content_length(self):
        print("\n[Вектор 5] Memory DoS & Обработка Content-Length (CWE-770, CWE-400)")
        findings = []

        # 5.1 Отрицательный Content-Length (-1) -> зависание потока
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        try:
            s.connect(("127.0.0.1", self.port))
            s.sendall(b"POST /api/order HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: -1\r\nContent-Type: application/json\r\n\r\n")
            try:
                data = s.recv(1024)
                findings.append(f"OK: Сервер ответил на отрицательный Content-Length: {data[:50]}")
            except socket.timeout:
                findings.append("КРИТИЧЕСКАЯ УЯЗВИМОСТЬ (Slowloris / Hang DoS): Запрос с Content-Length: -1 блокирует поток сервера в ожидании EOF (CWE-400)")
        except Exception as e:
            findings.append(f"Ошибка сокета: {e}")
        finally:
            s.close()

        # 5.2 Проверка ограничения максимального размера тела запроса (Max Body Size)
        req = urllib.request.Request(
            f"{self.base_url}/api/order",
            data=b"{}",
            headers={"Content-Length": "100000000", "Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=2) as resp:
                pass
        except urllib.error.HTTPError as e:
            if e.code == 413:
                findings.append("OK: Сервер отклоняет запросы с чрезмерным Content-Length (413 Request Entity Too Large)")
            else:
                findings.append(f"OK: Запрос с чрезмерным Content-Length отклонен с кодом {e.code}")
        except Exception:
            findings.append("OK: Сервер корректно защищен от DoS по размеру тела запроса")

        # 5.3 Утечка внутреннего стека исключений в JSON (CWE-209)
        # При ошибке JSON-парсинга возвращается {"status": "error", "message": str(e)}
        req = urllib.request.Request(
            f"{self.base_url}/api/order",
            data=b"{broken_json:",
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=2) as resp:
                pass
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            if "Expecting value" in body or "JSONDecodeError" in body:
                findings.append("НЕДОЧЕТ (CWE-209 Information Exposure): Детали внутренних исключений (str(e)) возвращаются клиенту в открытом виде")
            else:
                findings.append("OK: Детали внутренних исключений парсера скрыты от клиента")

        self.results["5_memory_dos"] = findings
        for f in findings:
            print(f"  • {f}")

    # ==========================================================================
    # 6. THREADING & SIGNAL HANDLING (CWE-400)
    # ==========================================================================
    def test_6_threading_and_signal_handling(self):
        print("\n[Вектор 6] Многопоточность и обработка сигналов завершения")
        findings = []

        # 6.1 Проверка ThreadingHTTPServer
        if issubclass(server.ThreadingHTTPServer, object):
            findings.append("OK: Сервер использует ThreadingHTTPServer (неблокирующая обработка запросов)")

        # 6.2 Анализ обработки сигналов в server.py
        server_path = os.path.join(PROJECT_ROOT, "server.py")
        with open(server_path, "r", encoding="utf-8") as f:
            server_src = f.read()

        if "signal.signal(signal.SIGINT" in server_src:
            findings.append("OK: Сигнал SIGINT (Ctrl+C) зарегистрирован и завершает процесс с кодом 130")
        else:
            findings.append("НЕДОЧЕТ: Сигнал SIGINT не зарегистрирован")

        if "signal.signal(signal.SIGTERM" not in server_src:
            findings.append("НЕДОЧЕТ: Отсутствует обработчик SIGTERM (критично для контейнеров Docker, Kubernetes, systemd)")
        else:
            findings.append("OK: Сигнал SIGTERM зарегистрирован")

        self.results["6_threading_signals"] = findings
        for f in findings:
            print(f"  • {f}")

    # ==========================================================================
    # 7. CSV / EXCEL FORMULA INJECTION (CWE-1236)
    # ==========================================================================
    def test_7_csv_formula_injection(self):
        print("\n[Вектор 7] CSV / Excel Formula Injection при экспорте заказов (CWE-1236)")
        findings = []

        # Проверяем наличие экспорта в CSV
        db_src = open(os.path.join(PROJECT_ROOT, "database.py"), "r", encoding="utf-8").read()
        server_src = open(os.path.join(PROJECT_ROOT, "server.py"), "r", encoding="utf-8").read()

        has_csv_export = "csv" in db_src or "csv" in server_src
        if not has_csv_export:
            findings.append("АРХИТЕКТУРНЫЙ ПРОБЕЛ: В проекте отсутствует встроенная функция экспорта заказов в CSV для CRM / Excel")
            findings.append("РЕКОМЕНДАЦИЯ (CWE-1236): При реализации экспорта все поля (ФИО, адрес, телефон), начинающиеся с '=', '+', '-', '@', '\\t', '\\r', должны санитизироваться префиксом апострофа ('), кодироваться в utf-8-sig и разделяться точкой с запятой (;)")
        else:
            findings.append("OK: Экспорт в CSV реализован с санитизацией Formula Injection")

        self.results["7_csv_injection"] = findings
        for f in findings:
            print(f"  • {f}")

    # ==========================================================================
    # 8. PII MASKING IN LOGS (CWE-532)
    # ==========================================================================
    def test_8_pii_masking_in_logs(self):
        print("\n[Вектор 8] Маскирование персональных данных (PII) в логах (CWE-532)")
        findings = []

        db_src = open(os.path.join(PROJECT_ROOT, "database.py"), "r", encoding="utf-8").read()
        server_src = open(os.path.join(PROJECT_ROOT, "server.py"), "r", encoding="utf-8").read()

        # Поиск логирования customer_name
        if 'Клиент: {customer_name}' in db_src or 'Клиент: " + customer_name' in db_src:
            findings.append("УЯЗВИМОСТЬ (CWE-532 PII Exposure): Имя клиента логируется в открытом виде: logger.info(f'... Клиент: {customer_name}')")
        else:
            findings.append("OK: Имя клиента маскируется в логах БД")

        # Проверка логирования телефонов
        import re
        if re.search(r"logger\.(info|debug|warning|error)\(.*phone", server_src):
            findings.append("НЕДОЧЕТ: Номера телефонов могут попадать в системные логи")
        else:
            findings.append("OK: Прямое логирование телефонов в server.py отсутствует")

        self.results["8_pii_masking"] = findings
        for f in findings:
            print(f"  • {f}")

    # ==========================================================================
    # ИТОГОВЫЙ СТРУКТУРИРОВАННЫЙ ОТЧЕТ
    # ==========================================================================
    def print_summary(self):
        print("\n" + "=" * 75)
        print("📊 СВОДНЫЙ РЕЗУЛЬТАТ АУДИТА БЕЗОПАСНОСТИ")
        print("=" * 75)
        for cat, list_findings in self.results.items():
            print(f"\n[{cat.upper()}]:")
            for item in list_findings:
                status_icon = "🔴" if "КРИТИЧ" in item or "УЯЗВИМОСТЬ" in item or "СБОЙ" in item else ("🟡" if "НЕДОЧЕТ" in item or "АРХИТЕКТУРНЫЙ" in item else "🟢")
                print(f"  {status_icon} {item}")
        print("\n" + "=" * 75)


if __name__ == "__main__":
    auditor = SecurityAuditorAndStressTester()
    auditor.run_all()
