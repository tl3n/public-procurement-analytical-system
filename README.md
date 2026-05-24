# Аналітична система моніторингу державних закупівель України

Аналітична система для автоматизованого збору, обробки та візуалізації даних
про тендерні процедури з відкритого API [Prozorro](https://prozorro.gov.ua).
Дипломна робота на здобуття ступеня бакалавра.

---

## Можливості

- **Збір** — інкрементальна синхронізація з публічним API Prozorro з
  відмовостійкою стратегією повторних спроб, ідемпотентною нормалізацією та
  локальним кешем оригінальних JSON-документів.
- **Аналітика** — п'ять індикаторів ризику (одиночне подання, неконкурентна
  процедура, скорочений строк, концентрація витрат замовника, цінове
  відхилення), розширюваний фреймворк індикаторів, агрегації за типом /
  регіоном / CPV і часовою динамікою, виявлення викидів (IQR, MAD), HHI / Gini,
  кореляції, сезонна декомпозиція.
- **REST API** — пошук тендерів із багатовимірним фільтруванням і keyset-
  пагінацією, дашборд, рейтинги, звіт по індикаторах, потоковий експорт у
  CSV / JSON, ендпоінт ручного перерахунку.
- **Інтерфейс** — SPA на React+TypeScript із дашбордом, переліком тендерів із
  фільтрами, деталями тендеру (включно з результатами індикаторів) та
  аналітичним поданням із часовим діапазоном і експортом.

---

## Архітектура

Модульний моноліт із п'яти сервісів. Усе піднімається через Docker Compose:

| Сервіс      | Стек                              | Призначення                                                       |
|-------------|-----------------------------------|-------------------------------------------------------------------|
| `postgres`  | PostgreSQL 16                     | Структуровані дані + повний JSONB-документ кожного тендеру        |
| `redis`     | Redis 7                           | Кеш агрегаційних відповідей API                                   |
| `backend`   | FastAPI · SQLAlchemy 2.x (async)  | REST API + аналітичний модуль                                     |
| `scheduler` | APScheduler 3.x · AsyncIOScheduler| Періодичний збір даних із Prozorro, при старті виконує міграції   |
| `frontend`  | Vite · React 18 · TypeScript      | SPA з дашбордом, переліком, деталями та аналітикою                |

Дані рухаються однонаправлено: `scheduler` тягне з API Prozorro → нормалізує
→ пише в Postgres → `backend` віддає аналітику через REST → `frontend`
відображає.

---

## Quickstart

Передумова: встановлений Docker із Docker Compose v2.

```bash
git clone <repo>
cd public-procurement-analytical-system
cp .env.example .env

# Перший запуск: піднімає БД + кеш, виконує міграції, запускає періодичний збір.
docker compose up -d --build

# Відкрити інтерфейс:                http://localhost:5173/
# OpenAPI документація бекенду:      http://localhost:8000/docs
# Перевірка стану бекенду:           http://localhost:8000/health
```

Логи планувальника (видно сам процес збору):

```bash
docker compose logs -f scheduler
```

Зупинити все, зберігши дані:

```bash
docker compose down
```

Повне очищення (видаляє volume PostgreSQL — наступний запуск піде з нуля):

```bash
docker compose down -v
```

---

## Швидке наповнення демо-даними

За замовчуванням `scheduler` тягне до `MAX_TENDERS=20000` записів за один
запуск, що для презентації забагато. Простіше — запустити `seed_demo`,
який збирає невелику вибірку та одразу обчислює всі індикатори.

```bash
# Зупинити автоматичний збір, поки робимо демо.
docker compose stop scheduler

# Завантажити 200 тендерів зі свіжого стану та обчислити індикатори
# (можна вказати інше число; --fresh скидає курсор синхронізації).
docker compose run --rm backend python -m app.scripts.seed_demo 200 --fresh

# Готово — відкрийте http://localhost:5173/
```

Перевірити, скільки тендерів у БД, можна напряму:

```bash
docker compose exec postgres psql -U procurement -d procurement \
  -c "SELECT count(*) FROM tenders;"
```

---

## Змінні середовища

Усі параметри задаються через `.env` (шаблон у `.env.example`).

