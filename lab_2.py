import pandas as pd
import requests
import sqlite3
import numpy as np
import os


# Этап C. Загрузка источников в Python.


# organizations читается из CSV;
# transactions получается через REST API;
# cities извлекается SQL-запросом из SQLite.
def load_sources():
    organizations = pd.read_csv('data/raw/organizations.csv')

    response = requests.get('http://localhost:8000/api/transactions')
    response.raise_for_status()
    transactions = pd.DataFrame(response.json())

    conn = sqlite3.connect('data/raw/regions.db')
    cities = pd.read_sql_query('SELECT * FROM cities', conn)
    conn.close()

    print('Organizations:')
    print(f'Shape: {organizations.shape}')
    print(f'Типы данных:\n{organizations.dtypes}')
    print(f'Head:\n{organizations.head()}')
    print(f'Отсутствующие значения:\n{organizations.isna().sum()}')
    print(f'Дубликаты: {organizations.duplicated().sum()}')
    print(f"Число уникальных ключей: {organizations['org_id'].nunique()}\n")

    print('Transactions:')
    print(f'Shape: {transactions.shape}')
    print(f'Типы данных:\n{transactions.dtypes}')
    print(f'Head:\n{transactions.head()}')
    print(f'Отсутствующие значения:\n{transactions.isna().sum()}')
    print(f'Дубликаты: {transactions.duplicated().sum()}')
    print(f"Число уникальных ключей: {transactions['transaction_id'].nunique()}\n")

    print('Cities:')
    print(f'Shape: {cities.shape}')
    print(f'Типы данных:\n{cities.dtypes}')
    print(f'Head:\n{cities.head()}')
    print(f'Отсутствующие значения:\n{cities.isna().sum()}')
    print(f'Дубликаты: {cities.duplicated().sum()}')
    print(f"Число уникальных ключей: {cities['city_id'].nunique()}\n")

    return organizations, transactions, cities


# Этап D. Очистка ключей. 
def clean_keys(df, key_column):  
    # приводим ключи к одинаковому типу 
    # + корректно обрабатываем пропуски в ключах
    df[key_column] = pd.to_numeric(
        df[key_column], 
        errors='coerce'
    ).astype('Int64')

    print(f'Столбец: {key_column}')
    print(f'Пропущенные ключи: {df[key_column].isna().sum()}')
    print(f'Дубли ключей: {df[key_column].duplicated().sum()}\n')

    return df


def compare_keys(left_df, right_df, left_key, right_key):
    left_keys = set(left_df[left_key].dropna())
    right_keys = set(right_df[right_key].dropna())

    left_only = left_keys - right_keys
    right_only = right_keys - left_keys

    print(f'Сравнение {left_key} и {right_key}:')
    print(f'Ключи только слева: {sorted(left_only)}')
    print(f'Ключи только справа: {sorted(right_only)}')

    print(f'Количество ключей только слева: {len(left_only)}')
    print(f'Количество ключей только справа: {len(right_only)}\n')


def check_cardinality(left_df, right_df, left_key, right_key):
    left_unique = left_df[left_key].dropna().is_unique
    right_unique = right_df[right_key].dropna().is_unique

    if left_unique and right_unique:
        cardinality = '1:1'
    elif left_unique and not right_unique:
        cardinality = '1:N'
    elif not left_unique and right_unique:
        cardinality = 'N:1'
    else:
        cardinality = 'N:N'

    print(f'Кардинальность связи: {cardinality}')


# Этап E. Объединение средствами pandas. 
def merge_df(left_df, right_df, left_key, right_key, how='inner', indicator=True, validate=None):
    merged_df = pd.merge(
        left_df, right_df,
        left_on=left_key, right_on=right_key,
        how=how,
        indicator=indicator,
        validate=validate
    )

    # отдельное диагностическое объединение,
    # чтобы увидеть все три категории строк
    diagnostic = pd.merge(
        left_df,
        right_df,
        left_on=left_key,
        right_on=right_key,
        how='outer',
        indicator=True,
        validate=validate
    )

    print(f'Тип объединения: {how}')
    print(f'Строк в левой таблице: {left_df.shape[0]}')
    print(f'Строк в правой таблице: {right_df.shape[0]}')
    print(f'Строк после объединения: {merged_df.shape[0]}')
    print('Результат сравнения:')
    print(diagnostic['_merge'].value_counts())
    print()

    return merged_df


# Этап F. SQL JOIN. 
def load_to_sql(df, name):
    conn = sqlite3.connect('data/raw/cleaned.db')
    df.to_sql(
        name=name,
        con=conn,
        if_exists='replace',
        index=False
    )
    conn.close()


def merge_sql():
    conn = sqlite3.connect('data/raw/cleaned.db')
    org_trans_inner = pd.read_sql_query("""
        SELECT *
        FROM organizations o
        INNER JOIN transactions t
            ON o.org_id = t.org_id;
    """, conn)

    org_trans_left = pd.read_sql_query("""
        SELECT *
        FROM organizations o
        LEFT JOIN transactions t
            ON o.org_id = t.org_id;
    """, conn)

    full = pd.read_sql_query("""
        SELECT
            o.org_id, o.org_name, o.sector, o.city_id,
            t.transaction_id, t.date, t.amount, t.currency,
            c.city_name, c.region_name
        FROM organizations o
        LEFT JOIN transactions t
            ON o.org_id = t.org_id
        LEFT JOIN cities c
            ON o.city_id = c.city_id;
    """, conn)

    print(f'Количество строк INNER JOIN организаций и транзакций: {org_trans_inner.shape[0]}')
    print(f'Количество строк LEFT JOIN организаций и транзакций: {org_trans_left.shape[0]}')
    print(f'Количество строк LEFT JOIN набора и городов: {full.shape[0]}')
    
    conn.close()

    return org_trans_inner, org_trans_left, full


