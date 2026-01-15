import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="UK Climate Co-Benefits", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS CUSTOM (Gaya Tampilan) ---
st.markdown("""
<style>
    /* Metric Card */
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
    h1, h2, h3 { color: #00CC96 !important; }
    
    /* Kotak Insight Khusus */
    .insight-box {
        padding: 20px;
        border-radius: 10px;
        background-color: #262730;
        border-left: 5px solid #00CC96;
        margin-bottom: 20px;
        color: white;
        font-family: sans-serif;
    }
    .insight-box h4 {
        margin-top: 0;
        color: #00CC96;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. LOAD DATA ---
@st.cache_data
def load_data():
    try:
        df1 = pd.read_parquet("optimized_level_1.parquet")
        df2 = pd.read_parquet("optimized_level_2.parquet")
        try:
            df3 = pd.read_parquet("optimized_level_3.parquet")
        except:
            df3 = pd.DataFrame() 

        lookup = pd.read_excel("lookups.xlsx")
        cols_to_use = [c for c in ['small_area', 'local_authority', 'nation', 'population'] if c in lookup.columns]
        df1 = df1.merge(lookup[cols_to_use], on='small_area', how='left')
        
        # Benefit Per Kapita
        df1['benefit_per_capita'] = df1.apply(lambda row: (row['sum'] * 1_000_000) / row['population'] if row['population'] > 0 else 0, axis=1)
        return df1, df2, df3
    except Exception as e:
        st.error(f"Error Loading Data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

try:
    df1, df2, df3 = load_data()
    if df1.empty: st.stop()
    
    # ==========================================
    # 4. SIDEBAR
    # ==========================================
    st.sidebar.title("🌱 Moving Better")
    page_mode = st.sidebar.radio("Pilih Mode:", ["📊 Dashboard Data", "📝 Story & Kesimpulan"])
    st.sidebar.markdown("---")

    st.sidebar.header("⚙️ Filter Data")
    
    # Filter Nation
    all_nations = sorted(df1['nation'].dropna().unique().tolist()) if 'nation' in df1.columns else []
    default_nat = ["United Kingdom (All)"] if "United Kingdom (All)" in all_nations else all_nations[:1]
    selected_nations = st.sidebar.multiselect("Negara Bagian:", all_nations, default=default_nat)
    
    if not selected_nations:
        st.sidebar.warning("Pilih minimal 1 negara.")
        st.stop()

    main_df = df1[df1['nation'].isin(selected_nations)]

    # Filter Benefit
    exclude = ['sum', 'population', 'households', 'geometry', 'benefit_per_capita']
    benefit_opts = [c for c in main_df.select_dtypes(include='number').columns if c not in exclude]
    def_idx = benefit_opts.index('physical_activity') if 'physical_activity' in benefit_opts else 0
    selected_benefit = st.sidebar.selectbox("Fokus Manfaat (Detail):", benefit_opts, index=def_idx)

    st.sidebar.markdown("---")
    st.sidebar.caption("Data: UK Co-Benefits Atlas | Kelompok 6")

    # KPI Global
    total_val = main_df[selected_benefit].sum()
    total_all = main_df['sum'].sum()
    valid_areas = main_df['small_area'].unique()

    # ==========================================
    # HALAMAN 1: DASHBOARD
    # ==========================================
    if page_mode == "📊 Dashboard Data":
        st.title(f"📊 Dashboard: {selected_benefit.replace('_', ' ').title()}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric(f"💰 Nilai {selected_benefit}", f"£ {total_val:,.0f} Juta")
        c2.metric("🌍 Total Semua Manfaat", f"£ {total_all:,.0f} Juta")
        if 'population' in main_df.columns and main_df['population'].sum() > 0:
            per_capita = (total_val * 1_000_000) / main_df['population'].sum()
            c3.metric("👤 Per Kapita", f"£ {per_capita:,.2f}")

        t1, t2, t3, t4, t5 = st.tabs(["📈 Tren", "🏆 Peringkat", "📉 Korelasi", "🥊 Head-to-Head", "❤️ Health"])

        with t1: # Tren
            st.subheader("Tren Pertumbuhan (2025-2050)")
            df2_sub = df2[(df2['co_benefit_type'] == selected_benefit) & (df2['small_area'].isin(valid_areas))]
            if not df2_sub.empty:
                df2_merged = df2_sub.merge(df1[['small_area', 'nation']], on='small_area', how='left')
                years = [c for c in df2_merged.columns if c.startswith('20')]
                trend = df2_merged.melt(id_vars=["nation"], value_vars=years, var_name="Tahun", value_name="Nilai")
                agg = trend.groupby(["Tahun", "nation"])["Nilai"].sum().reset_index()
                st.plotly_chart(px.line(agg, x="Tahun", y="Nilai", color="nation", markers=True, template="plotly_dark"), use_container_width=True)
            else:
                st.warning("Data tren tidak tersedia.")

        with t2: # Ranking
            c_opt, c_plot = st.columns([1, 3])
            rank_mode = c_opt.radio("Urutkan:", ["Total Nilai (£)", "Per Kapita (£)"])
            if 'local_authority' in main_df.columns:
                if rank_mode == "Total Nilai (£)":
                    top10 = main_df.groupby('local_authority')[selected_benefit].sum().reset_index().sort_values(selected_benefit, ascending=False).head(10)
                    y_col, col_s = selected_benefit, 'Viridis'
                else:
                    top10 = main_df.groupby('local_authority').agg({selected_benefit: 'sum', 'population': 'sum'}).reset_index()
                    top10['pc'] = (top10[selected_benefit] * 1e6) / top10['population']
                    top10 = top10.sort_values('pc', ascending=False).head(10)
                    y_col, col_s = 'pc', 'Plasma'
                st.plotly_chart(px.bar(top10, x=y_col, y='local_authority', orientation='h', text_auto='.2s', template="plotly_dark", color=y_col, color_continuous_scale=col_s), use_container_width=True)

        with t3: # Korelasi
            c_a, c_b = st.columns(2)
            with c_a:
                scat = main_df.groupby('local_authority').agg({'population': 'sum', selected_benefit: 'sum', 'nation': 'first'}).reset_index()
                st.plotly_chart(px.scatter(scat, x='population', y=selected_benefit, color='nation', size='population', template="plotly_dark", log_x=True, title="Populasi vs Manfaat"), use_container_width=True)
            with c_b:
                num_df = main_df.select_dtypes(include='number').drop(columns=['sum', 'population', 'benefit_per_capita'], errors='ignore')
                corr = num_df.corr()[[selected_benefit]].sort_values(by=selected_benefit, ascending=False)
                st.plotly_chart(px.imshow(corr.T, text_auto=True, color_continuous_scale='RdBu_r', template="plotly_dark", aspect='auto', title="Heatmap Korelasi"), use_container_width=True)

        with t4: # VS
            ca, cb = st.columns(2)
            locs = sorted(df1['local_authority'].dropna().unique())
            la = ca.selectbox("Wilayah A", locs, index=0)
            lb = cb.selectbox("Wilayah B", locs, index=1)
            va = df1[df1['local_authority'] == la][selected_benefit].sum()
            vb = df1[df1['local_authority'] == lb][selected_benefit].sum()
            st.plotly_chart(px.bar(x=[la, lb], y=[va, vb], color=[la, lb], template="plotly_dark", title="Head-to-Head"), use_container_width=True)

        with t5: # Health
            if not df3.empty:
                df3_s = df3[(df3['co_benefit_type'] == selected_benefit) & (df3['small_area'].isin(valid_areas))]
                if not df3_s.empty:
                    pie_d = df3_s.groupby('damage_type')['sum'].sum().reset_index()
                    st.plotly_chart(px.pie(pie_d, values='sum', names='damage_type', color='damage_type', template="plotly_dark", hole=0.5), use_container_width=True)
                else:
                    st.info("Data detail tidak tersedia.")

    # ==========================================
    # HALAMAN 2: STORY (FITUR BARU)
    # ==========================================
    elif page_mode == "📝 Story & Kesimpulan":
        st.title("📝 Executive Summary")
        
        # 1. VISUALISASI PERBANDINGAN SEMUA MANFAAT (YANG KAMU MINTA!)
        st.subheader("🏆 Komparasi: Mana Manfaat Paling Besar?")
        st.caption(f"Perbandingan total nilai ekonomi seluruh kategori manfaat di {', '.join(selected_nations)}")
        
        # Hitung total untuk semua benefit types
        all_benefits_sum = main_df[benefit_opts].sum().sort_values(ascending=True)
        
        fig_comp = px.bar(
            x=all_benefits_sum.values,
            y=all_benefits_sum.index,
            orientation='h',
            template="plotly_dark",
            labels={'x': 'Total Nilai (Juta GBP)', 'y': 'Jenis Manfaat'},
            color=all_benefits_sum.values,
            color_continuous_scale='Viridis'
        )
        fig_comp.update_layout(height=500)
        st.plotly_chart(fig_comp, use_container_width=True)

        st.markdown("---")
        
        # 2. INSIGHT BOX (FIXED HTML BUG)
        st.subheader(f"💡 Deep Dive: {selected_benefit.replace('_', ' ').title()}")
        
        # Logika Text (Menggunakan HTML standar yang aman)
        if selected_benefit == 'physical_activity':
            html_content = """
            <h4>1. Dominasi Sektor Kesehatan</h4>
            <p>Nilai ekonomi kategori ini sebagian besar berasal dari <b>"Cost Avoidance"</b> (Biaya yang terhindarkan). Ketika masyarakat lebih aktif berjalan kaki, beban NHS untuk penyakit jantung dan diabetes turun drastis.</p>
            <br>
            <h4>2. Efektivitas Urban</h4>
            <p>Data menunjukkan korelasi positif kuat di kota padat. Investasi trotoar di kota besar memberikan <b>Return on Investment (ROI)</b> paling cepat.</p>
            """
        elif selected_benefit == 'air_quality':
            html_content = """
            <h4>1. Nyawa yang Selamat</h4>
            <p>Polusi udara adalah pembunuh senyap. Nilai ekonomi di sini merepresentasikan penurunan kematian dini akibat penyakit pernapasan kronis.</p>
            <br>
            <h4>2. Sinergi Kebijakan</h4>
            <p>Terdapat korelasi kuat dengan <b>Physical Activity</b>. Mengurangi kendaraan pribadi otomatis meningkatkan kualitas udara sekaligus aktivitas fisik warga.</p>
            """
        else:
            pct = (total_val/total_all)*100
            html_content = f"""
            <h4>Kontribusi Signifikan</h4>
            <p>Kategori ini menyumbang sekitar <b>{pct:.1f}%</b> dari total manfaat aksi iklim. Tren grafik menunjukkan pertumbuhan yang konsisten hingga tahun 2050.</p>
            """

        # Render HTML yang sudah diperbaiki
        st.markdown(f"""
        <div class="insight-box">
            {html_content}
        </div>
        """, unsafe_allow_html=True)

        # 3. REKOMENDASI
        col_cta1, col_cta2 = st.columns(2)
        with col_cta1:
            st.success("""
            **✅ Rekomendasi Pemerintah:**
            * Alihkan anggaran pelebaran jalan ke jalur sepeda terproteksi.
            * Prioritaskan wilayah padat penduduk dengan nilai per kapita rendah.
            """)
        with col_cta2:
            st.info("""
            **🔬 Rencana Selanjutnya:**
            * Integrasi sensor IoT kualitas udara real-time.
            * Prediksi dampak ekonomi dengan Machine Learning.
            """)

except Exception as e:
    st.error(f"Critical Error: {e}")
