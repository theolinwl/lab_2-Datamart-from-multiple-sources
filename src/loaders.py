import pandas as pd
import requests
import sqlite3


# Этап C. Загрузка источников в Python.
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