def aggregate_data(pd_table):
    conn = sqlite3.connect('data/raw/cleaned.db')

    org_stats_sql = pd.read_sql_query("""
        SELECT
            org_id,
            COUNT(*) AS transactions_count,
            SUM(amount) AS total_amount,
            AVG(amount) AS avg_amount
        FROM transactions
        GROUP BY org_id;
    """, conn)

    conn.close()

    org_stats_pd = pd_table.groupby('org_id').agg(
        transactions_count=('transaction_id', 'count'),
        total_amount=('amount', 'sum'),
        avg_amount=('amount', 'mean')
    ).reset_index()

    print('SQL:')
    print(org_stats_sql.head())

    print('\nPandas:')
    print(org_stats_pd.head())

    print('\nРазмер SQL:', org_stats_sql.shape)
    print('Размер Pandas:', org_stats_pd.shape)

    # проверяем соврадение
    # для целочисленныйх столбцов строго, для вычесленных - с погрешностью
    org_stats_pd['org_id'] = org_stats_pd['org_id'].astype('int64')
    sql_sorted = org_stats_sql.sort_values('org_id').reset_index(drop=True)
    pd_sorted = org_stats_pd.sort_values('org_id').reset_index(drop=True)
    aggregates_match = (
        sql_sorted[['org_id', 'transactions_count']].equals(
            pd_sorted[['org_id', 'transactions_count']]
        )
        and np.allclose(
            sql_sorted[['total_amount', 'avg_amount']],
            pd_sorted[['total_amount', 'avg_amount']],
            rtol=1e-9,  # относительная разница
            atol=1e-9   # макс. абсолютная разница
        )
    )
    print(f'\nАгрегаты полностью совпадают: {aggregates_match}')

    return org_stats_sql, org_stats_pd


# Этап G. Построение витрины.
def create_datamart(full_data):
    aggregated = full_data.groupby([
        'org_id', 'org_name', 'sector', 'city_name', 'region_name'
    ]).agg(
        transactions_count=('transaction_id', 'count'),
        total_amount=('amount', 'sum'),
        avg_amount=('amount', 'mean'),
        last_transaction_date=('date', 'max')
    ).reset_index()

    print(aggregated.head())
    print(f'\nРазмер: {aggregated.shape}')

    return aggregated


def save_datamart(datamart):
    os.makedirs('data/processed', exist_ok=True)
    datamart.to_csv('data/processed/data_mart.csv', index=False)
    datamart.to_parquet('data/processed/data_mart.parquet', index=False)
    print('\nФайлы сохранены в data/processed:')
    print(os.listdir('data/processed'))


if __name__ == '__main__':
    organizations, transactions, cities = load_sources()
    print('Загрузка источников завершена')
    print('-' * 40)

    print('\nОчистка ключей:')
    print('Организации:')
    organizations = clean_keys(organizations, 'org_id')
    organizations = clean_keys(organizations, 'city_id')
    print('Транзакции:')
    transactions = clean_keys(transactions, 'org_id')
    print('Города:')
    cities = clean_keys(cities, 'city_id')
    print('-' * 40)

    print('\nСравнение ключей:')
    print('Организации и транзакции:')
    compare_keys(organizations, transactions, 'org_id', 'org_id')
    print('Организации и города:')
    compare_keys(organizations, cities, 'city_id', 'city_id')
    print('-' * 40)

    print('\nКардинальность организаций и транзакций:')
    check_cardinality(
        organizations, transactions,
        'org_id', 'org_id'
    )

    print('\nКардинальность организаций и городов:')
    check_cardinality(
        organizations, cities,
        'city_id', 'city_id'
    )

    print('-' * 40)
    print(f'Убираем полный дубликат из транзакций перед merge...')
    transactions = transactions.drop_duplicates()

    print('-' * 40)
    print('Объединение организаций и транзакций INNER:')
    org_transactions_inner = merge_df(
        organizations,
        transactions,
        'org_id',
        'org_id',
        how='inner',
        validate='one_to_many'
    )

    print('Объединение организаций и транзакций LEFT:')
    org_transactions_left = merge_df(
        organizations,
        transactions,
        'org_id',
        'org_id',
        how='left',
        validate='one_to_many'
    )

    print('Объединение набора с городами LEFT:')
    # переименовываем столбец предыдущего индикатора
    # чтобы можно было создать новый
    org_transactions_left = org_transactions_left.rename(
        columns={'_merge': 'org_transaction_merge'}
    )
    full_data = merge_df(
        org_transactions_left,
        cities,
        'city_id',
        'city_id',
        how='left',
        validate='many_to_one'
    )

    print('-' * 40)
    load_to_sql(organizations, 'organizations')
    load_to_sql(transactions, 'transactions')
    load_to_sql(cities, 'cities')
    print('Загрузка таблиц в SQL завершена.')
    
    print('-' * 40)
    print('Результаты объединения через SQL:\n')
    org_trans_inner, org_trans_left, full = merge_sql()

    print('-' * 40)
    print('Агрегация через SQL и Pandas.')
    org_stats_sql, org_stats_pd = aggregate_data(pd_table=transactions)

    print('-' * 40)
    print('Построенная витрина:')
    datamart = create_datamart(full)
    save_datamart(datamart)
    