| Змінна                          | Призначення                                                        | За замовчуванням                                            |
|---------------------------------|--------------------------------------------------------------------|-------------------------------------------------------------|
| `POSTGRES_USER` / `_PASSWORD` / `_DB` | Параметри PostgreSQL                                          | `procurement` / `procurement` / `procurement`              |
| `DATABASE_URL`                  | DSN підключення з боку застосунку (`postgresql+asyncpg://…`)       | див. `.env.example`                                         |
| `REDIS_URL`                     | DSN підключення до Redis                                           | `redis://redis:6379/0`                                      |
| `PROZORRO_API_URL`              | База API Prozorro                                                  | `https://public.api.openprocurement.org/api/2.5`            |
| `SYNC_INTERVAL_MINUTES`         | Інтервал між циклами планувальника                                 | `10`                                                        |
| `MAX_TENDERS`                   | Жорсткий ліміт на кількість записів за один цикл                   | `20000`                                                     |
| `INITIAL_LOAD_START_TIMESTAMP`  | Unix-таймстемп, з якого починається перший прохід (за `dateModified`)| `1767225600` (2026-01-01 UTC)                              |
| `CACHE_TTL_SECONDS`             | TTL кешу агрегаційних ендпоінтів                                   | `300` (5 хв)                                                |
| `BACKEND_PORT`                  | Зовнішній порт для бекенду                                         | `8000`                                                      |
| `FRONTEND_PORT`                 | Зовнішній порт для фронтенду                                       | `5173`                                                      |

---

## Адміністрування

```bash
# Зупинити лише збір даних (інші сервіси продовжують працювати).
docker compose stop scheduler

# Скинути курсор синхронізації — наступний цикл піде з INITIAL_LOAD_START_TIMESTAMP.
docker compose exec postgres psql -U procurement -d procurement \
  -c "DELETE FROM sync_state WHERE feed_name = 'tenders';"

# Очистити кеш агрегацій без скидання даних.
docker compose exec redis redis-cli FLUSHDB

# Запустити повний перерахунок індикаторів (також скидає кеш).
curl -X POST http://localhost:8000/admin/recompute

# Виконати міграції вручну (у штатному режимі це робить scheduler при старті).
docker compose run --rm backend alembic upgrade head
```

---

## Розробка

### Backend

```bash
# Тести (потребують підняті postgres + redis):
docker compose run --rm -v "$(pwd)/backend:/app" backend pytest

# З покриттям:
docker compose run --rm -v "$(pwd)/backend:/app" backend pytest \
  --cov=app --cov-report=term-missing
```

Стек тестів: pytest, pytest-asyncio, pytest-cov, httpx MockTransport для
ізольованих сценаріїв API. Поточне покриття — 92%.

### Frontend

```bash
# Тип-чек:
docker compose run --rm --no-deps -v "$(pwd)/frontend:/app" frontend npm run type-check

# Прод-збірка:
docker compose run --rm --no-deps -v "$(pwd)/frontend:/app" frontend npm run build
```

---

## Структура проекту

```
backend/
  app/
    api/           # FastAPI роутери + Pydantic схеми
    analytics/     # Індикатори, агрегації, статистики, пакетний перерахунок
    collector/     # HTTP-клієнт, пагінатор фіду, нормалізатор → ORM
    models/        # SQLAlchemy декларативні моделі
    scheduler/     # AsyncIOScheduler — точка входу контейнера scheduler
    scripts/       # CLI-скрипти (seed_demo тощо)
    cache.py       # Fail-soft Redis-обгортка
    config.py      # pydantic-settings конфігурація з env
    db.py          # async engine + сесії
    main.py        # FastAPI app + /health
  alembic/         # Міграції
  tests/           # pytest-suite із seeded fixtures

frontend/
  src/
    api/           # Типи + HTTP-клієнт
    components/    # shadcn/ui примітиви + UI-блоки за доменом
    lib/           # Утиліти форматування, метадані індикаторів
    routes/        # Сторінки маршрутизатора (Dashboard / TenderList / TenderDetail / Statistics)

docs/
  defense_notes.md # Підказки для захисту дипломної роботи

design.md          # Текст диплому (gitignored, локальний референс)
instructions.md    # Поетапний план реалізації за комітами (gitignored)
```

---

## Дизайн і обґрунтування рішень

Усе технічне обґрунтування — у `design.md` (текст дипломної роботи).
Найбільш специфічні рішення:

- **`raw_data` JSONB поряд із структурованими колонками** — швидкі агрегати по
  типізованих стовпцях + повний оригінальний обʼєкт API для довільного аналізу.
- **Замовники й постачальники — окремі сутності з UUID PK**, ідентифікація за
  ЄДРПОУ, унікальне обмеження. Тендер з API має 32-символьний hex як PK.
- **Replace-стратегія для дочірніх сутностей тендеру** + upsert тендеру —
  ідемпотентна синхронізація під регулярні re-emit'и API.
- **Keyset-пагінація `(date_published, id)`** замість OFFSET для стабільності
  під час паралельних оновлень.
- **Fail-soft Redis** — пропадання кешу не валить API, лише пришвидшується
  база. Інвалідація після recompute.
