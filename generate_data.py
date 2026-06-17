import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

np.random.seed(42)
random.seed(42)

TEA_VARIETIES = [
    '龙井', '大红袍', '铁观音', '普洱', '金骏眉',
    '碧螺春', '信阳毛尖', '黄山毛峰', '太平猴魁', '六安瓜片',
    '祁门红茶', '白毫银针', '白牡丹', '君山银针', '蒙顶甘露',
    '都匀毛尖', '武夷岩茶', '正山小种', '滇红', '庐山云雾'
]

MARKETS = [
    {'name': '安溪', 'province': '福建', 'specialty': ['铁观音', '武夷岩茶', '大红袍']},
    {'name': '武夷山', 'province': '福建', 'specialty': ['大红袍', '武夷岩茶', '正山小种', '金骏眉']},
    {'name': '新昌', 'province': '浙江', 'specialty': ['龙井', '碧螺春']},
    {'name': '勐海', 'province': '云南', 'specialty': ['普洱', '滇红']},
    {'name': '横县', 'province': '广西', 'specialty': ['白毫银针', '白牡丹', '君山银针']}
]

SPRING_START = 3
SPRING_END = 5
SUMMER_START = 6
SUMMER_END = 8
AUTUMN_START = 9
AUTUMN_END = 11


def generate_tea_data():
    end_date = datetime(2026, 6, 16)
    start_date = end_date - timedelta(days=365)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')

    records = []

    for date in dates:
        month = date.month
        day_of_year = date.timetuple().tm_yday

        season_factor = 1.0
        is_spring_tea = SPRING_START <= month <= SPRING_END
        is_summer_tea = SUMMER_START <= month <= SUMMER_END
        is_autumn_tea = AUTUMN_START <= month <= AUTUMN_END

        if is_spring_tea:
            season_factor = 1.5
        elif is_autumn_tea:
            season_factor = 1.2
        elif is_summer_tea:
            season_factor = 0.9

        is_mingqian = month == 3 and day_of_year >= 80 and day_of_year <= 104
        is_yuqian = (month == 3 and day_of_year > 104) or (month == 4 and day_of_year <= 135)

        for market in MARKETS:
            for variety in TEA_VARIETIES:
                is_specialty = variety in market['specialty']
                specialty_factor = 1.5 if is_specialty else 0.7

                base_price_map = {
                    '龙井': 300, '大红袍': 500, '铁观音': 200, '普洱': 150, '金骏眉': 800,
                    '碧螺春': 280, '信阳毛尖': 250, '黄山毛峰': 220, '太平猴魁': 350, '六安瓜片': 260,
                    '祁门红茶': 240, '白毫银针': 600, '白牡丹': 320, '君山银针': 450, '蒙顶甘露': 200,
                    '都匀毛尖': 180, '武夷岩茶': 400, '正山小种': 350, '滇红': 160, '庐山云雾': 230
                }

                base_volume_map = {
                    '龙井': 8, '大红袍': 5, '铁观音': 12, '普洱': 15, '金骏眉': 3,
                    '碧螺春': 7, '信阳毛尖': 6, '黄山毛峰': 6, '太平猴魁': 4, '六安瓜片': 5,
                    '祁门红茶': 6, '白毫银针': 4, '白牡丹': 5, '君山银针': 3, '蒙顶甘露': 7,
                    '都匀毛尖': 8, '武夷岩茶': 6, '正山小种': 5, '滇红': 10, '庐山云雾': 6
                }

                base_price = base_price_map.get(variety, 200)
                base_volume = base_volume_map.get(variety, 5)

                price_factor = 1.0
                if is_mingqian:
                    price_factor = 1.8
                elif is_yuqian:
                    price_factor = 1.4

                trend = 0.001 * (day_of_year - 180)
                random_walk = np.random.normal(0, 0.02)

                anomaly = np.random.random() < 0.005
                if anomaly:
                    anomaly_factor = np.random.choice([0.7, 1.3, 0.65, 1.35])
                else:
                    anomaly_factor = 1.0

                price = base_price * season_factor * price_factor * specialty_factor * (1 + trend + random_walk) * anomaly_factor
                price = max(20, price)

                volume = base_volume * season_factor * specialty_factor * (1 + np.random.normal(0, 0.15))
                volume = max(0.1, volume)

                records.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'market': market['name'],
                    'province': market['province'],
                    'variety': variety,
                    'volume_ton': round(volume, 2),
                    'price_yuan_per_jin': round(price, 2),
                    'is_mingqian': is_mingqian,
                    'is_yuqian': is_yuqian,
                    'is_spring_tea': is_spring_tea,
                    'is_summer_tea': is_summer_tea,
                    'is_autumn_tea': is_autumn_tea
                })

    df = pd.DataFrame(records)
    df.to_csv('data/tea_trading_data.csv', index=False, encoding='utf-8-sig')
    print(f'Generated {len(df)} trading records')
    return df


def generate_weather_data():
    end_date = datetime(2026, 6, 16)
    start_date = end_date - timedelta(days=365)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')

    records = []

    for date in dates:
        month = date.month
        day_of_year = date.timetuple().tm_yday

        for market in MARKETS:
            location = market['name']

            if location in ['安溪', '武夷山']:
                base_temp = 15 + 15 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
                base_rain = 5 + 10 * np.sin((day_of_year - 100) * np.pi / 180)
            elif location == '新昌':
                base_temp = 12 + 16 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
                base_rain = 4 + 8 * np.sin((day_of_year - 90) * np.pi / 180)
            elif location == '勐海':
                base_temp = 18 + 8 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
                base_rain = 8 + 12 * np.sin((day_of_year - 120) * np.pi / 180)
            else:
                base_temp = 16 + 12 * np.sin((day_of_year - 80) * 2 * np.pi / 365)
                base_rain = 6 + 10 * np.sin((day_of_year - 100) * np.pi / 180)

            temp = base_temp + np.random.normal(0, 2)
            rainfall = max(0, base_rain + np.random.normal(0, 5))

            weather_type = '晴'
            if rainfall > 15:
                weather_type = '暴雨'
            elif rainfall > 8:
                weather_type = '中雨'
            elif rainfall > 2:
                weather_type = '小雨'
            elif np.random.random() < 0.3:
                weather_type = '多云'

            warnings = []
            has_frost = (month in [12, 1, 2, 3]) and temp < 2
            if has_frost:
                warnings.append('霜冻')

            if rainfall > 20:
                warnings.append('洪涝')

            if temp > 38:
                warnings.append('高温')

            if temp < -5:
                warnings.append('低温冻害')

            is_disaster = len(warnings) > 0
            warning_text = ';'.join(warnings) if warnings else ''

            records.append({
                'date': date.strftime('%Y-%m-%d'),
                'location': location,
                'temperature': round(temp, 1),
                'rainfall_mm': round(rainfall, 1),
                'weather_type': weather_type,
                'has_warning': is_disaster,
                'warning_type': warning_text
            })

    df = pd.DataFrame(records)
    df.to_csv('data/weather_data.csv', index=False, encoding='utf-8-sig')
    print(f'Generated {len(df)} weather records')
    return df


if __name__ == '__main__':
    print('Generating simulated data...')
    generate_tea_data()
    generate_weather_data()
    print('Data generation complete!')
