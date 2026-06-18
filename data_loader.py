import pandas as pd
import numpy as np
import hashlib
from datetime import datetime, timedelta


def _stable_hash(s):
    return int(hashlib.md5(str(s).encode('utf-8')).hexdigest(), 16) % (2**31)


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


def get_price_trend(df, variety, days=30, start_date=None, end_date=None):
    if end_date is None:
        end_date = df['date'].max()
    if start_date is None:
        start_date = end_date - timedelta(days=days)
    filtered = df[
        (df['variety'] == variety) &
        (df['date'] >= start_date) &
        (df['date'] <= end_date)
    ]
    trend = filtered.groupby('date').agg({
        'price_yuan_per_jin': 'mean',
        'volume_ton': 'sum'
    }).reset_index()
    trend = trend.sort_values('date')
    return trend


def detect_price_anomalies(df, variety, threshold=0.15):
    if len(df) < 1:
        return pd.DataFrame()
    trend = get_price_trend(
        df, variety,
        start_date=df['date'].min(),
        end_date=df['date'].max()
    )
    if len(trend) < 3:
        return pd.DataFrame()

    trend['pct_change'] = trend['price_yuan_per_jin'].pct_change()
    trend['abs_pct_change'] = trend['pct_change'].abs()
    anomalies = trend[trend['abs_pct_change'] > threshold].copy()
    anomalies['change_direction'] = anomalies['pct_change'].apply(
        lambda x: '上涨' if x > 0 else '下跌'
    )
    return anomalies


def calculate_kline_data(df, variety, days=90, start_date=None, end_date=None):
    if end_date is None:
        end_date = df['date'].max()
    if start_date is None:
        start_date = end_date - timedelta(days=days)

    filtered = df[
        (df['variety'] == variety) &
        (df['date'] >= start_date) &
        (df['date'] <= end_date)
    ]

    if len(filtered) < 1:
        return pd.DataFrame()

    def _calc_ohlc(group):
        prices = group.sort_values('market')['price_yuan_per_jin'].values
        sorted_prices = np.sort(prices)
        return pd.Series({
            'open': sorted_prices[0],
            'high': sorted_prices[-1],
            'low': sorted_prices[0],
            'close': np.mean(sorted_prices),
            'volume_ton': group['volume_ton'].sum()
        })

    ohlc = filtered.groupby('date').apply(_calc_ohlc).reset_index()
    ohlc['date'] = pd.to_datetime(ohlc['date'])
    ohlc = ohlc.sort_values('date').reset_index(drop=True)

    kline_data = pd.DataFrame()
    kline_data['date'] = ohlc['date']
    kline_data['open'] = ohlc['open'].values
    kline_data['close'] = ohlc['close'].values
    kline_data['high'] = ohlc['high'].values
    kline_data['low'] = ohlc['low'].values
    kline_data['volume'] = ohlc['volume_ton'].values

    for i in range(1, len(kline_data)):
        prev_close = kline_data.loc[i - 1, 'close']
        curr_open = kline_data.loc[i, 'open']
        blend = 0.5
        kline_data.loc[i, 'open'] = prev_close * blend + curr_open * (1 - blend)

    if len(kline_data) > 0:
        for i in range(len(kline_data)):
            o = kline_data.loc[i, 'open']
            c = kline_data.loc[i, 'close']
            h = kline_data.loc[i, 'high']
            l = kline_data.loc[i, 'low']
            kline_data.loc[i, 'high'] = max(h, o, c)
            kline_data.loc[i, 'low'] = min(l, o, c)

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


def get_years_in_range(start_date, end_date):
    start_year = pd.Timestamp(start_date).year
    end_year = pd.Timestamp(end_date).year
    return list(range(start_year, end_year + 1))


def get_season_ranges_for_years(years):
    season_ranges = get_season_ranges()
    result = []
    for year in years:
        for season, info in season_ranges.items():
            try:
                start_dt = datetime(year, info['start_month'], info['start_day'])
                end_dt = datetime(year, info['end_month'], info['end_day'])
                result.append({
                    'year': year,
                    'season': season,
                    'start': start_dt,
                    'end': end_dt,
                    'color': info['color']
                })
            except (ValueError, TypeError):
                pass
    return result
