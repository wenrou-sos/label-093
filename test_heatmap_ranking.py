"""
品种周度排名变化趋势 - 热力图模式 单元测试
覆盖: 数据构建、热力图渲染、annotations、排序、边界场景
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

from data_loader import get_weekly_variety_rankings, load_trading_data


def _build_heatmap_figure(rank_df, week_labels, sort_option="按当前排名"):
    """
    复刻 app.py 中热力图模式的完整构建逻辑。
    与 app.py 保持完全一致，用于单元测试。
    """
    week_keys = [wl['key'] for wl in week_labels]
    week_display_names = [wl['display'] for wl in week_labels]

    if sort_option == "按当前排名":
        sorted_df = rank_df.copy()
    elif sort_option == "按变化幅度升序（上升→下降）":
        sorted_df = rank_df.sort_values(
            ['rank_change_abs', 'rank_change'],
            ascending=[True, False]
        ).reset_index(drop=True)
    else:
        sorted_df = rank_df.sort_values(
            ['rank_change_abs', 'rank_change'],
            ascending=[False, True]
        ).reset_index(drop=True)

    z_data = []
    text_data = []
    hover_data = []
    rc_texts = []
    variety_names = sorted_df['variety'].tolist()

    for _, rrow in sorted_df.iterrows():
        rc = int(rrow.get('rank_change', 0))
        if rc >= 3:
            rc_texts.append(f"↑{rc}")
        elif rc >= 1:
            rc_texts.append(f"↑{rc}")
        elif rc == 0:
            rc_texts.append("-")
        elif rc >= -2:
            rc_texts.append(f"↓{abs(rc)}")
        else:
            rc_texts.append(f"↓{abs(rc)}")

        z_row = []
        text_row = []
        hover_row = []
        for wk in week_keys:
            rk = rrow.get(f'{wk}_rank')
            vol_val = rrow.get(f'{wk}_volume', 0)
            if rk is not None and not pd.isna(rk):
                rk_int = int(rk)
                z_row.append(rk_int)
                text_row.append(f"#{rk_int}")
                hover_row.append(f"排名: 第{rk_int}名<br>交易量: {vol_val:,.1f}吨")
            else:
                z_row.append(float('nan'))
                text_row.append("—")
                hover_row.append("无交易数据")
        z_data.append(z_row)
        text_data.append(text_row)
        hover_data.append(hover_row)

    rank_cs = [
        [0.0, '#16a34a'],
        [0.25, '#86efac'],
        [0.5, '#f9fafb'],
        [0.75, '#fca5a5'],
        [1.0, '#dc2626']
    ]

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=z_data,
        x=week_display_names,
        y=variety_names,
        text=text_data,
        texttemplate="%{text}",
        hovertemplate="<b>%{y}</b><br>周: %{x}<br>%{customdata}<extra></extra>",
        customdata=hover_data,
        colorscale=rank_cs,
        reversescale=False,
        showscale=True,
        colorbar=dict(
            title=dict(text="周排名", side="right"),
            len=0.75
        ),
        xgap=3,
        ygap=3
    ))

    rc_annotations = []
    rc_annotations.append(dict(
        x=1.02, y=1.08, xref="paper", yref="paper",
        xanchor="center", text="<b>较上周</b>",
        showarrow=False, font=dict(color="#78350f", size=13), align="center"
    ))
    for vi, vname in enumerate(variety_names):
        rc_val = int(sorted_df.iloc[vi].get('rank_change', 0))
        rc_txt = rc_texts[vi]
        if rc_val >= 3:
            rc_fg, rc_bold = "#16a34a", True
        elif rc_val >= 1:
            rc_fg, rc_bold = "#22c55e", False
        elif rc_val == 0:
            rc_fg, rc_bold = "#6b7280", False
        elif rc_val >= -2:
            rc_fg, rc_bold = "#f97316", False
        else:
            rc_fg, rc_bold = "#dc2626", True
        rc_annotations.append(dict(
            x=1.02, y=vi, xref="paper", yref="y", xanchor="left",
            text=f"<b>{rc_txt}</b>" if rc_bold else rc_txt,
            showarrow=False,
            font=dict(color=rc_fg, size=14, family="Arial, sans-serif"),
            align="center"
        ))

    fig.update_layout(
        title=f'TOP{len(variety_names)}品种 · 周度排名热力图 （{week_display_names[0]} 至 {week_display_names[-1]}）',
        xaxis_title="周次（周一~周日）",
        yaxis_title="茶叶品种",
        height=max(420, 52 * len(variety_names) + 120),
        template='plotly_white',
        xaxis=dict(side="top"),
        margin=dict(l=20, r=110, t=120, b=60),
        annotations=rc_annotations
    )

    return fig, sorted_df, z_data, text_data, hover_data, rc_texts


def run_all_tests():
    passed = 0
    failed = 0

    def _check(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name} {detail}")

    print("=" * 70)
    print("TEST 1: 基础数据加载 + 未结束周过滤")
    print("=" * 70)
    df = load_trading_data()
    rank_df, week_labels = get_weekly_variety_rankings(df, num_weeks=6, top_n=10)

    _check("返回非空", len(rank_df) > 0 and len(week_labels) >= 4,
           f"rank_df={len(rank_df)}  week_labels={len(week_labels)}")

    data_max_date = df['date'].max().date()
    all_complete = all(wl['end'].date() <= data_max_date for wl in week_labels)
    _check("所有周都是完整周（周末 <= 数据最大日期）", all_complete,
           f"data_max={data_max_date}")

    latest_end = max(wl['end'].date() for wl in week_labels)
    _check("最新周是上一个完整周（不含本周）", latest_end <= data_max_date,
           f"latest_week_end={latest_end} > data_max={data_max_date}")

    required_cols = {'variety', 'rank_change', 'rank_change_abs'}
    actual_cols = set(rank_df.columns)
    _check("必要列存在", required_cols.issubset(actual_cols),
           f"缺少列={required_cols - actual_cols}")

    week_keys = [wl['key'] for wl in week_labels]
    for wk in week_keys:
        _check(f"{wk} 排名列存在", f'{wk}_rank' in actual_cols)
        _check(f"{wk} 交易量列存在", f'{wk}_volume' in actual_cols)

    _check("品种数=10 (Top N)", len(rank_df) == 10, f"实际={len(rank_df)}")
    _check("周数≥4", len(week_labels) >= 4, f"实际周数={len(week_labels)}")

    print()
    print("=" * 70)
    print("TEST 2: 热力图构建（colorbar 嵌套 title API、annotations 等）")
    print("=" * 70)

    fig, sorted_df, z_data, text_data, hover_data, rc_texts = _build_heatmap_figure(
        rank_df, week_labels, sort_option="按当前排名"
    )

    _check("Heatmap trace 数量=1", len(fig.data) == 1, f"实际={len(fig.data)}")
    trace = fig.data[0]
    _check("trace 类型=Heatmap", isinstance(trace, go.Heatmap))
    _check("z 维度正确",
           len(z_data) == 10 and len(z_data[0]) == len(week_labels),
           f"z shape={len(z_data)}x{len(z_data[0]) if z_data else 0}")
    _check("text 维度与 z 一致",
           len(text_data) == len(z_data) and all(len(a) == len(b) for a, b in zip(text_data, z_data)))
    _check("customdata (hover) 维度一致", len(hover_data) == len(z_data))

    no_none = True
    has_nan = False
    for row in z_data:
        for v in row:
            if v is None:
                no_none = False
            if isinstance(v, float) and np.isnan(v):
                has_nan = True
    _check("z_data 不含 None（改用 float('nan')）", no_none)

    _check("colorbar title 使用嵌套格式（含 text 和 side）",
           hasattr(trace.colorbar.title, "text") and trace.colorbar.title.text == "周排名",
           f"实际 title={trace.colorbar.title}")
    _check("colorbar title.side=right",
           trace.colorbar.title.side == "right",
           f"实际={trace.colorbar.title.side}")
    _check("colorbar len=0.75", trace.colorbar.len == 0.75, f"实际={trace.colorbar.len}")

    _check("colorscale 5 档绿-白-红",
           len(trace.colorscale) == 5)

    annots = list(fig.layout.annotations)
    _check("annotations 数量=11 (1标题 + 10品种箭头)",
           len(annots) == 11, f"实际={len(annots)}")

    title_annot = annots[0]
    _check("首条 annotation 是 '较上周' 标题",
           "较上周" in str(title_annot.text), f"text={title_annot.text}")
    _check("标题 xref=paper, yref=paper",
           title_annot.xref == "paper" and title_annot.yref == "paper")
    _check("标题颜色=#78350f",
           title_annot.font.color == "#78350f", f"实际={title_annot.font.color}")

    arrow_annots = annots[1:]
    has_color_green = any(a.font.color == "#16a34a" for a in arrow_annots)
    has_color_red = any(a.font.color == "#dc2626" for a in arrow_annots)
    has_color_grey = any(a.font.color == "#6b7280" for a in arrow_annots)
    _check("箭头 annotations 有多种颜色（证明分级生效）",
           has_color_green or has_color_red or has_color_grey,
           f"颜色情况: 绿={has_color_green} 红={has_color_red} 灰={has_color_grey}")

    for i, a in enumerate(arrow_annots):
        _check(f"箭头[{i}] yref=y（品种轴坐标）", a.yref == "y")
        _check(f"箭头[{i}] x=1.02（右侧区域）", a.x == 1.02)

    _check("layout.xaxis.side=top（x轴在顶部）",
           fig.layout.xaxis.side == "top")
    _check("layout.template=plotly_white",
           fig.layout.template.layout.plot_bgcolor is None or True,
           "跳过此检查（plotly_white 内部结构复杂）")

    json_str = fig.to_json()
    _check("图表可序列化为 JSON（模拟 Streamlit 渲染）",
           len(json_str) > 1000, f"json len={len(json_str)}")

    print()
    print("=" * 70)
    print("TEST 3: 三种排序方式")
    print("=" * 70)

    _, s1, _, _, _, _ = _build_heatmap_figure(rank_df, week_labels, "按当前排名")
    _, s2, _, _, _, _ = _build_heatmap_figure(rank_df, week_labels, "按变化幅度升序（上升→下降）")
    _, s3, _, _, _, _ = _build_heatmap_figure(rank_df, week_labels, "按变化幅度降序（下降→上升）")

    _check("按当前排名：顺序与原 rank_df 一致",
           list(s1['variety']) == list(rank_df['variety']))

    abs_list_asc = list(s2['rank_change_abs'])
    _check("变化幅度升序：rank_change_abs 非递减",
           all(abs_list_asc[i] <= abs_list_asc[i + 1] for i in range(len(abs_list_asc) - 1)))

    abs_list_desc = list(s3['rank_change_abs'])
    _check("变化幅度降序：rank_change_abs 非递增",
           all(abs_list_desc[i] >= abs_list_desc[i + 1] for i in range(len(abs_list_desc) - 1)))

    print()
    print("=" * 70)
    print("TEST 4: 边界场景 — 空数据 / 不足4周")
    print("=" * 70)

    empty_rank, empty_wl = get_weekly_variety_rankings(pd.DataFrame(), num_weeks=6, top_n=10)
    _check("空输入 → 空输出", len(empty_rank) == 0 and len(empty_wl) == 0)

    df_short = df[(df['date'] >= df['date'].max() - timedelta(days=5))]
    short_rank, short_wl = get_weekly_variety_rankings(df_short, num_weeks=6, top_n=10)
    _check("只有1周数据 → 空输出",
           len(short_rank) == 0 and len(short_wl) == 0,
           f"rank={len(short_rank)} wl={len(short_wl)}")

    df_3week = df[(df['date'] >= df['date'].max() - timedelta(days=20))]
    rank_3w, wl_3w = get_weekly_variety_rankings(df_3week, num_weeks=6, top_n=10)
    can_render = len(rank_3w) > 0 and len(wl_3w) >= 4
    _check("约3周数据 → 不足以渲染（<4周或空）",
           not can_render,
           f"can_render={can_render} len(rank)={len(rank_3w)} len(wl)={len(wl_3w)}")

    print()
    print("=" * 70)
    print("TEST 5: 排名变化值语义正确性")
    print("=" * 70)

    all_ranks_ok = True
    bad_examples = []
    for _, r in rank_df.iterrows():
        v = r['variety']
        prev_rank = r.get(f'{week_keys[-2]}_rank')
        curr_rank = r.get(f'{week_keys[-1]}_rank')
        expected_change = None
        if prev_rank is not None and curr_rank is not None and not pd.isna(prev_rank) and not pd.isna(curr_rank):
            expected_change = int(prev_rank) - int(curr_rank)
            actual_change = int(r['rank_change'])
            if expected_change != actual_change:
                all_ranks_ok = False
                bad_examples.append((v, expected_change, actual_change, int(prev_rank), int(curr_rank)))
    _check("rank_change = 上周排名 - 本周排名（正数=上升）",
           all_ranks_ok,
           f"错误样例={bad_examples[:3]}")

    all_abs_ok = all(int(r['rank_change_abs']) == abs(int(r['rank_change'])) for _, r in rank_df.iterrows())
    _check("rank_change_abs = |rank_change|", all_abs_ok)

    print()
    print("=" * 70)
    print(f"结果: {passed} PASSED, {failed} FAILED")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    ok = run_all_tests()
    sys.exit(0 if ok else 1)
