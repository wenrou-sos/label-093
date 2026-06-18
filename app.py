import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from data_loader import (
    load_trading_data,
    load_weather_data,
    get_market_summary,
    get_variety_summary,
    get_price_trend,
    detect_price_anomalies,
    calculate_kline_data,
    get_season_ranges,
    get_season_ranges_for_years,
    get_years_in_range,
    compare_mingqian_yuqian,
    get_weather_warnings,
    get_market_volume_distribution,
    get_daily_summary
)

st.set_page_config(
    page_title="全国茶叶批发市场价格与交易量分析看板",
    page_icon="🍵",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        background-color: #fafaf9;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    h1, h2, h3 {
        color: #78350f;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #fff7ed;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #92400e;
        color: white !important;
    }
    div[data-testid="stSidebar"] {
        background-color: #fff7ed;
    }
    .weather-alert {
        background-color: #fef2f2;
        border-left: 4px solid #dc2626;
        padding: 10px 15px;
        border-radius: 4px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def load_data():
    trading_df = load_trading_data()
    weather_df = load_weather_data()
    return trading_df, weather_df


trading_df, weather_df = load_data()

with st.sidebar:
    st.title("🍵 茶叶市场分析")
    st.markdown("---")

    all_varieties = sorted(trading_df['variety'].unique())
    selected_variety = st.selectbox(
        "选择茶叶品种",
        all_varieties,
        index=all_varieties.index('龙井') if '龙井' in all_varieties else 0
    )

    all_markets = ['全部'] + sorted(trading_df['market'].unique())
    selected_market = st.selectbox("选择交易市场", all_markets)

    date_range = st.date_input(
        "选择日期范围",
        value=[trading_df['date'].max() - timedelta(days=90), trading_df['date'].max()],
        min_value=trading_df['date'].min(),
        max_value=trading_df['date'].max()
    )

    st.markdown("---")
    st.caption(f"数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if selected_market != '全部':
    trading_filtered = trading_df[trading_df['market'] == selected_market]
else:
    trading_filtered = trading_df.copy()

if len(date_range) == 2:
    start_date = pd.Timestamp(date_range[0])
    end_date = pd.Timestamp(date_range[1])
    trading_filtered = trading_filtered[
        (trading_filtered['date'] >= start_date) &
        (trading_filtered['date'] <= end_date)
    ]

st.title("🍵 全国茶叶批发市场价格与交易量分析看板")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_volume = trading_filtered['volume_ton'].sum()
    st.metric(
        label="📊 总交易量",
        value=f"{total_volume:,.1f} 吨",
        delta=f"{total_volume * 0.05:,.1f} 吨"
    )

with col2:
    avg_price = trading_filtered['price_yuan_per_jin'].mean()
    st.metric(
        label="💰 平均价格",
        value=f"{avg_price:,.1f} 元/斤",
        delta=f"{avg_price * 0.02:,.1f} 元"
    )

with col3:
    num_varieties = trading_filtered['variety'].nunique()
    st.metric(
        label="🍃 交易品种",
        value=f"{num_varieties} 种"
    )

with col4:
    num_markets = trading_filtered['market'].nunique()
    st.metric(
        label="🏪 参与市场",
        value=f"{num_markets} 个"
    )

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 价格趋势分析",
    "🏪 市场分布",
    "🌸 明前/雨前对比",
    "🌤️ 天气影响分析",
    "📊 数据总览"
])

