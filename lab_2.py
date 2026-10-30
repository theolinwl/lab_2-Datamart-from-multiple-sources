import pandas as pd
import requests
import sqlite3


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