# Аналітична система моніторингу державних закупівель України

Аналітична система для автоматизованого збору, обробки та візуалізації даних про
тендерні процедури з відкритого API Prozorro.

## Архітектура

Модульний моноліт із чотирьох сервісів, розгортається через Docker Compose:

| Сервіс      | Призначення                                              |
|-------------|----------------------------------------------------------|
| `postgres`  | PostgreSQL 16 — структуровані дані + JSONB               |
| `redis`     | Кеш агрегаційних запитів                                 |
| `backend`   | FastAPI — REST API та аналітичний модуль                 |
| `scheduler` | APScheduler — періодичний збір даних з API Prozorro      |
| `frontend`  | React + TypeScript — вебзастосунок (SPA)                 |

## Технологічний стек

Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Alembic · httpx · APScheduler ·
Pandas / NumPy / statsmodels · PostgreSQL 16 · Redis · React · TypeScript.

## Запуск

```bash
cp .env.example .env       # за потреби відкоригувати параметри
docker compose up --build
```

Сервіси після запуску:

- Backend API — http://localhost:8000 (health: http://localhost:8000/health)
- OpenAPI документація — http://localhost:8000/docs
- Frontend — http://localhost:5173

## Конфігурація

Усі параметри задаються через змінні середовища у `.env` (див. `.env.example`):
рядок підключення до БД, URL API Prozorro, інтервал синхронізації, обмеження обсягу
збору (`MAX_TENDERS`).