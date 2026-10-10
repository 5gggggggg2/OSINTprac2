import logging
import time
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

#Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler("api_collector.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("api_collector")

BASE_URL = "https://openlibrary.org"
HEADERS = {
    "User-Agent": "student-osint-pr3 (educational use)",
    "Accept": "application/json"
}


def build_session() -> requests.Session:
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update(HEADERS)
    return session


def fetch_all(session, query, max_records=500):
    """Собирает записи с пагинацией через offset."""
    records = []
    limit = 100
    offset = 0

    while len(records) < max_records:
        params = {"q": query, "limit": limit, "offset": offset}
        try:
            resp = session.get(f"{BASE_URL}/search.json", params=params, timeout=10)
            resp.raise_for_status()
            page = resp.json()
        except requests.exceptions.Timeout:
            log.warning("Таймаут на offset=%d", offset)
            offset += limit
            continue
        except requests.exceptions.RequestException as e:
            log.error("Ошибка на offset=%d: %s", offset, e)
            break

        docs = page.get("docs", [])
        if not docs:
            log.info("Пустая страница — остановка")
            break

        records.extend(docs)
        log.info("offset=%d: +%d (всего %d)", offset, len(docs), len(records))
        offset += limit

        if offset >= page.get("numFound", 0):
            break
        time.sleep(0.5)

    return records[:max_records]


#Сбор
session = build_session()
raw_records = fetch_all(session, "Cornell University", max_records=500)
log.info("Итого собрано: %d", len(raw_records))

#Нормализация и сохранение
flat_records = []

for r in raw_records:
    # Безопасно извлекаем значения — если поля нет, ставим None
    author_name = r.get("author_name")
    if isinstance(author_name, list):
        author_name = ", ".join(str(a) for a in author_name[:3])  # первые 3 автора

    publisher = r.get("publisher")
    if isinstance(publisher, list):
        publisher = ", ".join(str(p) for p in publisher[:3])

    language = r.get("language")
    if isinstance(language, list):
        language = ", ".join(str(l) for l in language[:3])

    isbn = r.get("isbn")
    if isinstance(isbn, list):
        isbn = ", ".join(str(i) for i in isbn[:3])

    flat_records.append({
        "key": r.get("key"),
        "title": r.get("title"),
        "subtitle": r.get("subtitle"),
        "first_publish_year": r.get("first_publish_year"),
        "author_name": author_name,
        "publisher": publisher,
        "language": language,
        "isbn": isbn,
        "edition_count": r.get("edition_count"),
        "ebook_access": r.get("ebook_access"),
    })

df = pd.DataFrame(flat_records)
df = df.drop_duplicates(subset="key").reset_index(drop=True)
df.to_csv("api_dataset.csv", index=False, encoding="utf-8-sig", quoting=1)

log.info("Сохранено: %d строк, %d колонок", *df.shape)
print(f"\nДатасет: api_dataset.csv — {df.shape[0]} строк, {df.shape[1]} колонок")
print(f"Колонки: {df.columns.tolist()}")
print(f"\nПервые 3 записи:")
print(df[["title", "first_publish_year", "author_name"]].head(3))
