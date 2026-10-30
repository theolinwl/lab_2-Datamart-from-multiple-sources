import pandas as pd


# Этап D. Очистка ключей.
def clean_keys(df, key_column):
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
def merge_df(left_df, right_df, left_key, right_key,
             how='inner', indicator=True, validate=None):

    merged_df = pd.merge(
        left_df, right_df,
        left_on=left_key,
        right_on=right_key,
        how=how,
        indicator=indicator,
        validate=validate
    )

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