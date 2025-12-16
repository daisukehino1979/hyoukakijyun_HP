import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- Rerun関数の互換性対応 ---
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.write("※画面を更新してください（F5キー）")

# ページ設定
st.set_page_config(page_title="技術評価シミュレーション", layout="wide")
st.markdown("### 技術評価シミュレーション")

# --- サイドバー設定 ---
st.sidebar.header("⚙️ 設定パネル")

# 1. 配点設定
st.sidebar.subheader("💯 配点設定 (各0~100点)")
max_s1 = st.sidebar.number_input("①実績", min_value=0, max_value=100, value=10)
max_s2 = st.sidebar.number_input("②技術提案", min_value=0, max_value=100, value=90)
max_s3 = st.sidebar.number_input("③地域貢献", min_value=0, max_value=100, value=10)
max_s4 = st.sidebar.number_input("④工事費評価", min_value=0, max_value=100, value=90)
max_s5 = st.sidebar.number_input("⑤削減提案", min_value=0, max_value=100, value=25)

# 合計配点の計算
total_max_score = max_s1 + max_s2 + max_s3 + max_s4 + max_s5
st.sidebar.caption(f"現在の合計配点: **{total_max_score}点**")

st.sidebar.markdown("---")

# 2. 目標価格の設定
st.sidebar.subheader("💰 工事費評価基準")
target_price = st.sidebar.number_input("目標価格（億円）", value=420.0, step=1.0, format="%.1f")
full_score_price = target_price * 0.8
st.sidebar.info(f"満点基準額: {full_score_price:.1f} 億円\n\n(目標価格の80%)\n※Tab1で使用")


# --- データ初期化関数 ---
def get_initial_data():
    return pd.DataFrame({
        "会社名": ["A社", "B社", "C社"],
        "①実績":      [max_s1, max_s1 * 0.8, max_s1 * 0.6], 
        "②技術提案":  [max_s2 * 0.94, max_s2 * 0.77, max_s2 * 0.61], 
        "③地域貢献":  [max_s3, max_s3 * 0.8, max_s3 * 0.6],
        "入札価格":   [420.0, 380.0, 340.0],
        "④工事費評価": [0.0, 0.0, 0.0], 
        "⑤削減提案":   [max_s5, max_s5, max_s5],
        "合計点":     [0.0, 0.0, 0.0]
    })

# Session Stateの初期化
if "df_tab1_v3" not in st.session_state:
    st.session_state.df_tab1_v3 = get_initial_data()
if "df_tab2_v3" not in st.session_state:
    st.session_state.df_tab2_v3 = get_initial_data()

# --- 共通の列設定生成関数 ---
def get_column_config():
    return {
        "会社名": st.column_config.TextColumn("会社名", help="クリックして編集可能"),
        
        "①実績": st.column_config.NumberColumn(
            "①実績", help=f"配点: {max_s1}点満点", 
            min_value=0.0, max_value=float(max_s1), step=0.1, format="%.1f"
        ),
        "②技術提案": st.column_config.NumberColumn(
            "②技術提案", help=f"配点: {max_s2}点満点", 
            min_value=0.0, max_value=float(max_s2), step=0.1, format="%.1f"
        ),
        "③地域貢献": st.column_config.NumberColumn(
            "③地域貢献", help=f"配点: {max_s3}点満点", 
            min_value=0.0, max_value=float(max_s3), step=0.1, format="%.1f"
        ),
        "入札価格": st.column_config.NumberColumn(
            "④入札価格", help="単位: 億円", 
            min_value=0.0, step=0.1, format="%.1f"
        ),
        "④工事費評価": st.column_config.NumberColumn(
            "④価格点", help=f"配点: {max_s4}点満点（自動計算）", 
            disabled=True, format="%.1f"
        ),
        "⑤削減提案": st.column_config.NumberColumn(
            "⑤削減提案", help=f"配点: {max_s5}点満点", 
            min_value=0.0, max_value=float(max_s5), step=0.1, format="%.1f"
        ),
        "合計点": st.column_config.NumberColumn(
            "合計点", disabled=True, format="%.1f"
        ),
    }

# --- タブの作成 ---
tab1, tab2 = st.tabs(["① 標準モデル (直線減点)", "② 別案モデル (最低入札価格基準)"])


