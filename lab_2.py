import os
import matplotlib.pyplot as plt

from src.loaders import load_sources
from src.transform import (
    clean_keys,
    compare_keys,
    check_cardinality,
    merge_df,
    create_datamart
)
from src.database import (
    load_to_sql,
    merge_sql,
    aggregate_data
)


def save_datamart(datamart):
    os.makedirs('data/processed', exist_ok=True)
    datamart.to_csv('data/processed/data_mart.csv', index=False)
    datamart.to_parquet('data/processed/data_mart.parquet', index=False)
    print('\nФайлы сохранены в data/processed:')
    print(os.listdir('data/processed'))


# Этап H. Визуализация и BI.
def visualise(datamart):
    os.makedirs('results/plots', exist_ok=True)
    # Общая сумма операция по регионам
    region_stats = datamart.groupby('region_name')['total_amount'].sum().sort_values(ascending=False)

    plt.figure(figsize=(10, 5))
    region_stats.plot(kind='bar')

    plt.title('Общая сумма операций по регионам')
    plt.xlabel('Регион')
    plt.ylabel('Сумма операций')
    plt.xticks(rotation=45, ha='right')
    plt.ticklabel_format(axis='y', style='plain')
    plt.tight_layout()

    plt.savefig('results/plots/region_totals.png')
    plt.close()

    # ТОП организаций по общей сумме
    top_orgs = datamart.nlargest(10, 'total_amount')

    plt.figure(figsize=(12, 6))
    plt.bar(top_orgs['org_name'], top_orgs['total_amount'])

    plt.title('TOP-10 организаций по общей сумме операций')
    plt.xlabel('Организация')
    plt.ylabel('Сумма операций')
    plt.xticks(rotation=45, ha='right')
    plt.ticklabel_format(axis='y', style='plain')
    plt.tight_layout()

    plt.savefig('results/plots/top_organizations.png')
    plt.close()

    print('\nПостроенные графики сохранены в results/plots')
    print(os.listdir('results/plots'))


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
    print('Убираем полный дубликат из транзакций перед merge...')
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

    print('-' * 40)
    print('Построенние графиков.')
    visualise(datamart)
