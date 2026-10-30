import sqlite3
import pandas as pd
import numpy as np


# Этап F. Загрузка таблиц в SQLite.
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
            rtol=1e-9,
            atol=1e-9
        )
    )

    print(f'\nАгрегаты полностью совпадают: {aggregates_match}')

    return org_stats_sql, org_stats_pd