import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def load_trading_data():
    df = pd.read_csv('data/tea_trading_data.csv', encoding='utf-8-sig')
    df['date'] = pd.to_datetime(df['date'])
    return df


def load_weather_data():
    df = pd.read_csv('data/weather_data.csv', encoding='utf-8-sig')
    df['date'] = pd.to_datetime(df['date'])
    return df


def get_market_summary(df):
    summary = df.groupby('market').agg({
        'volume_ton': 'sum',
        'price_yuan_per_jin': 'mean'
    }).reset_index()
    summary.columns = ['market', 'total_volume_ton', 'avg_price']
    return summary


def get_variety_summary(df):
    summary = df.groupby('variety').agg({
        'volume_ton': 'sum',
        'price_yuan_per_jin': 'mean'
    }).reset_index()
    summary.columns = ['variety', 'total_volume_ton', 'avg_price']
    summary = summary.sort_values('total_volume_ton', ascending=False)
    return summary


def get_price_trend(df, variety, days=30):
    end_date = df['date'].max()
    start_date = end_date - timedelta(days=days)
    filtered = df[(df['variety'] == variety) & (df['date'] >= start_date)]
    trend = filtered.groupby('date').agg({
        'price_yuan_per_jin': 'mean',
        'volume_ton': 'sum'
    }).reset_index()
    trend = trend.sort_values('date')
    return trend


def detect_price_anomalies(df, variety, threshold=0.15):
    trend = get_price_trend(df, variety, days=365)
    if len(trend) < 3:
        return pd.DataFrame()

    trend['pct_change'] = trend['price_yuan_per_jin'].pct_change()
    trend['abs_pct_change'] = trend['pct_change'].abs()
    anomalies = trend[trend['abs_pct_change'] > threshold].copy()
    anomalies['change_direction'] = anomalies['pct_change'].apply(
        lambda x: '上涨' if x > 0 else '下跌'
    )
    return anomalies


def calculate_kline_data(df, variety, days=90):
    trend = get_price_trend(df, variety, days=days)
    if len(trend) < 1:
        return pd.DataFrame()

    trend['date'] = pd.to_datetime(trend['date'])

    kline_data = pd.DataFrame()
    kline_data['date'] = trend['date']
    kline_data['open'] = trend['price_yuan_per_jin'].shift(1)
    kline_data['close'] = trend['price_yuan_per_jin']

    def seeded_random(seed_val, low, high, idx):
        rng = np.random.default_rng(seed=seed_val)
        return rng.uniform(low, high)

    kline_data['high'] = trend.apply(
        lambda row: row['price_yuan_per_jin'] * (1 + seeded_random(
            int(pd.Timestamp(row['date']).timestamp() * 1000) + hash(variety) % 10000,
            0.005, 0.03, 0
        )),
        axis=1
    )
    kline_data['low'] = trend.apply(
        lambda row: row['price_yuan_per_jin'] * (1 - seeded_random(
            int(pd.Timestamp(row['date']).timestamp() * 1000) + hash(variety) % 10000 + 999,
            0.005, 0.03, 0
        )),
        axis=1
    )
    kline_data['volume'] = trend['volume_ton']

    if len(kline_data) > 0:
        first_seed = int(pd.Timestamp(kline_data.loc[0, 'date']).timestamp() * 1000) + hash(variety) % 10000 + 555
        rng_first = np.random.default_rng(seed=first_seed)
        kline_data.loc[0, 'open'] = kline_data.loc[0, 'close'] * (1 + rng_first.uniform(-0.02, 0.02))

    return kline_data


def get_season_ranges():
    return {
        '春茶': {'start_month': 3, 'start_day': 1, 'end_month': 5, 'end_day': 31, 'color': '#22c55e'},
        '夏茶': {'start_month': 6, 'start_day': 1, 'end_month': 8, 'end_day': 31, 'color': '#eab308'},
        '秋茶': {'start_month': 9, 'start_day': 1, 'end_month': 11, 'end_day': 30, 'color': '#f97316'}
    }


def compare_mingqian_yuqian(df, variety=None):
    if variety:
        df = df[df['variety'] == variety]

    mingqian = df[df['is_mingqian'] == True]
    yuqian = df[df['is_yuqian'] == True]

    result = {
        'mingqian_avg_price': mingqian['price_yuan_per_jin'].mean() if len(mingqian) > 0 else 0,
        'yuqian_avg_price': yuqian['price_yuan_per_jin'].mean() if len(yuqian) > 0 else 0,
        'mingqian_total_volume': mingqian['volume_ton'].sum() if len(mingqian) > 0 else 0,
        'yuqian_total_volume': yuqian['volume_ton'].sum() if len(yuqian) > 0 else 0,
        'mingqian_count': len(mingqian),
        'yuqian_count': len(yuqian)
    }

    if result['yuqian_avg_price'] > 0:
        result['price_diff_pct'] = (result['mingqian_avg_price'] - result['yuqian_avg_price']) / result['yuqian_avg_price'] * 100
    else:
        result['price_diff_pct'] = 0

    return result


def get_weather_warnings(weather_df, location=None, start_date=None, end_date=None):
    filtered = weather_df.copy()
    if location:
        filtered = filtered[filtered['location'] == location]
    if start_date:
        filtered = filtered[filtered['date'] >= start_date]
    if end_date:
        filtered = filtered[filtered['date'] <= end_date]
    return filtered[filtered['has_warning'] == True]


def get_market_volume_distribution(df, start_date=None, end_date=None):
    filtered = df.copy()
    if start_date:
        filtered = filtered[filtered['date'] >= start_date]
    if end_date:
        filtered = filtered[filtered['date'] <= end_date]

    dist = filtered.groupby(['market', 'province'])['volume_ton'].sum().reset_index()
    dist = dist.sort_values('volume_ton', ascending=False)
    return dist


def get_daily_summary(df):
    summary = df.groupby('date').agg({
        'volume_ton': 'sum',
        'price_yuan_per_jin': 'mean'
    }).reset_index()
    return summary
