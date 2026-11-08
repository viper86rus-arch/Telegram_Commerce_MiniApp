# 🛍️ V1PER IT Solutions | Telegram Commerce MiniApp (TMA)

[![Live Demo](https://badgen.net/badge/Live%20Demo/Interactive%20App/green?icon=telegram)](https://viper86rus-arch.github.io/Telegram_Commerce_MiniApp/)
[![Tests](https://badgen.net/badge/Tests/14%2F14%20Passed/green)](tests/)
[![Security Audit](https://badgen.net/badge/Security%20Audit/8%2F8%20Hardened/green)](audit_stress_test.py)
[![Python Version](https://badgen.net/badge/Python/3.10%20-%203.13/blue?icon=python)](https://www.python.org/)
[![Studio](https://badgen.net/badge/Studio/V1PER%20IT%20Solutions/cyan)](https://github.com/viper86rus-arch)
[![Telegram](https://badgen.net/badge/Telegram%20Bot%20API/v7.0+/blue?icon=telegram)](https://core.telegram.org/bots/webapps)
[![Dependencies](https://badgen.net/badge/Dependencies/Zero-Pip/purple)](https://github.com/viper86rus-arch/Telegram_Commerce_MiniApp)
[![Database](https://badgen.net/badge/Database/SQLite3%20WAL/blue)](https://sqlite.org/)
[![License: MIT](https://badgen.net/badge/license/MIT/yellow)](LICENSE)

> 🎮 **[Запустить интерактивное Live Demo в браузере](https://viper86rus-arch.github.io/Telegram_Commerce_MiniApp/)**  
> **Полнофункциональный эталонный интернет-магазин и витрина заказов для Telegram Mini Apps (TMA) от студии V1PER IT Solutions.**  
> Спроектирован по стандарту высокой производительности: ультра-быстрый адаптивный фронтенд без тяжелых сборок (загрузка <100 мс) и серверный бэкенд на стандартной библиотеке Python с транзакционной базой данных SQLite. Не требует установки сторонних pip-библиотек.

> [!IMPORTANT]
> **🚀 Разработка и внедрение интернет-магазина в Telegram (TMA) под ключ:**  
> В данном репозитории представлена базовая открытая архитектура и демо-витрина электроники. Студия **V1PER IT Solutions** выполняет индивидуальную разработку полномасштабного магазина в Telegram под ключ:
> - 🛍️ **Ваш каталог и брендинг:** перенос вашей товарной матрицы, модификаций, цен, фотогалерей и персонального дизайна.
> - 📦 **Интеграция со складом:** автоматическая синхронизация товаров и заказов с вашей CRM (МойСклад, 1С, RetailCRM, Битрикс24).
> - 💳 **Приём платежей:** подключение эквайринга (ЮKassa, Т-Банк, Сбербанк, СБП, Telegram Stars) с автоматической фискализацией (54-ФЗ).
> - 🚚 **Логистика и доставка:** интеграция модулей расчёта стоимости и пунктов выдачи СДЭК, Boxberry, Почты РФ.
> - 🛡️ **Инфраструктура:** развёртывание на надёжном сервере с SSL-сертификатом, CDN и поддержкой 24/7.
>
> 📩 **Заказать разработку магазина:** [Заказать на Kwork (Безопасная сделка)](https://kwork.ru/user/V1PER86RUS) • [Создать заявку (Issue)](https://github.com/viper86rus-arch/Telegram_Commerce_MiniApp/issues) • [Профиль студии](https://github.com/viper86rus-arch)

---

## 📑 Содержание

- [Ключевые возможности](#-ключевые-возможности)
- [Архитектура решения](#-архитектура-решения)
- [Структура проекта](#-структура-проекта)
- [Быстрый старт (Zero-Pip)](#-быстрый-старт-zero-pip)
- [Интеграция с Telegram Bot (@BotFather)](#-интеграция-с-telegram-bot-botfather)
- [Спецификация REST API](#-спецификация-rest-api)
- [Среды развертывания](#-среды-развертывания)
- [Лицензия и авторство](#-лицензия-и-авторство)

---

## ✨ Ключевые возможности

| Возможность | Описание реализации |
|---|---|
| **Zero-Pip Architecture** | Полная автономность: работает на стандартных библиотеках Python (`http.server`, `sqlite3`, `urllib.request`) без внешних pip-пакетов. |
| **Telegram WebApp SDK v7.0+** | Глубокая интеграция: адаптация под темную/светлую тему, нативная нижняя кнопка `MainButton`, тактильная отдача `HapticFeedback`, закрытие через подтверждение. |
| **Интерактивная витрина** | Каталог товаров с категориями, быстрым поиском, фильтрами, модальными карточками описания и бейджами («Хит», «Новинка»). |
| **Корзина и Bottom Sheet** | Выдвижная шторка корзины с мгновенным пересчетом сумм, управлением количеством (+ / −) и сохранением состояния в `localStorage`. |
| **Многоканальное оформление** | Валидация контактов, адреса доставки и выбор методов оплаты (Telegram Stars, банковские карты / СБП, счета для юр. лиц). |
| **Автономный бот и чеки** | Встроенный Long-Polling Telegram-бот: отправляет кнопку запуска WebApp, принимает оформленные заказы и высылает покупателю структурированный электронный чек. |
| **Уведомления администратору** | Мгновенная отправка детального состава каждого заказа в Telegram-чат оператора/администратора. |
| **Offline `--demo` режим** | Возможность локального запуска и полного тестирования интерфейса и корзины в обычном браузере без указания Telegram токена. |

---

## 🏛 Архитектура решения

```
┌────────────────────────────────────────────────────────┐
│                   Telegram Client                      │
│   (Telegram Mini App Webview / Desktop / Web Client)   │
└───────────────────────────┬────────────────────────────┘
                            │
               HTTPS / REST │ WebApp SDK Events
                            ▼
┌────────────────────────────────────────────────────────┐
│               MiniApp Python Backend                   │
│                                                        │
│  ┌───────────────────────┐   ┌───────────────────────┐ │
│  │   HTTP Server (8000)  │   │  Telegram Long Poller │ │
│  │   - Static Web Assets │   │  - /start Command     │ │
│  │   - REST API Endpoints│   │  - Receipts & Alerts  │ │
│  └───────────┬───────────┘   └───────────┬───────────┘ │
└──────────────┼───────────────────────────┼─────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────┐   ┌─────────────────────────┐
│     SQLite Database      │   │   Telegram Bot API      │
│ (store.db: Orders/Items) │   │ (api.telegram.org/bot)  │
└──────────────────────────┘   └─────────────────────────┘
```

---

## 📁 Структура проекта

```text
Telegram_Commerce_MiniApp/
├── server.py              # Основное серверное ядро (HTTP, REST API, Bot Controller)
├── database.py            # Модуль транзакционной базы данных SQLite (Zero-Pip)
├── .env.example           # Шаблон конфигурации переменных окружения
├── LICENSE                # Официальная лицензия MIT (2026)
├── README.md              # Документация и техническое руководство
├── data/                  # Каталог данных базы
│   └── store.db           # База данных SQLite (генерируется автоматически)
└── web/                   # Фронтенд-приложение Telegram Mini App
    ├── index.html         # Адаптивная разметка (Zero-Scroll, Bottom Sheets)
    ├── css/
    │   └── style.css      # Премиальный Dark Glassmorphism стиль
    └── js/
        └── app.js         # Контроллер витрины и интеграция Telegram SDK
```

---

## 🚀 Быстрый старт (Zero-Pip)

Для запуска не требуется устанавливать сторонние пакеты через `pip` — достаточно стандартного дистрибутива Python 3.10+.

### 1. Локальный запуск в демо-режиме (без Telegram токена)

```bash
# Клонирование репозитория
git clone https://github.com/viper86rus-arch/Telegram_Commerce_MiniApp.git
cd Telegram_Commerce_MiniApp

# Запуск сервера
python server.py --demo
```

После запуска откройте в браузере: **`http://127.0.0.1:8000`**.  
Интерфейс автоматически эмулирует среду Telegram WebApp SDK, позволяя наполнять корзину и оформлять тестовые заказы.

---

### 2. Запуск в режиме Telegram-бота

1. Скопируйте шаблон окружения и укажите ваш токен:
   ```bash
   cp .env.example .env
   ```
2. Запустите сервер с флагами авторизации:
   ```bash
   python server.py --token "ВАШ_ТОКЕН_БОТА" --admin-id "ВАШ_CHAT_ID" --webapp-url "https://your-domain.com"
   ```

---

## 🤖 Интеграция с Telegram Bot (@BotFather)

1. Откройте в Telegram официального бота **[@BotFather](https://t.me/BotFather)**.
2. Создайте нового бота через `/newbot` или выберите существующего через `/mybots`.
3. Перейдите в **Bot Settings** → **Menu Button** → **Configure menu button**.
4. Отправьте URL вашего развернутого веб-приложения (обязательно по протоколу `https://`, например через Cloudflare Tunnel, ngrok или собственный SSL-сервер).
5. Укажите название кнопки меню, например: `🛍️ Каталог V1-Store`.

---

## 📡 Спецификация REST API

Сервер предоставляет легковесный REST API со встроенной поддержкой CORS:

* **`GET /api/health`** — Проверка работоспособности сервиса.
* **`GET /api/categories`** — Получение списка категорий с иконками.
* **`GET /api/products`** — Получение витрины товаров. Поддерживает query-параметры `?category=hardware` и `?search=сервер`.
* **`POST /api/order`** — Оформление нового заказа.
  * *Тело запроса (JSON):*
    ```json
    {
      "customer_name": "Артем",
      "phone": "+7 (999) 000-00-00",
      "address": "г. Москва, ул. Тверская, 12",
      "payment_method": "Telegram Stars",
      "items": [
        { "id": "p-101", "quantity": 1 },
        { "id": "p-104", "quantity": 2 }
      ],
      "notes": "Доставка в первой половине дня"
    }
    ```
  * *Ответ (JSON, 201 Created):*
    ```json
    {
      "status": "success",
      "order_id": "ORD-2026-F981C0",
      "total_amount": 60700,
      "message": "Заказ успешно принят в обработку."
    }
    ```

---

## 🛡️ Аудит безопасности и стресс-тестирование

Кодовая база прошла полный ревизионный аудит защищенности и стресс-тестирование (`audit_stress_test.py`) по 8 ключевым векторам отказоустойчивости и информационной безопасности:

```bash
# Запуск полного стресс-теста безопасности:
python audit_stress_test.py

# Запуск модульных тестов:
python -m unittest discover -s tests -v
```

| Вектор аудита | Статус | Описание реализованной защиты |
|---|:---:|---|
| **Directory Traversal (CWE-22, CWE-548)** | 🟢 Защищено | Блокировка выхода за пределы `web/`, запрет автолистинга каталогов (`list_directory`). |
| **Price Tampering (CWE-472)** | 🟢 Защищено | Сервер полностью игнорирует клиентские цены и производит строгий пересчет сумм по SQLite. |
| **XSS & HTML Injection (CWE-79, CWE-116)** | 🟢 Защищено | Экранирование всех пользовательских полей (`html.escape`), безопасная работа с DOM, CSP заголовки. |
| **SQLite Concurrency & WAL (CWE-662)** | 🟢 Защищено | PRAGMA WAL, `busy_timeout = 5000`, пул `ClosingConnection` с гарантированным закрытием дескрипторов. |
| **Memory DoS & Slowloris (CWE-770, CWE-400)** | 🟢 Защищено | Лимит размера тела запроса (`MAX_CONTENT_LENGTH = 1MB`), валидация заголовка `Content-Length`. |
| **Threading & Signals (CWE-400)** | 🟢 Защищено | Неблокирующий `ThreadingHTTPServer`, грациозное завершение по `SIGINT` (Ctrl+C, exit code 130) и `SIGTERM`. |
| **CSV / Excel Formula Injection (CWE-1236)** | 🟢 Защищено | Автоматическая санитизация префиксом `'` опасных формул (`=`, `+`, `-`, `@`, `\t`), UTF-8 BOM и разделитель `;`. |
| **PII Data Masking in Logs (CWE-532)** | 🟢 Защищено | Маскирование персональных данных клиентов в журналах сервера и базы данных. |

---

## 🖥 Среды развертывания

Протестировано и гарантированно работает на серверных платформах:
* **Linux:** Ubuntu 20.04/22.04/24.04 LTS, Debian 11/12, RHEL / Rocky Linux 9+.
* **macOS:** macOS Monterey, Ventura, Sonoma, Sequoia (Apple Silicon & Intel).
* **Windows Server:** Windows Server 2019/2022 / Windows 10/11.

---

## 📄 Лицензия и авторство

* **Автор разработки:** V1PER ([`viper86rus-arch`](https://github.com/viper86rus-arch))
* **Лицензия:** [MIT License](LICENSE) (2026) — открытый исходный код без ограничений на коммерческое и образовательное применение.
