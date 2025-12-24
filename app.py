import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="UK Climate Co-Benefits", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")

# --- CSS CUSTOM BIAR LEBIH CANTIK ---
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
    h1, h2, h3 { color: #00CC96 !important; }
</style>
""", unsafe_allow_html=True)

# --- JUDUL & STORY ---
st.title("🌱 Moving Better, Living Longer")
st.markdown("""
**The Hidden Wealth of UK Climate Action.**
Dashboard ini tidak hanya menampilkan angka, tetapi menceritakan dampak transisi Net Zero terhadap **Kualitas Hidup** manusia.
""")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    # ... (KODE BARU - Hapus base_path)
    df1 = pd.read_parquet("optimized_level_1.parquet")
    df2 = pd.read_parquet("optimized_level_2.parquet")
    try:
        df3 = pd.read_parquet("optimized_level_3.parquet")
    except:
        df3 = pd.DataFrame() 

    # Langsung baca file karena nanti filenya satu folder di GitHub
    lookup = pd.read_excel("lookups.xlsx")
    
    # Merge Lookup
    cols_to_use = [c for c in ['small_area', 'local_authority', 'nation', 'population'] if c in lookup.columns]
    df1 = df1.merge(lookup[cols_to_use], on='small_area', how='left')
    
    return df1, df2, df3

# --- MAIN APP ---
try:
    df1, df2, df3 = load_data()
    
    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Filter Data")
    
    # Filter Nation
    all_nations = ["United Kingdom (All)"] + sorted(df1['nation'].dropna().unique().tolist()) if 'nation' in df1.columns else []
    selected_nation = st.sidebar.selectbox("Pilih Negara Bagian:", all_nations)
    
    # Filter Dataset Utama
    main_df = df1[df1['nation'] == selected_nation] if selected_nation != "United Kingdom (All)" else df1

    # Filter Benefit
    exclude = ['sum', 'population', 'households', 'geometry']
    benefit_opts = [c for c in main_df.select_dtypes(include='number').columns if c not in exclude]
    def_idx = benefit_opts.index('physical_activity') if 'physical_activity' in benefit_opts else 0
    selected_benefit = st.sidebar.selectbox("Pilih Manfaat (Co-Benefit):", benefit_opts, index=def_idx)

    # --- ABOUT ---
    with st.sidebar.expander("ℹ️ Sumber & Metodologi"):
        st.caption("Data: UK Co-Benefits Atlas (Univ. of Edinburgh). Model Net Zero 2025-2050. Values in Million GBP (2025 NPV).")
        st.write("**Kelompok 6 - Visualisasi Data**")

    # --- KPI CARDS ---
    total_val = main_df[selected_benefit].sum()
    total_all = main_df['sum'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric(f"💰 Nilai: {selected_benefit.replace('_',' ').title()}", f"£ {total_val:,.0f} Juta")
    c2.metric("🌍 Total Semua Manfaat", f"£ {total_all:,.0f} Juta")
    
    if 'population' in main_df.columns:
        pop_total = main_df['population'].sum()
        if pop_total > 0:
            per_capita = (total_val * 1_000_000) / pop_total 
            c3.metric("👤 Manfaat per Orang", f"£ {per_capita:,.2f}")

    # --- INSIGHT BOX ---
    st.markdown("### 💡 Key Insight")
    if selected_benefit == 'physical_activity':
        st.info(f"**Insight Kesehatan:** Investasi infrastruktur aktif (jalan kaki/sepeda) menghasilkan **£{total_val:,.0f} Juta**. Ini membuktikan bahwa warga yang sehat adalah aset ekonomi terbesar.")
    elif selected_benefit == 'air_quality':
        st.info(f"**Insight Lingkungan:** Udara bersih menyumbang **£{total_val:,.0f} Juta**. Penurunan polusi mengurangi beban biaya NHS secara drastis.")
    elif total_val < 0:
        st.warning(f"**Trade-off:** Kategori ini menunjukkan biaya transisi atau dampak negatif sebesar **£{total_val:,.0f} Juta**. Penting untuk memitigasi dampak ini agar transisi adil.")
    else:
        st.success(f"Kategori ini menyumbang **{(total_val/total_all)*100:.1f}%** dari total manfaat di wilayah terpilih.")

    st.markdown("---")

    # --- TABS VISUALISASI ---
    t1, t2, t3, t4 = st.tabs(["📈 Tren & Ranking", "🥊 Bandingkan Wilayah", "📉 Korelasi Populasi", "❤️ Health Deep Dive"])

    # TAB 1: DASHBOARD UTAMA (Gabungan Tren & Ranking biar hemat tempat)
    with t1:
        col_trend, col_rank = st.columns([3, 2])
        
        with col_trend:
            st.subheader("Tren Pertumbuhan (2025-2050)")
            valid_areas = main_df['small_area'].unique()
            df2_sub = df2[(df2['co_benefit_type'] == selected_benefit) & (df2['small_area'].isin(valid_areas))]
            
            if not df2_sub.empty:
                avail_years = [c for c in df2_sub.columns if c.startswith('20')]
                df_trend = df2_sub.melt(id_vars=["small_area"], value_vars=avail_years, var_name="Tahun", value_name="Nilai")
                df_trend["Nilai"] = df_trend["Nilai"].astype(float)
                trend_agg = df_trend.groupby("Tahun")["Nilai"].sum().reset_index()
                
                fig = px.line(trend_agg, x="Tahun", y="Nilai", markers=True, template="plotly_dark")
                fig.update_traces(line_color='#00CC96', line_width=4)
                st.plotly_chart(fig, use_container_width=True)
        
        with col_rank:
            st.subheader("Top 10 Wilayah")
            if 'local_authority' in main_df.columns:
                city_rank = main_df.groupby('local_authority')[[selected_benefit]].sum().reset_index()
                top10 = city_rank.sort_values(by=selected_benefit, ascending=False).head(10)
                
                fig_bar = px.bar(top10, x=selected_benefit, y='local_authority', orientation='h', template="plotly_dark", color=selected_benefit, color_continuous_scale='Viridis')
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig_bar, use_container_width=True)

    # TAB 2: KOMPARASI WILAYAH (Fitur Baru!)
    with t2:
        st.subheader("⚔️ Head-to-Head: Bandingkan Dua Wilayah")
        st.caption("Pilih dua wilayah untuk membandingkan total manfaat secara langsung.")
        
        c_sel1, c_sel2 = st.columns(2)
        all_locs = sorted(df1['local_authority'].dropna().unique())
        
        with c_sel1:
            loc_a = st.selectbox("Wilayah A", all_locs, index=0)
            val_a = df1[df1['local_authority'] == loc_a][selected_benefit].sum()
            st.metric(f"{loc_a}", f"£ {val_a:,.0f} M")
            
        with c_sel2:
            loc_b = st.selectbox("Wilayah B", all_locs, index=1)
            val_b = df1[df1['local_authority'] == loc_b][selected_benefit].sum()
            st.metric(f"{loc_b}", f"£ {val_b:,.0f} M")
            delta = val_a - val_b
            st.caption(f"Selisih: £ {abs(delta):,.0f} M")

        # Grafik Perbandingan
        comp_df = pd.DataFrame({
            'Wilayah': [loc_a, loc_b],
            'Nilai': [val_a, val_b]
        })
        fig_comp = px.bar(comp_df, x='Wilayah', y='Nilai', color='Wilayah', template="plotly_dark", title=f"Perbandingan {selected_benefit}")
        st.plotly_chart(fig_comp, use_container_width=True)

    # TAB 3: KORELASI POPULASI (Analisis Data)
    with t3:
        st.subheader("Apakah Kota Padat Lebih Untung?")
        st.caption("Scatter plot ini menunjukkan hubungan antara Jumlah Penduduk (X) dan Nilai Manfaat (Y).")
        
        if 'population' in main_df.columns:
            # Agregasi per kota biar titiknya tidak kebanyakan
            scatter_data = main_df.groupby('local_authority').agg({
                'population': 'sum',
                selected_benefit: 'sum',
                'nation': 'first'
            }).reset_index()
            
            fig_scat = px.scatter(
                scatter_data, x='population', y=selected_benefit,
                color='nation', size='population', hover_name='local_authority',
                template="plotly_dark", log_x=True, # Log scale biar rapi
                title=f"Korelasi Populasi vs {selected_benefit}"
            )
            st.plotly_chart(fig_scat, use_container_width=True)
        else:
            st.warning("Data populasi tidak tersedia.")

    # TAB 4: HEALTH DEEP DIVE (Pie Chart)
    with t4:
        st.subheader("Analisis Kesehatan")
        if not df3.empty:
            df3_sub = df3[(df3['co_benefit_type'] == selected_benefit) & (df3['small_area'].isin(valid_areas))]
            if not df3_sub.empty and 'damage_type' in df3_sub.columns:
                health_breakdown = df3_sub.groupby('damage_type')['sum'].sum().reset_index()
                fig_pie = px.pie(health_breakdown, values='sum', names='damage_type', color='damage_type', color_discrete_map={'health':'#EF553B', 'non-health':'#636EFA'}, template="plotly_dark", hole=0.5)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Detail breakdown tidak tersedia.")
        else:
            st.warning("Data Level 3 belum dimuat.")

except Exception as e:
    st.error(f"Error: {e}")
