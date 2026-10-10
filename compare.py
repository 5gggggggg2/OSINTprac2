import pandas as pd

#Загружаем оба датасета
df_api = pd.read_csv("api_dataset.csv")
df_scr = pd.read_csv(r"C:\Users\Semen\OneDrive\Рабочий стол\ЛАБЫ\осинт\практика 2\books_dataset.csv")

print(f"ПР2 (скрапинг): {df_scr.shape[0]} записей, {df_scr.shape[1]} колонок")
print(f"ПР3 (API):      {df_api.shape[0]} записей, {df_api.shape[1]} колонок")

#Нормализуем названия для сопоставления
titles_api = set(df_api["title"].dropna().str.lower().str.strip())
titles_scr = set(df_scr["title"].dropna().str.lower().str.strip())

common = titles_api & titles_scr

print(f"\nОбщих названий:      {len(common)}")
print(f"Только в API:        {len(titles_api - titles_scr)}")
print(f"Только в скрапинге:  {len(titles_scr - titles_api)}")

#Статистика по OpenAlex-датасету
print(f"\n--- Статистика ПР3 (OpenAlex) ---")
print(f"Диапазон годов публикаций: {df_api['publication_year'].min()} – {df_api['publication_year'].max()}")
print(f"\nТоп-5 типов публикаций:")
print(df_api['type'].value_counts().head())
print(f"\nТоп-5 языков:")
print(df_api['language'].value_counts().head())
print(f"\nТоп-5 институций:")
print(df_api['institution'].value_counts().head())
