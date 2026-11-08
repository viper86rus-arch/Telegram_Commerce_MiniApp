"""
==============================================================================
Серверный модуль: Telegram_Commerce_MiniApp (Zero-Pip Server & Bot Engine)
==============================================================================
Автор: V1PER (viper86rus-arch)
GitHub: https://github.com/viper86rus-arch/Telegram_Commerce_MiniApp
Лицензия: MIT License (2026)
Назначение: Автономный сервер интернет-магазина, REST API для каталога и заказов,
           а также Telegram-бот (Long Polling) на стандартной библиотеке Python.
==============================================================================
"""

import os
import sys
import json
import logging
import signal
import threading
import argparse
import html
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request
import urllib.error

# Импорт локального модуля базы данных
import database

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("MiniAppServer")

# Директория статики фронтенда
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


# ==============================================================================
# 1. ОБРАБОТЧИК HTTP И REST API (REQUEST HANDLER)
# ==============================================================================

class MiniAppRequestHandler(SimpleHTTPRequestHandler):
    """
    Высокопроизводительный обработчик запросов:
    1. Раздает статические файлы Mini App (HTML5, CSS3, JS).
    2. Обрабатывает REST API эндпоинты (/api/categories, /api/products, /api/order).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        """Информативное форматирование системных логов HTTP-сервера."""
        logger.info(f"{self.client_address[0]} - {args[0]} - {args[1]}")

    def _send_json(self, data: any, status: int = 200) -> None:
        """Вспомогательный метод сериализации и отправки JSON-ответа."""
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def list_directory(self, path):
        """Запрет листинга каталогов для предотвращения раскрытия структуры файлов (CWE-548)."""
        self.send_error(HTTPStatus.FORBIDDEN, "Directory listing is forbidden")
        return None

    def end_headers(self):
        """Добавление критически важных заголовков безопасности."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self' 'unsafe-inline' https://telegram.org https://*.telegram.org; img-src 'self' data: https:; frame-ancestors https://web.telegram.org https://*.telegram.org;"
        )
        super().end_headers()

    def do_OPTIONS(self):
        """Поддержка CORS preflight запросов для гибкой интеграции."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Маршрутизация GET-запросов (REST API и статика)."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Health Check
        if path == "/api/health":
            self._send_json({
                "status": "healthy",
                "service": "Telegram_Commerce_MiniApp",
                "version": "1.0.0",
                "author": "V1PER (viper86rus-arch)"
            })
            return

        # Категории товаров
        if path == "/api/categories":
            cats = database.get_categories()
            self._send_json(cats)
            return

        # Список товаров (с фильтрацией)
        if path == "/api/products":
            query_params = parse_qs(parsed.query)
            category_id = query_params.get("category", [None])[0]
            search = query_params.get("search", [None])[0]
            products = database.get_products(category_id=category_id, search=search)
            self._send_json(products)
            return

        # Получение отдельного товара по ID
        if path.startswith("/api/products/"):
            product_id = path.replace("/api/products/", "").strip()
            product = database.get_product(product_id)
            if product:
                self._send_json(product)
            else:
                self._send_json({"error": "Товар не найден"}, status=404)
            return

        # Раздача статических файлов веб-приложения
        super().do_GET()

    def do_POST(self):
        """Маршрутизация POST-запросов (Оформление заказов) с защитой от DoS и валидацией."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/order":
            MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # Лимит 1 МБ (CWE-770)
            content_len_hdr = self.headers.get("Content-Length", "")
            if not content_len_hdr or not content_len_hdr.isdigit():
                self._send_json({"status": "error", "message": "Некорректный или отсутствующий заголовок Content-Length."}, status=HTTPStatus.BAD_REQUEST)
                return

            content_len = int(content_len_hdr)
            if content_len <= 0:
                self._send_json({"status": "error", "message": "Content-Length должен быть положительным числом."}, status=HTTPStatus.BAD_REQUEST)
                return

            if content_len > MAX_CONTENT_LENGTH:
                self._send_json({"status": "error", "message": "Превышен максимальный размер тела запроса (1 МБ)."}, status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return

            try:
                raw_body = self.rfile.read(content_len).decode("utf-8")
                order_data = json.loads(raw_body)

                # Создание записи в БД
                order_result = database.create_order(
                    customer_name=order_data.get("customer_name", "Клиент Telegram"),
                    phone=order_data.get("phone", "Не указан"),
                    address=order_data.get("address", "Самовывоз"),
                    payment_method=order_data.get("payment_method", "Telegram Stars"),
                    items=order_data.get("items", []),
                    notes=order_data.get("notes", "")
                )

                # Отправка уведомления администратору в Telegram (если настроен бот)
                server = getattr(self, "server", None)
                bot_controller = getattr(server, "bot_controller", None) if server else None
                if bot_controller:
                    bot_controller.notify_order_created(order_result)

                self._send_json({
                    "status": "success",
                    "order_id": order_result["order_id"],
                    "total_amount": order_result["total_amount"],
                    "message": "Заказ успешно принят в обработку."
                }, status=201)

            except json.JSONDecodeError:
                self._send_json({"status": "error", "message": "Невалидный формат JSON"}, status=HTTPStatus.BAD_REQUEST)
            except ValueError as e:
                self._send_json({"status": "error", "message": str(e)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as e:
                logger.error(f"Ошибка при оформлении заказа: {e}", exc_info=True)
                self._send_json({"status": "error", "message": "Внутренняя ошибка сервера"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Эндпоинт не найден")


# ==============================================================================
# 2. АВТОНОМНЫЙ TELEGRAM BOT КОНТРОЛЛЕР (LONG POLLING / ZERO-PIP)
# ==============================================================================

class TelegramBotController:
    """
    Встроенный Telegram-бот на чистом Python:
    - Не требует внешних библиотек (aiogram, telebot).
    - Обрабатывает команду /start с выдачей кнопки запуска Mini App.
    - Обрабатывает событие web_app_data и отправляет чеки покупателям.
    - Оповещает администратора о новых заказах.
    """

    def __init__(self, token: str, webapp_url: str, admin_chat_id: str = ""):
        self.token = token.strip()
        self.webapp_url = webapp_url.strip()
        self.admin_chat_id = admin_chat_id.strip()
        self.api_base = f"https://api.telegram.org/bot{self.token}"
        self.running = False
        self.thread = None

    def _api_request(self, method: str, data: dict) -> dict:
        """Выполняет сетевой запрос к Telegram Bot API через urllib."""
        url = f"{self.api_base}/{method}"
        req_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url, data=req_data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Telegram Bot API ошибка ({method}): {e}")
            return {"ok": False, "error": str(e)}

    def send_message(self, chat_id: any, text: str, reply_markup: dict = None) -> None:
        """Отправляет текстовое сообщение пользователю."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        self._api_request("sendMessage", payload)

    def notify_order_created(self, order: dict) -> None:
        """Отправляет уведомление администратору о поступлении нового заказа с экранированием HTML."""
        if not self.admin_chat_id:
            return

        order_id = html.escape(str(order.get("order_id", "")))
        customer_name = html.escape(str(order.get("customer_name", "")))
        phone = html.escape(str(order.get("phone", "")))
        address = html.escape(str(order.get("address", "")))
        payment_method = html.escape(str(order.get("payment_method", "")))
        total_amount = order.get("total_amount", 0)

        lines = [
            "🛍️ <b>НОВЫЙ ЗАКАЗ ИЗ TELEGRAM MINI APP!</b>\n",
            f"<b>Номер:</b> <code>{order_id}</code>",
            f"<b>Клиент:</b> {customer_name}",
            f"<b>Телефон:</b> {phone}",
            f"<b>Адрес:</b> {address}",
            f"<b>Оплата:</b> {payment_method}",
            f"<b>Сумма:</b> <b>{total_amount:,} ₽</b>".replace(",", " "),
            "\n<b>Состав заказа:</b>"
        ]
        for idx, itm in enumerate(order.get("items", []), 1):
            p_name = html.escape(str(itm.get("product_name", "")))
            qty = itm.get("quantity", 0)
            u_price = itm.get("unit_price", 0)
            lines.append(f"{idx}. {p_name} — {qty} шт. × {u_price:,} ₽".replace(",", " "))

        text = "\n".join(lines)
        self.send_message(self.admin_chat_id, text)

    def start_polling(self) -> None:
        """Запускает опрос обновлений (Long Polling) в фоновом потоке."""
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info("Telegram Bot Long-Polling поток успешно запущен.")

    def stop(self) -> None:
        """Останавливает цикл опроса."""
        self.running = False

    def _poll_loop(self) -> None:
        """Внутренний цикл опроса новых событий Telegram."""
        offset = 0
        while self.running:
            try:
                res = self._api_request("getUpdates", {"offset": offset, "timeout": 20})
                if not res.get("ok"):
                    continue

                for update in res.get("result", []):
                    offset = update["update_id"] + 1
                    self._handle_update(update)
            except Exception as e:
                logger.error(f"Сбой в цикле Long-Polling: {e}")

    def _handle_update(self, update: dict) -> None:
        """Маршрутизация событий Telegram."""
        msg = update.get("message")
        if not msg:
            return

        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        # Обработка команды /start
        if text.startswith("/start"):
            first_name = html.escape(msg["from"].get("first_name", "пользователь"))
            welcome_text = (
                f"Здравствуйте, <b>{first_name}</b>!\n\n"
                f"Добро пожаловать в <b>V1-Store</b> — демонстрационный магазин "
                f"на базе Telegram Mini App (TMA).\n\n"
                f"Нажмите кнопку ниже, чтобы открыть интерактивную витрину прямо в Telegram!"
            )
            # Инлайн-кнопка для открытия WebApp
            keyboard = {
                "inline_keyboard": [[
                    {
                        "text": "🛍️ Открыть V1-Store (Mini App)",
                        "web_app": {"url": self.webapp_url or "https://telegram.org"}
                    }
                ]]
            }
            self.send_message(chat_id, welcome_text, reply_markup=keyboard)

        # Обработка данных, отправленных из WebApp через tg.sendData
        elif "web_app_data" in msg:
            try:
                data = json.loads(msg["web_app_data"]["data"])
                order_id = data.get("order_id")
                # Валидация заказа по базе данных для исключения подмены стоимости (CWE-472)
                order = database.get_order(order_id) if order_id else None
                total_amount = order["total_amount"] if order else data.get("total", 0)
                safe_order_id = html.escape(str(order_id or "—"))
                receipt = (
                    "🎉 <b>Ваш заказ успешно зарегистрирован!</b>\n\n"
                    f"<b>Номер заказа:</b> <code>{safe_order_id}</code>\n"
                    f"<b>Сумма к оплате:</b> {total_amount:,} ₽\n\n"
                    "Менеджер свяжется с вами для подтверждения доставки. "
                    "Спасибо за покупку в V1-Store!"
                ).replace(",", " ")
                self.send_message(chat_id, receipt)
            except Exception as e:
                logger.warning(f"Ошибка парсинга web_app_data: {e}")


# ==============================================================================
# 3. ТОЧКА ВХОДА И УПРАВЛЕНИЕ ЖИЗНЕННЫМ ЦИКЛОМ (MAIN ENTRY POINT)
# ==============================================================================

def parse_arguments() -> argparse.Namespace:
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Telegram_Commerce_MiniApp: Автономный сервер и бот (Zero-Pip)."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Хост для привязки (по умолчанию 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Порт веб-сервера (по умолчанию 8000)")
    parser.add_argument("--token", default=os.getenv("TELEGRAM_BOT_TOKEN", ""), help="Токен бота Telegram")
    parser.add_argument("--webapp-url", default=os.getenv("WEBAPP_URL", ""), help="Публичный HTTPS URL для Mini App")
    parser.add_argument("--admin-id", default=os.getenv("TELEGRAM_ADMIN_CHAT_ID", ""), help="Chat ID администратора")
    parser.add_argument("--demo", action="store_true", help="Автономный демо-режим в локальном браузере")
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Инициализация базы данных SQLite
    database.init_db()

    # Настройка Telegram бота (если передан токен)
    bot_controller = None
    if args.token:
        bot_controller = TelegramBotController(
            token=args.token,
            webapp_url=args.webapp_url,
            admin_chat_id=args.admin_id
        )
        bot_controller.start_polling()
        logger.info("Модуль Telegram-бота инициализирован.")
    else:
        logger.info("Режим работы: Локальный веб-сервер / Демо (Telegram токен не указан).")

    # Запуск HTTP сервера
    server_address = (args.host, args.port)
    httpd = ThreadingHTTPServer(server_address, MiniAppRequestHandler)
    httpd.bot_controller = bot_controller

    logger.info("=" * 65)
    logger.info("⚡ V1PER Telegram Commerce Mini App запущен!")
    logger.info(f"🌐 Локальный URL: http://{args.host}:{args.port}")
    if args.webapp_url:
        logger.info(f"📱 WebApp URL: {args.webapp_url}")
    logger.info("Для остановки нажмите Ctrl+C (SIGINT)")
    logger.info("=" * 65)

    # Обработка грациозного завершения по Ctrl+C (SIGINT) и SIGTERM
    def shutdown_handler(signum, frame):
        sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        logger.info(f"\nПолучен сигнал завершения работы ({sig_name}). Корректная остановка сервисов...")
        if bot_controller:
            bot_controller.stop()
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, shutdown_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        httpd.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        httpd.server_close()
        logger.info("Сервер успешно остановлен. До свидания!")
        sys.exit(130)


if __name__ == "__main__":
    main()