# ==========================================
#  Tab 1: 標準モデル (直線減点方式に変更)
# ==========================================
with tab1:
    st.subheader("📝 標準モデル：直線減点方式")
    st.caption(f"計算式： 基準額({full_score_price:.1f}億)以下は満点、目標額({target_price:.1f}億)以上は0点。その間は比例配分。")

    # データエディタ
    edited_df_t1 = st.data_editor(
        st.session_state.df_tab1_v3,
        column_config=get_column_config(),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="editor_tab1"
    )

    # --- Tab1 計算ロジック (変更箇所) ---
    def calc_standard(row):
        price = row["入札価格"]
        
        # 1. 満点基準額以下の場合 -> 満点
        if price <= full_score_price:
            s4 = float(max_s4)
        
        # 2. 目標価格以上の場合 -> 0点
        elif price >= target_price:
            s4 = 0.0
            
        # 3. その間の場合 -> 直線補間で点数を算出
        # (目標価格 - 入札価格) / (目標価格 - 満点基準額) * 満点
        else:
            range_width = target_price - full_score_price # 価格差の幅（20%部分）
            price_diff = target_price - price             # 目標価格まであといくらか
            s4 = (price_diff / range_width) * float(max_s4)

        # 合計計算
        total = row["①実績"] + row["②技術提案"] + row["③地域貢献"] + s4 + row["⑤削減提案"]
        return pd.Series([s4, total])

    # 計算実行
    if not edited_df_t1.empty:
        if "入札価格" in edited_df_t1.columns:
            edited_df_t1[["④工事費評価", "合計点"]] = edited_df_t1.apply(calc_standard, axis=1)

    # 保存とリロード
    if not edited_df_t1.equals(st.session_state.df_tab1_v3):
        st.session_state.df_tab1_v3 = edited_df_t1
        safe_rerun()

    # 結果表示
    if not edited_df_t1.empty and "合計点" in edited_df_t1.columns:
        win_t1 = edited_df_t1.loc[edited_df_t1["合計点"].idxmax(), "会社名"]
        score_t1 = edited_df_t1["合計点"].max()
        st.info(f"🏆 Tab1 最高評価: **{win_t1}** （{score_t1:.1f} 点）")

        # グラフ表示
        items = ["①実績", "②技術提案", "③地域貢献", "④工事費評価", "⑤削減提案"]
        colors = px.colors.qualitative.Pastel
        fig1 = go.Figure()
        for i, item in enumerate(items):
            if item in edited_df_t1.columns:
                fig1.add_trace(go.Bar(
                    name=item, x=edited_df_t1["会社名"], y=edited_df_t1[item],
                    text=edited_df_t1[item], texttemplate='%{text:.1f}', textposition='inside',
                    marker_color=colors[i % len(colors)]
                ))
        
        fig1.update_layout(
            barmode='stack', title="【標準】評価スコア構成",
            yaxis_title="獲得スコア", 
            yaxis_range=[0, total_max_score * 1.1],
            height=1000,
            bargap=0.6
        )
        st.plotly_chart(fig1, use_container_width=True)


# ==========================================
#  Tab 2: 別案モデル
# ==========================================
with tab2:
    st.subheader("📝 別案モデル：最低入札価格基準")
    st.caption(f"計算式： 最低入札価格 ÷ 各社の入札価格 × {max_s4}点 (配点)")

    # データエディタ
    edited_df_t2 = st.data_editor(
        st.session_state.df_tab2_v3,
        column_config=get_column_config(),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="editor_tab2"
    )

    # --- Tab2 計算ロジック ---
    if not edited_df_t2.empty and "入札価格" in edited_df_t2.columns:
        valid_prices = edited_df_t2[edited_df_t2["入札価格"] > 0]["入札価格"]
        
        if not valid_prices.empty:
            min_price = valid_prices.min()
            st.info(f"ℹ️ 現在の最低入札価格: **{min_price:.1f} 億円** （基準値）")
        else:
            min_price = 0

        def calc_min_ratio(row):
            price = row["入札価格"]
            if price > 0 and min_price > 0:
                s4 = (min_price / price) * float(max_s4)
            else:
                s4 = 0.0  
            total = row["①実績"] + row["②技術提案"] + row["③地域貢献"] + s4 + row["⑤削減提案"]
            return pd.Series([s4, total])

        edited_df_t2[["④工事費評価", "合計点"]] = edited_df_t2.apply(calc_min_ratio, axis=1)

    # 保存とリロード
    if not edited_df_t2.equals(st.session_state.df_tab2_v3):
        st.session_state.df_tab2_v3 = edited_df_t2
        safe_rerun()

    # 結果表示
    if not edited_df_t2.empty and "合計点" in edited_df_t2.columns:
        win_t2 = edited_df_t2.loc[edited_df_t2["合計点"].idxmax(), "会社名"]
        score_t2 = edited_df_t2["合計点"].max()
        st.info(f"🏆 Tab2 最高評価: **{win_t2}** （{score_t2:.1f} 点）")

        # グラフ表示
        fig2 = go.Figure()
        items = ["①実績", "②技術提案", "③地域貢献", "④工事費評価", "⑤削減提案"]
        for i, item in enumerate(items):
            if item in edited_df_t2.columns:
                fig2.add_trace(go.Bar(
                    name=item, x=edited_df_t2["会社名"], y=edited_df_t2[item],
                    text=edited_df_t2[item], texttemplate='%{text:.1f}', textposition='inside',
                    marker_color=colors[i % len(colors)]
                ))
        
        fig2.update_layout(
            barmode='stack', title="【別案】評価スコア構成",
            yaxis_title="獲得スコア", 
            yaxis_range=[0, total_max_score * 1.1],
            height=1000,
            bargap=0.6
        )
        st.plotly_chart(fig2, use_container_width=True)