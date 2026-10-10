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

#Настройки
BASE_URL = "https://api.openalex.org/works"
HEADERS = {
    "User-Agent": "student-osint-pr3 (educational use)",
    "Accept": "application/json"
}
MAILTO = "gorbenko.sa@gmail.com"

def build_session() -> requests.Session:
    """Сессия с автоматическими повторами при 429/5xx."""
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
    """Курсорная пагинация OpenAlex."""
    records = []
    cursor = "*"
    page_num = 0

    while len(records) < max_records:
        params = {
            "search": query,
            "per_page": 100,
            "cursor": cursor,
            "mailto": MAILTO
        }
        try:
            resp = session.get(BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
            page = resp.json()
        except requests.exceptions.Timeout:
            log.warning("Таймаут на странице %d — пропуск", page_num)
            break
        except requests.exceptions.RequestException as e:
            log.error("Ошибка запроса на странице %d: %s", page_num, e)
            break

        results = page.get("results", [])
        if not results:
            log.info("Пустая страница — остановка")
            break

        records.extend(results)
        page_num += 1
        log.info("Страница %d: +%d (всего %d)", page_num, len(results), len(records))

        cursor = page.get("meta", {}).get("next_cursor")
        if not cursor:
            log.info("Курсор пуст — конец результатов")
            break

        time.sleep(0.2)

    return records[:max_records]


#Сбор
session = build_session()
raw_records = fetch_all(session, "Cornell University", max_records=500)
log.info("Итого собрано: %d", len(raw_records))


#Нормализация под OpenAlex
flat_records = []

for r in raw_records:
    # Авторы: массив authorships → берём первые 3
    authors = []
    for a in r.get("authorships", [])[:3]:
        name = a.get("author", {}).get("display_name")
        if name:
            authors.append(name)
    author_name = ", ".join(authors)

    # Организации: массив institutions внутри authorships
    institutions = []
    for a in r.get("authorships", []):
        for inst in a.get("institutions", []):
            name = inst.get("display_name")
            if name and name not in institutions:
                institutions.append(name)
    institution = ", ".join(institutions[:3])

    # Тема (concept) — первая из concepts
    concepts = r.get("concepts", [])
    topic = concepts[0].get("display_name") if concepts else None

    flat_records.append({
        "id": r.get("id"),
        "doi": r.get("doi"),
        "title": r.get("display_name"),
        "publication_year": r.get("publication_year"),
        "author_name": author_name,
        "institution": institution,
        "topic": topic,
        "cited_by_count": r.get("cited_by_count"),
        "type": r.get("type"),
        "language": r.get("language"),
    })

df = pd.DataFrame(flat_records)
df = df.drop_duplicates(subset="id").reset_index(drop=True)
df.to_csv("api_dataset.csv", index=False, encoding="utf-8-sig", quoting=1)

log.info("Сохранено: %d строк, %d колонок", *df.shape)
print(f"\nДатасет: api_dataset.csv — {df.shape[0]} строк, {df.shape[1]} колонок")
print(f"Колонки: {df.columns.tolist()}")
print(f"\nПервые 3 записи:")
print(df[["title", "publication_year", "author_name"]].head(3))