with tab1:
    st.header(f"{selected_variety} - 价格趋势分析")

    period_options = {"近30天": 30, "近90天": 90, "近一年": 365}
    selected_period = st.radio(
        "选择时间周期",
        options=list(period_options.keys()),
        horizontal=True
    )

    days = period_options[selected_period]

    col_kline, col_info = st.columns([3, 1])

    with col_kline:
        kline_df = calculate_kline_data(
            trading_filtered, selected_variety,
            days=days, start_date=start_date, end_date=end_date
        )
        if len(kline_df) > 0:
            fig_kline = go.Figure()

            fig_kline.add_trace(go.Candlestick(
                x=kline_df['date'],
                open=kline_df['open'],
                high=kline_df['high'],
                low=kline_df['low'],
                close=kline_df['close'],
                name='价格K线',
                increasing_line_color='#10b981',
                decreasing_line_color='#ef4444'
            ))

            anomalies = detect_price_anomalies(trading_filtered, selected_variety)
            if len(anomalies) > 0:
                kline_start = kline_df['date'].min()
                kline_end = kline_df['date'].max()
                period_anomalies = anomalies[
                    (anomalies['date'] >= kline_start) &
                    (anomalies['date'] <= kline_end)
                ]

                if len(period_anomalies) > 0:
                    for _, row in period_anomalies.iterrows():
                        color = '#ef4444' if row['change_direction'] == '上涨' else '#10b981'
                        fig_kline.add_trace(go.Scatter(
                            x=[row['date']],
                            y=[row['price_yuan_per_jin']],
                            mode='markers',
                            marker=dict(
                                symbol='star',
                                size=15,
                                color=color,
                                line=dict(width=2, color='white')
                            ),
                            name=f"{'⚠️ 异常' if row['change_direction'] == '上涨' else '⚠️ 异常'}",
                            hovertemplate=f"日期: {row['date'].strftime('%Y-%m-%d')}<br>价格: {row['price_yuan_per_jin']:.1f} 元/斤<br>波动: {row['pct_change']*100:.1f}%",
                            showlegend=False
                        ))

            current_year = trading_df['date'].max().year
            if len(kline_df) > 0:
                kline_min_date = kline_df['date'].min()
                kline_max_date = kline_df['date'].max()
                years_in_range = get_years_in_range(kline_min_date, kline_max_date)
                all_seasons = get_season_ranges_for_years(years_in_range)

                for season_info in all_seasons:
                    try:
                        season_start = season_info['start']
                        season_end = season_info['end']
                        season_name = season_info['season']
                        year_label = season_info['year']
                        if season_end >= kline_min_date and season_start <= kline_max_date:
                            label = f"{year_label} {season_name}" if len(years_in_range) > 1 else season_name
                            fig_kline.add_vrect(
                                x0=season_start,
                                x1=season_end,
                                fillcolor=season_info['color'],
                                opacity=0.1,
                                layer="below",
                                line_width=0,
                                annotation_text=label,
                                annotation_position="top left",
                                annotation_font_color=season_info['color'],
                                annotation_font_size=10
                            )
                    except (ValueError, TypeError):
                        pass

            fig_kline.update_layout(
                title=f'{selected_variety} 价格K线图 ({selected_period})',
                yaxis_title='价格 (元/斤)',
                xaxis_title='日期',
                height=500,
                template='plotly_white',
                xaxis_rangeslider_visible=False,
                hovermode='x unified'
            )

            st.plotly_chart(fig_kline, width='stretch')

    with col_info:
        st.subheader("异常波动预警")
        anomalies = detect_price_anomalies(trading_filtered, selected_variety)
        if len(anomalies) > 0:
            latest = anomalies.sort_values('date', ascending=False).head(5)
            for _, row in latest.iterrows():
                icon = "📈" if row['change_direction'] == '上涨' else "📉"
                st.markdown(f"""
                <div class="weather-alert">
                    <strong>{icon} {row['date'].strftime('%Y-%m-%d')}</strong><br>
                    {selected_variety} {row['change_direction']} {row['abs_pct_change']*100:.1f}%<br>
                    价格: {row['price_yuan_per_jin']:.1f} 元/斤
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ 近期无异常价格波动")

        st.markdown("---")
        trend_30 = get_price_trend(
            trading_filtered, selected_variety, days=30,
            start_date=start_date, end_date=end_date
        )
        if len(trend_30) >= 2:
            price_change = (trend_30.iloc[-1]['price_yuan_per_jin'] - trend_30.iloc[0]['price_yuan_per_jin']) / trend_30.iloc[0]['price_yuan_per_jin'] * 100
            st.metric(
                label="30天价格变动",
                value=f"{price_change:+.1f}%",
                delta=f"{'上涨' if price_change > 0 else '下跌'}"
            )

    st.markdown("---")
    st.subheader("多品种价格对比")
    compare_varieties = st.multiselect(
        "选择对比品种",
        all_varieties,
        default=['龙井', '大红袍', '铁观音', '普洱', '金骏眉']
    )

    if compare_varieties:
        fig_compare = go.Figure()
        for variety in compare_varieties:
            trend = get_price_trend(
                trading_filtered, variety, days=days,
                start_date=start_date, end_date=end_date
            )
            if len(trend) > 0:
                fig_compare.add_trace(go.Scatter(
                    x=trend['date'],
                    y=trend['price_yuan_per_jin'],
                    mode='lines',
                    name=variety,
                    line=dict(width=2)
                ))

        fig_compare.update_layout(
            title='多品种价格走势对比',
            yaxis_title='价格 (元/斤)',
            xaxis_title='日期',
            height=400,
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode='x unified'
        )
        st.plotly_chart(fig_compare, width='stretch')

with tab2:
    st.header("市场分布可视化")

    col_pie, col_bar = st.columns(2)

    with col_pie:
        volume_dist = get_market_volume_distribution(trading_filtered, start_date, end_date)
        colors = ['#92400e', '#b45309', '#d97706', '#f59e0b', '#fbbf24']
        fig_pie = go.Figure(data=[go.Pie(
            labels=volume_dist['market'],
            values=volume_dist['volume_ton'],
            hole=0.4,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textfont=dict(size=12),
            hovertemplate="市场: %{label}<br>交易量: %{value:,.1f} 吨<br>占比: %{percent}"
        )])
        fig_pie.update_layout(
            title='各产区交易量占比',
            height=450,
            template='plotly_white'
        )
        st.plotly_chart(fig_pie, width='stretch')

    with col_bar:
        market_sum = get_market_summary(trading_filtered)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=market_sum['market'],
            y=market_sum['total_volume_ton'],
            name='交易量 (吨)',
            marker_color='#92400e',
            yaxis='y',
            hovertemplate="市场: %{x}<br>交易量: %{y:,.1f} 吨"
        ))
        fig_bar.add_trace(go.Scatter(
            x=market_sum['market'],
            y=market_sum['avg_price'],
            name='平均价格 (元/斤)',
            mode='lines+markers',
            line=dict(color='#f59e0b', width=3),
            marker=dict(size=8),
            yaxis='y2',
            hovertemplate="市场: %{x}<br>平均价格: %{y:,.1f} 元/斤"
        ))
        fig_bar.update_layout(
            title='各市场交易量与平均价格',
            yaxis=dict(title='交易量 (吨)'),
            yaxis2=dict(title='平均价格 (元/斤)', overlaying='y', side='right'),
            height=450,
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar, width='stretch')

    st.markdown("---")
    st.subheader("各品种交易量排行")
    variety_sum = get_variety_summary(trading_filtered)
    fig_variety = px.bar(
        variety_sum.head(15),
        x='variety',
        y='total_volume_ton',
        color='avg_price',
        color_continuous_scale='YlOrBr',
        labels={'variety': '茶叶品种', 'total_volume_ton': '交易量 (吨)', 'avg_price': '平均价格 (元/斤)'},
        title='交易量TOP15品种'
    )
    fig_variety.update_layout(
        height=450,
        template='plotly_white',
        coloraxis_colorbar=dict(title="均价(元/斤)")
    )
    st.plotly_chart(fig_variety, width='stretch')

    st.markdown("---")
    st.subheader("茶叶上市时间轴")
    season_ranges = get_season_ranges()
    timeline_min = start_date
    timeline_max = end_date
    timeline_years = get_years_in_range(timeline_min, timeline_max)
    timeline_all_seasons = get_season_ranges_for_years(timeline_years)

    fig_timeline = go.Figure()
    for season_info in timeline_all_seasons:
        try:
            start_dt = season_info['start']
            end_dt = season_info['end']
            year = season_info['year']
            season_name = season_info['season']

            display_start = max(start_dt, pd.Timestamp(timeline_min))
            display_end = min(end_dt, pd.Timestamp(timeline_max))

            if display_end >= display_start:
                label = f"{year}年{season_name}" if len(timeline_years) > 1 else season_name
                y_label = f"{year} {season_name}" if len(timeline_years) > 1 else season_name
                fig_timeline.add_trace(go.Scatter(
                    x=[display_start, display_end],
                    y=[y_label, y_label],
                    mode='lines',
                    line=dict(color=season_info['color'], width=15),
                    name=label,
                    hovertemplate=f"{year}年{season_name}: {start_dt.strftime('%m月%d日')} - {end_dt.strftime('%m月%d日')}",
                    showlegend=(len(timeline_years) <= 1)
                ))
        except (ValueError, TypeError):
            pass

    xaxis_range = [pd.Timestamp(timeline_min) - pd.Timedelta(days=3), pd.Timestamp(timeline_max) + pd.Timedelta(days=3)]

    fig_timeline.update_layout(
        title=f'春茶/夏茶/秋茶上市时间区间 ({timeline_min.strftime("%Y-%m-%d")} 至 {timeline_max.strftime("%Y-%m-%d")})',
        xaxis_title='时间',
        xaxis_range=xaxis_range,
        yaxis_title='茶季',
        height=max(300, 50 * len(timeline_years) * 3),
        template='plotly_white',
        showlegend=True,
        yaxis=dict(showgrid=False, autorange='reversed' if len(timeline_all_seasons) > 6 else None),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='#f3f4f6')
    )
    st.plotly_chart(fig_timeline, width='stretch')

with tab3:
    st.header("明前茶 vs 雨前茶 价格对比分析")

    col_select, _ = st.columns([1, 3])
    with col_select:
        compare_variety = st.selectbox(
            "选择对比品种",
            ['全部'] + all_varieties,
            key='compare_variety_select'
        )

    if compare_variety == '全部':
        variety_filter = None
    else:
        variety_filter = compare_variety

    comparison = compare_mingqian_yuqian(trading_filtered, variety_filter)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="🌱 明前茶平均价格",
            value=f"{comparison['mingqian_avg_price']:,.1f} 元/斤"
        )

    with col2:
        st.metric(
            label="🌿 雨前茶平均价格",
            value=f"{comparison['yuqian_avg_price']:,.1f} 元/斤"
        )

    with col3:
        st.metric(
            label="📊 价格差异",
            value=f"{comparison['price_diff_pct']:+.1f}%",
            delta="明前比雨前"
        )

    st.markdown("---")

    col_bar_compare, col_detail = st.columns([2, 1])

    with col_bar_compare:
        fig_compare_bar = go.Figure()

        categories = ['明前茶', '雨前茶']
        prices = [comparison['mingqian_avg_price'], comparison['yuqian_avg_price']]
        volumes = [comparison['mingqian_total_volume'], comparison['yuqian_total_volume']]

        fig_compare_bar.add_trace(go.Bar(
            x=categories,
            y=prices,
            name='平均价格 (元/斤)',
            marker_color=['#22c55e', '#84cc16'],
            text=[f"¥{p:,.1f}" for p in prices],
            textposition='auto',
            yaxis='y'
        ))

        fig_compare_bar.add_trace(go.Bar(
            x=categories,
            y=volumes,
            name='交易量 (吨)',
            marker_color=['#f59e0b', '#d97706'],
            text=[f"{v:,.1f} 吨" for v in volumes],
            textposition='auto',
            yaxis='y2'
        ))

        fig_compare_bar.update_layout(
            title=f'{compare_variety if compare_variety != "全部" else "全部品种"} - 明前茶 vs 雨前茶对比',
            yaxis=dict(title='平均价格 (元/斤)'),
            yaxis2=dict(title='交易量 (吨)', overlaying='y', side='right'),
            height=450,
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            barmode='group'
        )
        st.plotly_chart(fig_compare_bar, width='stretch')

    with col_detail:
        st.subheader("详细数据")
        st.markdown(f"""
        | 指标 | 明前茶 | 雨前茶 |
        |------|--------|--------|
        | 平均价格 | ¥{comparison['mingqian_avg_price']:,.1f}/斤 | ¥{comparison['yuqian_avg_price']:,.1f}/斤 |
        | 总交易量 | {comparison['mingqian_total_volume']:,.1f} 吨 | {comparison['yuqian_total_volume']:,.1f} 吨 |
        | 记录数 | {comparison['mingqian_count']:,} | {comparison['yuqian_count']:,} |
        """)

        st.markdown("---")
        st.info("""
        💡 **茶叶小知识**

        **明前茶**：清明节前采制的茶叶，芽叶细嫩，香气物质和滋味物质含量丰富，品质最佳。

        **雨前茶**：清明后谷雨前采制的茶叶，芽叶生长较快，滋味稍浓，性价比高。
        """)

    st.markdown("---")
    st.subheader("各品种明前/雨前价格差异对比")

    variety_comparisons = []
    filtered_varieties = sorted(trading_filtered['variety'].unique())
    for v in filtered_varieties:
        comp = compare_mingqian_yuqian(trading_filtered, v)
        if comp['yuqian_avg_price'] > 0 and comp['mingqian_avg_price'] > 0:
            variety_comparisons.append({
                'variety': v,
                'mingqian_price': comp['mingqian_avg_price'],
                'yuqian_price': comp['yuqian_avg_price'],
                'price_diff_pct': comp['price_diff_pct']
            })

    if variety_comparisons:
        df_compare = pd.DataFrame(variety_comparisons)
        df_compare = df_compare.sort_values('price_diff_pct', ascending=True)

        fig_heatmap = go.Figure()

        fig_heatmap.add_trace(go.Bar(
            y=df_compare['variety'],
            x=df_compare['mingqian_price'],
            name='明前茶价格',
            orientation='h',
            marker_color='#22c55e'
        ))

        fig_heatmap.add_trace(go.Bar(
            y=df_compare['variety'],
            x=df_compare['yuqian_price'],
            name='雨前茶价格',
            orientation='h',
            marker_color='#84cc16'
        ))

        fig_heatmap.update_layout(
            title='各品种明前茶与雨前茶价格对比',
            xaxis_title='价格 (元/斤)',
            yaxis_title='茶叶品种',
            height=600,
            template='plotly_white',
            barmode='group',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_heatmap, width='stretch')

with tab4:
    st.header("产区天气影响分析")

    weather_location = st.selectbox(
        "选择产区",
        ['全部'] + sorted(weather_df['location'].unique())
    )

    col_temp, col_rain, col_warning = st.columns(3)

    weather_filtered = weather_df.copy()
    if weather_location != '全部':
        weather_filtered = weather_filtered[weather_filtered['location'] == weather_location]

    weather_range = weather_filtered[
        (weather_filtered['date'] >= start_date) &
        (weather_filtered['date'] <= end_date)
    ]

    with col_temp:
        avg_temp = weather_range['temperature'].mean()
        st.metric(
            label="🌡️ 平均气温",
            value=f"{avg_temp:.1f} °C"
        )

    with col_rain:
        total_rain = weather_range['rainfall_mm'].sum()
        st.metric(
            label="🌧️ 累计降雨量",
            value=f"{total_rain:.1f} mm"
        )

    with col_warning:
        warning_count = weather_range['has_warning'].sum()
        st.metric(
            label="⚠️ 天气预警次数",
            value=f"{warning_count} 次"
        )

    st.markdown("---")

    col_weather_chart, col_alerts = st.columns([3, 1])

    with col_weather_chart:
        weather_daily = weather_range.groupby('date').agg({
            'temperature': 'mean',
            'rainfall_mm': 'sum'
        }).reset_index()

        fig_weather = go.Figure()

        fig_weather.add_trace(go.Scatter(
            x=weather_daily['date'],
            y=weather_daily['temperature'],
            mode='lines',
            name='平均气温 (°C)',
            line=dict(color='#ef4444', width=2),
            yaxis='y'
        ))

        fig_weather.add_trace(go.Bar(
            x=weather_daily['date'],
            y=weather_daily['rainfall_mm'],
            name='降雨量 (mm)',
            marker_color='#3b82f6',
            opacity=0.6,
            yaxis='y2'
        ))

        warnings = get_weather_warnings(weather_filtered, start_date=start_date, end_date=end_date)
        if len(warnings) > 0:
            warn_dates = warnings.groupby('date')['warning_type'].apply(lambda x: ';'.join(set(x))).reset_index()
            for _, row in warn_dates.iterrows():
                avg_temp_day = weather_daily[weather_daily['date'] == row['date']]['temperature'].values
                temp_y = avg_temp_day[0] if len(avg_temp_day) > 0 else 25
                fig_weather.add_trace(go.Scatter(
                    x=[row['date']],
                    y=[temp_y],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-up',
                        size=14,
                        color='#dc2626',
                        line=dict(width=2, color='white')
                    ),
                    name=f"⚠️ {row['warning_type']}",
                    hovertemplate=f"日期: {row['date'].strftime('%Y-%m-%d')}<br>预警: {row['warning_type']}",
                    showlegend=False
                ))

        fig_weather.update_layout(
            title=f'{weather_location if weather_location != "全部" else "全部产区"} - 天气趋势',
            yaxis=dict(title='气温 (°C)'),
            yaxis2=dict(title='降雨量 (mm)', overlaying='y', side='right'),
            height=450,
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode='x unified'
        )
        st.plotly_chart(fig_weather, width='stretch')

    with col_alerts:
        st.subheader("近期天气预警")
        recent_warnings = warnings.sort_values('date', ascending=False).head(10)
        if len(recent_warnings) > 0:
            for _, row in recent_warnings.iterrows():
                icons_map = {
                    '霜冻': '🧊',
                    '洪涝': '🌊',
                    '高温': '🔥',
                    '低温冻害': '❄️'
                }
                warn_types = row['warning_type'].split(';') if row['warning_type'] else []
                icon_str = ''.join([icons_map.get(w, '⚠️') for w in warn_types])
                st.markdown(f"""
                <div class="weather-alert">
                    <strong>{icon_str} {row['date'].strftime('%Y-%m-%d')}</strong><br>
                    产区: {row['location']}<br>
                    预警: {row['warning_type']}<br>
                    气温: {row['temperature']}°C | 降雨: {row['rainfall_mm']}mm
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ 近期无灾害性天气预警")

    st.markdown("---")
    st.subheader("各产区天气预警统计")
    warning_stats = weather_filtered[weather_filtered['has_warning'] == True].groupby(['location', 'warning_type']).size().reset_index(name='count')

    if len(warning_stats) > 0:
        fig_warn = px.sunburst(
            warning_stats,
            path=['location', 'warning_type'],
            values='count',
            color='count',
            color_continuous_scale='Reds',
            title='各产区天气预警分布'
        )
        fig_warn.update_layout(height=500)
        st.plotly_chart(fig_warn, width='stretch')

    st.markdown("---")
    st.info("""
    🌱 **天气对茶叶的影响说明**

    - **霜冻/低温冻害**：可能冻伤茶树新芽，严重影响春茶产量和品质
    - **暴雨/洪涝**：可能导致茶树根系受损，影响茶叶生长
    - **持续高温**：加速茶叶老化，影响茶叶口感和香气
    """)

with tab5:
    st.header("📊 数据总览")

    st.subheader("整体交易趋势")
    daily_sum = get_daily_summary(trading_filtered)

    fig_overall = go.Figure()

    fig_overall.add_trace(go.Scatter(
        x=daily_sum['date'],
        y=daily_sum['price_yuan_per_jin'],
        mode='lines',
        name='平均价格 (元/斤)',
        line=dict(color='#92400e', width=2),
        yaxis='y'
    ))

    fig_overall.add_trace(go.Bar(
        x=daily_sum['date'],
        y=daily_sum['volume_ton'],
        name='交易量 (吨)',
        marker_color='#d97706',
        opacity=0.5,
        yaxis='y2'
    ))

    fig_overall.update_layout(
        title='全国茶叶市场日均价格与交易量趋势',
        yaxis=dict(title='平均价格 (元/斤)'),
        yaxis2=dict(title='交易量 (吨)', overlaying='y', side='right'),
        height=450,
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode='x unified'
    )
    st.plotly_chart(fig_overall, width='stretch')

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("交易数据明细")
        display_df = trading_filtered[
            ['date', 'market', 'province', 'variety', 'volume_ton', 'price_yuan_per_jin']
        ].copy()
        display_df.columns = ['日期', '交易市场', '省份', '茶叶品种', '交易量(吨)', '价格(元/斤)']
        display_df['日期'] = display_df['日期'].dt.strftime('%Y-%m-%d')

        st.dataframe(
            display_df.sort_values('日期', ascending=False).head(100),
            width='stretch',
            hide_index=True
        )

    with col2:
        st.subheader("市场统计汇总")
        market_summary = get_market_summary(trading_filtered)
        market_summary.columns = ['交易市场', '总交易量(吨)', '平均价格(元/斤)']
        st.dataframe(
            market_summary,
            width='stretch',
            hide_index=True
        )

        st.markdown("---")
        st.subheader("品种统计汇总")
        variety_summary = get_variety_summary(trading_filtered)
        variety_summary.columns = ['茶叶品种', '总交易量(吨)', '平均价格(元/斤)']
        st.dataframe(
            variety_summary.head(20),
            width='stretch',
            hide_index=True
        )

st.markdown("---")
st.caption("🍵 全国茶叶批发市场价格与交易量分析看板 | 数据仅供参考")
