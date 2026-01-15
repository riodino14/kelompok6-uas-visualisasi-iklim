import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="UK Climate Co-Benefits", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS CUSTOM (Gaya Tampilan) ---
st.markdown("""
<style>
    /* Metric Card yang keren */
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
    h1, h2, h3 { color: #00CC96 !important; }
    
    /* Kotak Insight Khusus untuk Story Mode */
    .insight-box {
        padding: 20px;
        border-radius: 10px;
        background-color: #262730;
        border-left: 5px solid #00CC96;
        margin-bottom: 20px;
        font-size: 16px;
    }
    .recommendation-box {
        padding: 15px;
        border-radius: 10px;
        background-color: #2E1E1E; /* Agak kemerahan dikit */
        border: 1px solid #555;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. LOAD DATA (OPTIMIZED) ---
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
    
    # Hitung Benefit Per Kapita (Jaga-jaga pembagian nol)
    df1['benefit_per_capita'] = df1.apply(lambda row: (row['sum'] * 1_000_000) / row['population'] if row['population'] > 0 else 0, axis=1)
    
    return df1, df2, df3

try:
    df1, df2, df3 = load_data()
    
    # ==========================================
    # 4. SIDEBAR: NAVIGASI & FILTER GLOBAL
    # ==========================================
    st.sidebar.title("🌱 Moving Better")
    
    # Pilihan Menu Halaman
    page_mode = st.sidebar.radio("Pilih Mode Tampilan:", ["📊 Dashboard Data", "📝 Story & Kesimpulan"])
    st.sidebar.markdown("---")

    st.sidebar.header("⚙️ Filter Data")
    
    # Filter 1: Nation (Multiselect - Fitur Ultimate)
    all_nations = sorted(df1['nation'].dropna().unique().tolist()) if 'nation' in df1.columns else []
    # Default pilih United Kingdom (All) atau yang pertama
    default_nat = ["United Kingdom (All)"] if "United Kingdom (All)" in all_nations else all_nations[:1]
    selected_nations = st.sidebar.multiselect("Negara Bagian:", all_nations, default=default_nat)
    
    if not selected_nations:
        st.sidebar.warning("Pilih minimal 1 negara bagian.")
        st.stop()

    # Filter Dataframe Utama
    main_df = df1[df1['nation'].isin(selected_nations)]

    # Filter 2: Benefit
    exclude = ['sum', 'population', 'households', 'geometry', 'benefit_per_capita']
    benefit_opts = [c for c in main_df.select_dtypes(include='number').columns if c not in exclude]
    def_idx = benefit_opts.index('physical_activity') if 'physical_activity' in benefit_opts else 0
    selected_benefit = st.sidebar.selectbox("Fokus Manfaat:", benefit_opts, index=def_idx)

    # Info footer
    st.sidebar.markdown("---")
    st.sidebar.caption("Data: UK Co-Benefits Atlas | Kelompok 6")

    # Hitung KPI Global (Dipakai di kedua halaman)
    total_val = main_df[selected_benefit].sum()
    total_all = main_df['sum'].sum()
    valid_areas = main_df['small_area'].unique()

    # ==========================================
    # HALAMAN 1: DASHBOARD DATA (FITUR LENGKAP)
    # ==========================================
    if page_mode == "📊 Dashboard Data":
        st.title(f"📊 Dashboard: {selected_benefit.replace('_', ' ').title()}")
        st.markdown("Eksplorasi data interaktif, tren, dan perbandingan antar wilayah.")

        # KPI CARDS
        c1, c2, c3 = st.columns(3)
        c1.metric(f"💰 Nilai {selected_benefit}", f"£ {total_val:,.0f} Juta")
        c2.metric("🌍 Total Semua Manfaat", f"£ {total_all:,.0f} Juta")
        if 'population' in main_df.columns and main_df['population'].sum() > 0:
            per_capita = (total_val * 1_000_000) / main_df['population'].sum()
            c3.metric("👤 Per Kapita", f"£ {per_capita:,.2f}")

        # TABS VISUALISASI LENGKAP (Ultimate 2.0)
        t1, t2, t3, t4, t5 = st.tabs(["📈 Tren Komparasi", "🏆 Peringkat", "📉 Korelasi", "🥊 Head-to-Head", "❤️ Health"])

        # TAB 1: TREN (Line Chart Multi-Nation)
        with t1:
            st.subheader("Tren Pertumbuhan (2025-2050)")
            df2_sub = df2[(df2['co_benefit_type'] == selected_benefit) & (df2['small_area'].isin(valid_areas))]
            if not df2_sub.empty:
                df2_merged = df2_sub.merge(df1[['small_area', 'nation']], on='small_area', how='left')
                avail_years = [c for c in df2_merged.columns if c.startswith('20')]
                df_trend = df2_merged.melt(id_vars=["small_area", "nation"], value_vars=avail_years, var_name="Tahun", value_name="Nilai")
                df_trend["Nilai"] = df_trend["Nilai"].astype(float)
                trend_agg = df_trend.groupby(["Tahun", "nation"])["Nilai"].sum().reset_index()
                
                fig = px.line(trend_agg, x="Tahun", y="Nilai", color="nation", markers=True, template="plotly_dark")
                fig.update_traces(line_width=3)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Data tren tidak tersedia.")

        # TAB 2: RANKING (Opsi Total vs Per Kapita)
        with t2:
            c_opt, c_plot = st.columns([1, 3])
            with c_opt:
                st.markdown("#### Opsi Ranking")
                rank_mode = st.radio("Urutkan:", ["Total Nilai (£)", "Per Kapita (£)"])
            with c_plot:
                if 'local_authority' in main_df.columns:
                    if rank_mode == "Total Nilai (£)":
                        city_rank = main_df.groupby('local_authority')[[selected_benefit]].sum().reset_index()
                        y_col, color_s, lab_x = selected_benefit, 'Viridis', "Total (Juta GBP)"
                    else:
                        city_rank = main_df.groupby('local_authority').agg({selected_benefit: 'sum', 'population': 'sum'}).reset_index()
                        city_rank['pc'] = (city_rank[selected_benefit] * 1_000_000) / city_rank['population']
                        city_rank = city_rank[city_rank['pc'] > 0]
                        y_col, color_s, lab_x = 'pc', 'Plasma', "GBP per Orang"

                    top10 = city_rank.sort_values(by=y_col, ascending=False).head(10)
                    fig_bar = px.bar(top10, x=y_col, y='local_authority', orientation='h', text_auto='.2s', 
                                     template="plotly_dark", color=y_col, color_continuous_scale=color_s, labels={y_col: lab_x, 'local_authority': ''})
                    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_bar, use_container_width=True)

        # TAB 3: KORELASI (Scatter & Heatmap)
        with t3:
            c_corr1, c_corr2 = st.columns(2)
            with c_corr1:
                st.subheader("Populasi vs Manfaat")
                if 'population' in main_df.columns:
                    scat = main_df.groupby('local_authority').agg({'population': 'sum', selected_benefit: 'sum', 'nation': 'first'}).reset_index()
                    st.plotly_chart(px.scatter(scat, x='population', y=selected_benefit, color='nation', size='population', template="plotly_dark", log_x=True), use_container_width=True)
            with c_corr2:
                st.subheader("Heatmap Korelasi")
                num_df = main_df.select_dtypes(include='number').drop(columns=['sum', 'population', 'benefit_per_capita'], errors='ignore')
                corr = num_df.corr()[[selected_benefit]].sort_values(by=selected_benefit, ascending=False)
                st.plotly_chart(px.imshow(corr.T, text_auto=True, color_continuous_scale='RdBu_r', template="plotly_dark", aspect='auto'), use_container_width=True)

        # TAB 4: HEAD TO HEAD
        with t4:
            st.subheader("⚔️ Bandingkan 2 Wilayah")
            ca, cb = st.columns(2)
            locs = sorted(df1['local_authority'].dropna().unique())
            la = ca.selectbox("Wilayah A", locs, index=0)
            lb = cb.selectbox("Wilayah B", locs, index=1)
            
            va = df1[df1['local_authority'] == la][selected_benefit].sum()
            vb = df1[df1['local_authority'] == lb][selected_benefit].sum()
            
            comp_df = pd.DataFrame({'Wilayah': [la, lb], 'Nilai': [va, vb]})
            st.plotly_chart(px.bar(comp_df, x='Wilayah', y='Nilai', color='Wilayah', template="plotly_dark"), use_container_width=True)

        # TAB 5: HEALTH DEEP DIVE
        with t5:
            st.subheader("❤️ Analisis Kesehatan")
            if not df3.empty:
                df3_s = df3[(df3['co_benefit_type'] == selected_benefit) & (df3['small_area'].isin(valid_areas))]
                if not df3_s.empty:
                    pie_d = df3_s.groupby('damage_type')['sum'].sum().reset_index()
                    st.plotly_chart(px.pie(pie_d, values='sum', names='damage_type', color='damage_type', template="plotly_dark", hole=0.5), use_container_width=True)
                else:
                    st.info("Data detail tidak tersedia.")
            else:
                st.warning("Data Level 3 belum dimuat.")

    # ==========================================
    # HALAMAN 2: STORY & KESIMPULAN (DESAIN BARU!)
    # ==========================================
    elif page_mode == "📝 Story & Kesimpulan":
        st.title("📝 Executive Summary & Insights")
        st.markdown(f"### Analisis Mendalam: {selected_benefit.replace('_', ' ').title()}")
        
        # 1. GRAFIK UTAMA (Highlight Chart)
        # Kita ambil Area Chart besar untuk menunjukkan pertumbuhan masif
        valid_areas = main_df['small_area'].unique()
        df2_sub = df2[(df2['co_benefit_type'] == selected_benefit) & (df2['small_area'].isin(valid_areas))]
        if not df2_sub.empty:
            df2_merged = df2_sub.merge(df1[['small_area', 'nation']], on='small_area', how='left')
            avail_years = [c for c in df2_merged.columns if c.startswith('20')]
            trend_agg = df2_merged.melt(id_vars=["small_area", "nation"], value_vars=avail_years, var_name="Tahun", value_name="Nilai").astype({'Nilai':float}).groupby("Tahun")["Nilai"].sum().reset_index()
            
            fig_story = px.area(trend_agg, x="Tahun", y="Nilai", title=f"Proyeksi Total Nilai Ekonomi ({', '.join(selected_nations)})", template="plotly_dark")
            fig_story.update_traces(line_color="#00CC96")
            st.plotly_chart(fig_story, use_container_width=True)

        # 2. INSIGHT BOX (HTML Custom yang Cantik)
        st.markdown("#### 💡 Key Insights (Interpretasi Data)")
        
        # Logika Text Insight
        insight_content = ""
        if selected_benefit == 'physical_activity':
            insight_content = f"""
            <p><strong>1. Dominasi Sektor Kesehatan:</strong> Nilai ekonomi sebesar <strong>£{total_val:,.0f} Juta</strong> ini sebagian besar bukan uang tunai, melainkan "Cost Avoidance" (Biaya yang terhindarkan). Ketika masyarakat lebih aktif berjalan kaki, beban NHS untuk penyakit jantung dan diabetes turun drastis.</p>
            <p><strong>2. Efektivitas Urban:</strong> Data scatter plot (di menu Dashboard) menunjukkan korelasi positif kuat di kota padat. Artinya, investasi trotoar di kota besar memberikan <em>Return on Investment</em> (ROI) paling cepat.</p>
            """
        elif selected_benefit == 'air_quality':
            insight_content = f"""
            <p><strong>1. Nyawa yang Selamat:</strong> Polusi udara adalah pembunuh senyap. Nilai <strong>£{total_val:,.0f} Juta</strong> merepresentasikan penurunan kematian dini akibat penyakit pernapasan kronis.</p>
            <p><strong>2. Sinergi Kebijakan:</strong> Terdapat korelasi kuat dengan <em>Physical Activity</em>. Kebijakan mengurangi kendaraan pribadi otomatis meningkatkan kualitas udara sekaligus aktivitas fisik warga.</p>
            """
        else:
            insight_content = f"""
            <p><strong>Kontribusi Signifikan:</strong> Kategori ini menyumbang sekitar <strong>{(total_val/total_all)*100:.1f}%</strong> dari total manfaat aksi iklim. Tren grafik menunjukkan pertumbuhan yang konsisten hingga tahun 2050, menandakan bahwa manfaat ini bersifat jangka panjang dan berkelanjutan.</p>
            """

        # Render HTML Insight Box
        st.markdown(f"""
        <div class="insight-box">
            {insight_content}
        </div>
        """, unsafe_allow_html=True)

        # 3. REKOMENDASI (Call to Action)
        st.markdown("#### 🚀 Rekomendasi & Langkah Selanjutnya")
        
        col_cta1, col_cta2 = st.columns(2)
        with col_cta1:
            st.success("**✅ Untuk Pemerintah (Policy Makers):**")
            st.markdown("""
            * **Fokus Infrastruktur:** Alihkan anggaran pelebaran jalan ke pembangunan jalur sepeda terproteksi.
            * **Target Wilayah:** Prioritaskan Local Authority dengan kepadatan penduduk tinggi namun nilai per kapita rendah.
            """)
            
        with col_cta2:
            st.info("**🔬 Rencana Pengembangan (Next Steps):**")
            st.markdown("""
            * **Integrasi IoT:** Menghubungkan dashboard dengan sensor kualitas udara real-time.
            * **Machine Learning:** Menambahkan model prediksi dampak ekonomi jika kebijakan Net Zero dipercepat.
            """)

except Exception as e:
    st.error(f"Error System: {e}")
