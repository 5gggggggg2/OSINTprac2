import pandas as pd
df_api = pd.read_csv("api_dataset.csv")
print(f"Строк: {df_api.shape[0]}, колонок: {df_api.shape[1]}")
print(df_api.columns.tolist())
print(df_api[["title", "first_publish_year", "author_name"]].head(5))
