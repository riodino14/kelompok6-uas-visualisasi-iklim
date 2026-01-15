import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="UK Climate Co-Benefits", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")

# --- CSS CUSTOM ---
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
    .stAlert { background-color: #1E1E1E; border: 1px solid #444; color: white; }
</style>
""", unsafe_allow_html=True)

# --- JUDUL & STORY ---
st.title("🌱 Moving Better, Living Longer")
st.markdown("**The Hidden Wealth of UK Climate Action.**")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    df1 = pd.read_parquet("optimized_level_1.parquet")
    df2 = pd.read_parquet("optimized_level_2.parquet")
    try:
        df3 = pd.read_parquet("optimized_level_3.parquet")
    except:
        df3 = pd.DataFrame() 

    lookup = pd.read_excel("lookups.xlsx")
    cols_to_use = [c for c in ['small_area', 'local_authority', 'nation', 'population'] if c in lookup.columns]
    df1 = df1.merge(lookup[cols_to_use], on='small_area', how='left')
    
    # Tambahkan kolom Per Kapita di df1 agar mudah dianalisis
    # Hindari pembagian dengan nol
    df1['benefit_per_capita'] = df1.apply(lambda row: (row['sum'] * 1_000_000) / row['population'] if row['population'] > 0 else 0, axis=1)
    
    return df1, df2, df3

try:
    df1, df2, df3 = load_data()
    
    # --- SIDEBAR: FILTER UTAMA ---
    st.sidebar.header("⚙️ Filter Data")
    
    # 1. MULTISELECT NATION (Fitur Baru!)
    all_nations = sorted(df1['nation'].dropna().unique().tolist()) if 'nation' in df1.columns else []
    # Default pilih semua jika kosong, atau pilih United Kingdom (All) kalau ada
    selected_nations = st.sidebar.multiselect("Pilih Negara Bagian (Bisa Lebih dari 1):", all_nations, default=all_nations[:1])
    
    if not selected_nations:
        st.sidebar.warning("Mohon pilih setidaknya satu negara bagian.")
        st.stop()

    # Filter Dataframe Utama berdasarkan Multiselect
    main_df = df1[df1['nation'].isin(selected_nations)]

    # 2. SELECT BENEFIT
    exclude = ['sum', 'population', 'households', 'geometry', 'benefit_per_capita']
    benefit_opts = [c for c in main_df.select_dtypes(include='number').columns if c not in exclude]
    def_idx = benefit_opts.index('physical_activity') if 'physical_activity' in benefit_opts else 0
    selected_benefit = st.sidebar.selectbox("Pilih Manfaat (Co-Benefit):", benefit_opts, index=def_idx)

    # --- SIDEBAR: STORY & CTA (Fitur Baru!) ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("📢 Key Takeaway")
    st.sidebar.info("""
    **Kesimpulan:**
    Data menunjukkan bahwa transisi Net Zero memberikan keuntungan ganda: **Pertumbuhan Ekonomi** dan **Peningkatan Kesehatan**.
    
    **Rekomendasi:**
    Prioritaskan kebijakan transportasi aktif (jalan kaki/sepeda) di area padat penduduk untuk memaksimalkan ROI kesehatan.
    """)
    st.sidebar.caption("Data: UK Co-Benefits Atlas | By Kelompok 6")

    # --- KPI CARDS ---
    total_val = main_df[selected_benefit].sum()
    total_all = main_df['sum'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric(f"💰 Nilai Ekonomi: {selected_benefit.replace('_',' ').title()}", f"£ {total_val:,.0f} Juta")
    c2.metric("🌍 Total Semua Manfaat", f"£ {total_all:,.0f} Juta")
    
    if 'population' in main_df.columns:
        pop_total = main_df['population'].sum()
        if pop_total > 0:
            per_capita = (total_val * 1_000_000) / pop_total 
            c3.metric("👤 Manfaat per Orang", f"£ {per_capita:,.2f}")

    # --- INSIGHT BOX ---
    st.markdown("### 💡 Key Insight")
    if selected_benefit == 'physical_activity':
        st.info(f"**Insight Kesehatan:** Investasi infrastruktur aktif menghasilkan **£{total_val:,.0f} Juta**. Ini adalah bukti bahwa desain kota yang ramah pejalan kaki adalah investasi kesehatan publik terbaik.")
    elif selected_benefit == 'air_quality':
        st.info(f"**Insight Lingkungan:** Udara bersih menyumbang **£{total_val:,.0f} Juta**. Pengurangan polusi kendaraan bermotor secara drastis menurunkan biaya perawatan penyakit pernapasan.")
    elif total_val < 0:
        st.warning(f"**Trade-off:** Kategori ini memiliki nilai negatif sebesar **£{total_val:,.0f} Juta**, yang mungkin mencerminkan biaya transisi (misalnya waktu perjalanan yang lebih lama). Kebijakan kompensasi diperlukan di sini.")
    else:
        st.success(f"Kategori ini berkontribusi sebesar **{(total_val/total_all)*100:.1f}%** dari total manfaat di wilayah yang dipilih.")

    st.markdown("---")

    # --- TABS VISUALISASI ---
    t1, t2, t3, t4, t5 = st.tabs(["📈 Tren & Komparasi", "🏆 Peringkat Wilayah", "📉 Korelasi Data", "🥊 Head-to-Head", "❤️ Health Deep Dive"])

    # TAB 1: TREN MULTI-NEGARA (Fitur Baru!)
    with t1:
        st.subheader("Tren Pertumbuhan: Komparasi Antar Negara Bagian")
        st.caption("Grafik ini membandingkan pertumbuhan nilai manfaat dari tahun 2025 hingga 2050 untuk setiap negara bagian yang dipilih.")
        
        # Ambil data level 2, filter berdasarkan small_area milik nation yang dipilih
        valid_areas = main_df['small_area'].unique()
        df2_sub = df2[(df2['co_benefit_type'] == selected_benefit) & (df2['small_area'].isin(valid_areas))]
        
        if not df2_sub.empty:
            # Kita perlu merge balik dengan df1 (atau lookup) untuk tahu Nation dari setiap small_area di df2
            # Agar bisa di-group by Nation
            df2_merged = df2_sub.merge(df1[['small_area', 'nation']], on='small_area', how='left')
            
            avail_years = [c for c in df2_merged.columns if c.startswith('20')]
            df_trend = df2_merged.melt(id_vars=["small_area", "nation"], value_vars=avail_years, var_name="Tahun", value_name="Nilai")
            df_trend["Nilai"] = df_trend["Nilai"].astype(float)
            
            # Group by Tahun DAN Nation (untuk Multi-Line Chart)
            trend_agg = df_trend.groupby(["Tahun", "nation"])["Nilai"].sum().reset_index()
            
            fig = px.line(trend_agg, x="Tahun", y="Nilai", color="nation", markers=True, template="plotly_dark",
                          title=f"Proyeksi {selected_benefit} (2025-2050)")
            fig.update_traces(line_width=3)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Data tren tidak tersedia.")

    # TAB 2: RANKING TOTAL vs PER KAPITA (Fitur Baru!)
    with t2:
        col_rank_opt, col_chart = st.columns([1, 3])
        with col_rank_opt:
            st.markdown("#### Opsi Ranking")
            rank_mode = st.radio("Urutkan Berdasarkan:", ["Total Nilai Ekonomi (Juta GBP)", "Nilai Per Kapita (GBP)"])
        
        with col_chart:
            st.subheader("Top 10 Wilayah (Local Authority)")
            if 'local_authority' in main_df.columns:
                # Group by Local Authority
                if rank_mode == "Total Nilai Ekonomi (Juta GBP)":
                    city_rank = main_df.groupby('local_authority')[[selected_benefit]].sum().reset_index()
                    y_col = selected_benefit
                    color_scale = 'Viridis'
                    label_x = "Total Nilai (Juta GBP)"
                else:
                    # Hitung ulang per kapita di level kota
                    # Sum(Nilai) / Sum(Populasi)
                    city_rank = main_df.groupby('local_authority').agg({selected_benefit: 'sum', 'population': 'sum'}).reset_index()
                    city_rank['per_capita'] = (city_rank[selected_benefit] * 1_000_000) / city_rank['population']
                    city_rank = city_rank[city_rank['per_capita'] > 0] # Buang yang error/0
                    y_col = 'per_capita'
                    color_scale = 'Plasma' # Beda warna biar kelihatan beda mode
                    label_x = "Nilai per Orang (GBP)"

                top10 = city_rank.sort_values(by=y_col, ascending=False).head(10)
                
                fig_bar = px.bar(top10, x=y_col, y='local_authority', orientation='h', 
                                 text_auto='.2s', template="plotly_dark", 
                                 color=y_col, color_continuous_scale=color_scale,
                                 labels={y_col: label_x, 'local_authority': ''})
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)

    # TAB 3: KORELASI DATA (Fitur Baru!)
    with t3:
        c_corr1, c_corr2 = st.columns(2)
        
        with c_corr1:
            st.subheader("📉 Korelasi Populasi")
            st.caption("Apakah kota yang lebih padat selalu mendapatkan manfaat lebih besar?")
            if 'population' in main_df.columns:
                scatter_data = main_df.groupby('local_authority').agg({'population': 'sum', selected_benefit: 'sum', 'nation': 'first'}).reset_index()
                fig_scat = px.scatter(scatter_data, x='population', y=selected_benefit, color='nation', size='population', hover_name='local_authority', template="plotly_dark", log_x=True)
                st.plotly_chart(fig_scat, use_container_width=True)

        with c_corr2:
            st.subheader("🔗 Hubungan Antar Manfaat")
            st.caption(f"Bagaimana hubungan {selected_benefit} dengan manfaat lainnya?")
            
            # Hitung korelasi antar kolom numerik
            numeric_df = main_df.select_dtypes(include='number').drop(columns=['sum', 'population', 'benefit_per_capita'], errors='ignore')
            corr_matrix = numeric_df.corr()
            
            # Ambil korelasi hanya untuk benefit yang dipilih vs yang lain
            target_corr = corr_matrix[[selected_benefit]].sort_values(by=selected_benefit, ascending=False)
            
            fig_heat = px.imshow(target_corr.T, text_auto=True, color_continuous_scale='RdBu_r', template="plotly_dark", aspect="auto")
            st.plotly_chart(fig_heat, use_container_width=True)
            
            # Insight Otomatis Korelasi
            top_positive = target_corr.index[1] # Indeks 0 adalah dirinya sendiri
            st.info(f"💡 **Insight:** {selected_benefit} memiliki korelasi positif terkuat dengan **{top_positive}**. Artinya, kebijakan yang meningkatkan {selected_benefit} cenderung juga meningkatkan {top_positive}.")

    # TAB 4: HEAD TO HEAD
    with t4:
        st.subheader("⚔️ Head-to-Head Comparison")
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
        
        comp_df = pd.DataFrame({'Wilayah': [loc_a, loc_b], 'Nilai': [val_a, val_b]})
        fig_comp = px.bar(comp_df, x='Wilayah', y='Nilai', color='Wilayah', template="plotly_dark")
        st.plotly_chart(fig_comp, use_container_width=True)

    # TAB 5: HEALTH DEEP DIVE
    with t5:
        st.subheader("❤️ Analisis Kesehatan (Health Breakdown)")
        if not df3.empty:
            df3_sub = df3[(df3['co_benefit_type'] == selected_benefit) & (df3['small_area'].isin(valid_areas))]
            if not df3_sub.empty and 'damage_type' in df3_sub.columns:
                health_breakdown = df3_sub.groupby('damage_type')['sum'].sum().reset_index()
                fig_pie = px.pie(health_breakdown, values='sum', names='damage_type', color='damage_type', color_discrete_map={'health':'#EF553B', 'non-health':'#636EFA'}, template="plotly_dark", hole=0.5)
                st.plotly_chart(fig_pie, use_container_width=True)
                
                n_health = health_breakdown[health_breakdown['damage_type']=='health']['sum'].sum()
                n_non = health_breakdown[health_breakdown['damage_type']=='non-health']['sum'].sum()
                pct_health = (n_health / (n_health + n_non)) * 100
                st.caption(f"Pada kategori ini, **{pct_health:.1f}%** manfaatnya adalah keuntungan kesehatan langsung.")
            else:
                st.info("Detail breakdown tidak tersedia untuk kategori ini.")
        else:
            st.warning("Data Level 3 belum dimuat.")

except Exception as e:
    st.error(f"Error System: {e}")
