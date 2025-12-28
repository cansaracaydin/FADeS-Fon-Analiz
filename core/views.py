# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from core.processor import DataProcessor

# Initialize processor for usage in views if needed essentially
processor = DataProcessor()

# -----------------------------------------------------------------------------
# VIEW 1: DETAYLI ANALİZ def: definition (tanımlama) pd: pandas 
# -----------------------------------------------------------------------------
def render_analysis_view(df: pd.DataFrame, selected_funds: list, inf_df: pd.DataFrame, benchmark_id: str = None):
    """
    Renders the Detailed Analysis view: Charts, Tables, Assets, Risk, Real Return.
    """
    st.subheader("📈 Fon Performans Karnesi")
    #st: streamlit
    # Identify Benchmark Data
    benchmark_df = pd.DataFrame()
    if benchmark_id and benchmark_id != "Yok":
        # Usually benchmark is in the df but with a different code logic or flag
        # In app.py we treated benchmark as just another 'fund' in raw_data with FundCode = benchmark_name
        # We need to find it.
        # Benchmark ID comes from sidebar selectbox, e.g., "BIST 100", "Dolar ..."
        # But in app.py we set FundCode = benchmark.split(" ")[0] -> "BIST", "Dolar", "Altın"
        
        # Let's try to find it by name or code.
        # Ideally, we should pass the benchmark DF explicitly or know its code.
        # For now, let's assume the user selects 3 funds + Benchmark is in the DF.
        
        # Heuristic: Check common codes
        bench_code = benchmark_id.split(" ")[0] # "BIST", "Dolar", "Altın"
        if bench_code in df['FundCode'].unique():
            benchmark_df = df[df['FundCode'] == bench_code]
    
    # Tabs definition
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Karşılaştırmalı Grafik", 
        "📋 Detaylı Tablo", 
        "🔥 Korelasyon & Risk",
        "💰 Reel Getiri (Enflasyon)",
        "🧮 Matematiksel Modeller"
    ])
    
    # TAB 1: Chart
    with tab1:
        col_opt, col_chart = st.columns([1, 4])
        with col_opt:
            st.markdown("##### ⚙️ Grafik Ayarları")
            norm_active = st.toggle("Normalize Et (0'dan Başlat)", value=True)
            st.caption("Farklı fiyatlı fonları aynı eksende kıyaslamak için normalizasyon önerilir.")
            
        with col_chart:
            plot_df = processor.normalize_for_comparison(df) if norm_active else df
            y_col = "Cumulative_Return" if norm_active else "Price"
            title_txt = "Kümülatif Getiri Karşılaştırması" if norm_active else "Fiyat Grafiği"
            
            fig = px.line(plot_df, x="Date", y=y_col, color="FundCode", title=title_txt, template="plotly_dark")
            if norm_active: fig.layout.yaxis.tickformat = ',.0%'
            fig.update_layout(legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, use_container_width=True)
        
    # TAB 2: Table
    with tab2:
        metrics_list = []
        for f in df['FundCode'].unique():
            if f == benchmark_id: continue # Skip benchmark row itself if needed, or keep it.
            
            sub = df[df['FundCode']==f]
            m = processor.calculate_risk_metrics(sub)
            
            if m:
                # Add Comparative Metrics if Benchmark exists
                if not benchmark_df.empty:
                    comp_m = processor.calculate_comparative_metrics(sub, benchmark_df)
                    m.update(comp_m)
                
                m['Fon'] = f
                metrics_list.append(m)
        
        if metrics_list:
            m_df = pd.DataFrame(metrics_list).set_index("Fon")
            
            # Column Order
            base_cols = ["Toplam Getiri", "Yıllık Volatilite", "Sharpe Oranı", "Sortino Oranı", "Calmar Oranı", "Max Drawdown"]
            adv_cols = ["Alpha", "Beta", "Treynor Oranı", "Information Ratio", "R-Kare (R²)"]
            
            # Intersection to sort
            final_cols = [c for c in base_cols if c in m_df.columns] + [c for c in adv_cols if c in m_df.columns]
            m_df = m_df[final_cols]
            
            st.write("#### Finansal Performans Metrikleri")
            
            # 1. Higher is Better (Returns, Sharpe, Alpha, etc.) -> Green High / Red Low
            # Default RdYlGn: Red (Low) -> Green (High)
            up_cols = ["Toplam Getiri", "Sharpe Oranı", "Sortino Oranı", "Calmar Oranı", "Alpha", "Information Ratio", "Treynor Oranı", "Max Drawdown"]
            # Note: Max Drawdown is negative numbers. -0.1 (High) is Green, -0.5 (Low) is Red. So RdYlGn works.
            
            # 2. Lower is Better (Volatility) -> Green Low / Red High
            # We need to reverse: RdYlGn_r: Green (Low) -> Red (High)
            down_cols = ["Yıllık Volatilite"]
            
            # Neutral / Descriptive
            neutral_cols = ["Beta", "R-Kare (R²)"]
            
            # Verify columns exist
            valid_up = [c for c in up_cols if c in m_df.columns]
            valid_down = [c for c in down_cols if c in m_df.columns]
            valid_neutral = [c for c in neutral_cols if c in m_df.columns]
            
            # Apply Styles
            styler = m_df.style.format("{:.2f}")
            
            if valid_up:
                styler = styler.background_gradient(cmap="RdYlGn", subset=valid_up, vmin=None, vmax=None)
            
            if valid_down:
                styler = styler.background_gradient(cmap="RdYlGn_r", subset=valid_down)
                
            if valid_neutral:
                styler = styler.background_gradient(cmap="Blues", subset=valid_neutral)
            
            st.dataframe(
                styler, 
                use_container_width=True,
                height=300
            )
            if not benchmark_df.empty:
                st.caption(f"*Alpha, Beta ve diğer karşılaştırmalı metrikler **{benchmark_id}** baz alınarak hesaplanmıştır.*")
            else:
                st.info("💡 Beta, Alpha, Treynor gibi metrikleri görmek için Sol Menüden bir Benchmark (Kıyas) seçiniz.")

    # TAB 3: Correlation & Risk
    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔥 Korelasyon Matrisi")
            corr_funds = [f for f in selected_funds if f in df['FundCode'].unique()]
            if len(corr_funds) > 1:
                corr = processor.calculate_correlation_matrix(df[df['FundCode'].isin(corr_funds)])
                fig_corr = px.imshow(
                    corr, text_auto=".2f", color_continuous_scale="RdBu", 
                    zmin=-1, zmax=1, template="plotly_dark"
                )
                st.plotly_chart(fig_corr, use_container_width=True)
                
                with st.expander("ℹ️ Korelasyon Katsayıları Ne Anlama Gelir?"):
                    st.markdown("""
                    **Korelasyon (-1 ile +1 arası):** İki fonun fiyat hareketlerinin birbirine benzerliğini ölçer.
                    
                    *   🔵 **+1.00 (Tam Pozitif):** İki fon birebir aynı yönde hareket eder. (Çeşitlendirme faydası **YOKTUR**)
                    *   ⚪ **0.00 (Nötr):** Fonlar birbirinden bağımsız hareket eder.
                    *   🔴 **-1.00 (Tam Negatif):** Biri yükselirken diğeri düşer. (Maksimum çeşitlendirme ve risk düşüşü sağlar)
                    
                    **Strateji:** Riski düşürmek için korelasyonu **düşük (0'a veya -1'e yakın)** fonları aynı sepete koymalısınız.
                    """)
            else: 
                st.info("Korelasyon için en az 2 fon seçilmelidir.")
            
        with c2:
            st.markdown("#### 📉 Maksimum Kayıp (Drawdown)")
            fig_dd = go.Figure()
            for f in df['FundCode'].unique():
                sub = df[df['FundCode']==f]
                dd = processor.calculate_drawdown_series(sub)
                fig_dd.add_trace(go.Scatter(x=dd['Date'], y=dd['Drawdown'], name=f, fill='tozeroy'))
            fig_dd.update_layout(yaxis_tickformat='.1%', template="plotly_dark", title="Zirveden Düşüş Oranları")
            st.plotly_chart(fig_dd, use_container_width=True)

    # TAB 4: Real Return
    with tab4:
        if not inf_df.empty:
            # Layout: Left for Selection, Right for Chart
            c_sel, c_res = st.columns([1, 3])
            
            with c_sel:
                st.markdown("##### Enflasyon Analizi")
                f_sel = st.selectbox("İncelenecek Fon:", df['FundCode'].unique())
                st.caption("TÜFE (Enflasyon) verisi kullanılarak reel getiri hesaplanır.")
                
                # Show Inflation Data Table
                with st.expander("📊 Enflasyon Verilerini Göster", expanded=True):
                    # Format cols if exists
                    show_inf = inf_df.copy()
                    if 'Date' in show_inf.columns: show_inf['Date'] = show_inf['Date'].dt.date
                    st.dataframe(show_inf, use_container_width=True, height=250)

            with c_res:
                # 1. Real Return Chart
                sub = df[df['FundCode']==f_sel]
                res = processor.calculate_real_returns(sub, inf_df)
                
                fig_real = go.Figure()
                fig_real.add_trace(go.Scatter(x=res['Date'], y=res['Cumulative_Return'], name="Nominal (Görünen)", line=dict(color='#ef5350')))
                fig_real.add_trace(go.Scatter(x=res['Date'], y=res['Real_Return'], name="Reel (Net)", line=dict(color='#66bb6a', dash='dash'), fill='tonexty'))
                fig_real.update_layout(title=f"{f_sel} - Enflasyondan Arındırılmış Getiri", template="plotly_dark", yaxis_tickformat='.1%')
                st.plotly_chart(fig_real, use_container_width=True)
                
                # 2. Monthly Inflation Chart
                if 'Aylık Enflasyon' in inf_df.columns:
                    st.markdown("##### 📉 Aylık Enflasyon Seyri")
                    fig_inf = px.bar(inf_df, x='Date', y='Aylık Enflasyon', title="Aylık Enflasyon Oranları (%)", template="plotly_dark")
                    fig_inf.update_traces(marker_color='#bfa15f')
                    st.plotly_chart(fig_inf, use_container_width=True)
        else:
            st.warning("Enflasyon verisi eksik. Sol panelden EVDS anahtarı girin veya 'Şablon' butonunu kullanın.")
            
    # TAB 5: Mathematical Models (LaTeX)
    with tab5:
        st.header("🧮 Finansal Matematik ve Formüller")
        st.write("Profesyonel analizde kullanılan metriklerin matematiksel altyapısı aşağıdadır.")
        
        c_m1, c_m2 = st.columns(2)
        
        with c_m1:
            st.info("**Risk / Getiri Metrikleri**")
            st.markdown("#### Sharpe Oranı")
            st.latex(r"Sharpe = \frac{R_p - R_f}{\sigma_p}")
            st.caption("$R_p$: Portföy Getirisi, $R_f$: Risksiz Faiz, $\sigma_p$: Standart Sapma")
            
            st.markdown("#### Sortino Oranı")
            st.latex(r"Sortino = \frac{R_p - R_f}{\sigma_d}")
            st.caption("$\sigma_d$: Downside Deviation (Sadece negatif getirilerin standart sapması)")
            
            st.markdown("#### Calmar Oranı")
            st.latex(r"Calmar = \frac{R_p (Yıllık)}{|Max Drawdown|}")
            
        with c_m2:
            st.info("**Piyasa Duyarlılık (CAPM) Metrikleri**")
            st.markdown("#### Beta ($\\beta$)")
            st.latex(r"\beta = \frac{Cov(R_p, R_m)}{Var(R_m)}")
            st.caption("Piyasa ($R_m$) ile olan korelasyon ve volatilite ilişkisini ölçer.")
            
            st.markdown("#### Jensen's Alpha ($\\alpha$)")
            st.latex(r"\alpha = R_p - [R_f + \beta (R_m - R_f)]")
            st.caption("Piyasa beklentisinin üzerinde elde edilen 'Ekstra' getiri.")
            
            st.markdown("#### Treynor Oranı")
            st.latex(r"Treynor = \frac{R_p - R_f}{\beta_p}")
            st.caption("Sistematik risk birimi (£eta) başına düşen getiri.")

# -----------------------------------------------------------------------------
# VIEW 2: PORTFÖY SİMÜLASYONU
# -----------------------------------------------------------------------------
def render_simulation_view(df: pd.DataFrame, selected_funds: list, sim_weights: dict, budget: float, processor: DataProcessor):
    """
    Renders the Portfolio Simulation view.
    """
    st.subheader("💼 Portföy Simülasyonu & Optimizasyon")
    
    # Filter only available funds
    user_funds = [f for f in selected_funds if f in df['FundCode'].unique()]
    
    # Check weights
    total_w = sum(sim_weights.values())
    if len(user_funds) == 0:
        st.warning("Analiz edilecek fon verisi bulunamadı.")
        return
        
    if abs(total_w - 1.0) > 0.01:
        st.error(f"Filtrelenen ağırlıklar toplamı %100 olmalıdır. (Şu an: %{total_w*100:.0f})")
        return

    # Run Simulation
    sim_res = processor.calculate_portfolio_simulation(df, sim_weights, budget)
    
    if not sim_res.empty:
        # 1. SUMMARY CARDS
        curr_val = sim_res.iloc[-1]['Price']
        profit = curr_val - budget
        ret_rate = profit / budget
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Başlangıç Bütçesi", f"{budget:,.0f} ₺")
        col2.metric("Portföy Değeri", f"{curr_val:,.0f} ₺", f"{ret_rate:+.2%}")
        col3.metric("Net Kar/Zarar", f"{profit:,.0f} ₺", delta_color="normal")
        
        # 2. CHART
        st.markdown("### 📈 Portföy Büyüme Simülasyonu")
        fig_sim = px.line(sim_res, x="Date", y="Price", title="Zaman İçindeki Portföy Değeri", template="plotly_dark")
        fig_sim.update_traces(line_color="#48c9b0", line_width=3)
        st.plotly_chart(fig_sim, use_container_width=True)
        
        # 3. ADVANCED TABS
        t_risk, t_mc, t_eff = st.tabs(["🛡️ Riske Maruz Değer (VaR)", "🎲 Monte Carlo", "⚡ Etkin Sınır (Markowitz)"])
        
        with t_risk:
            var_95 = processor.calculate_value_at_risk(df, sim_weights, budget, 0.95)
            var_99 = processor.calculate_value_at_risk(df, sim_weights, budget, 0.99)
            
            if var_95:
                # Better UI for VaR
                st.info("VaR (Value at Risk), normal piyasa koşullarında belirli bir güven aralığında 'yarın' kaybedebileceğiniz maksimum tahmini tutarı gösterir.")
                c_v1, c_v2 = st.columns(2)
                with c_v1:
                    st.error(f"**%95 Güvenle VaR**\n\n### -{var_95['VaR_Amount']:,.2f} ₺")
                    st.caption("20 günde 1 bu miktardan fazla kayıp beklenebilir.")
                with c_v2:
                    st.error(f"**%99 Güvenle VaR (Kriz)**\n\n### -{var_99['VaR_Amount']:,.2f} ₺")
                    st.caption("100 günde 1 bu miktardan fazla kayıp beklenebilir.")

        with t_mc:
            # User Input: Forecast Horizon
            forecast_days = st.slider("Simülasyon Süresi (Gün)", min_value=30, max_value=365, value=180, step=30)
            
            st.markdown(f"##### 🎲 Gelecek {forecast_days} Gün İçin Olasılıklar")
            
            col_mc_btn, col_mc_info = st.columns([1, 4])
            with col_mc_btn:
                run_mc = st.button("🎲 Simülasyonu Başlat", key="btn_mc")
            
            if run_mc:
                with st.spinner("Monte Carlo Simülasyonu Çalışıyor..."):
                    mc_data = processor.run_monte_carlo_simulation(df, sim_weights, curr_val, forecast_days, 50)
                    
                    fig_mc = px.line(mc_data, x="Date", y=mc_data.columns[1:], title="50 Farklı Senaryo", template="plotly_dark")
                    fig_mc.update_traces(line=dict(width=1), opacity=0.3, showlegend=False)
                    st.plotly_chart(fig_mc, use_container_width=True)
                    
                    # Stats
                    end_vals = mc_data.iloc[-1, 1:]
                    worst = end_vals.quantile(0.05)
                    avg = end_vals.mean()
                    best = end_vals.quantile(0.95)
                    
                    m_c1, m_c2, m_c3 = st.columns(3)
                    m_c1.metric("Kötü Senaryo (%5)", f"{worst:,.0f} ₺", delta=f"{(worst-curr_val)/curr_val:.1%}")
                    m_c2.metric("Ortalama Beklenti", f"{avg:,.0f} ₺", delta=f"{(avg-curr_val)/curr_val:.1%}")
                    m_c3.metric("İyi Senaryo (%95)", f"{best:,.0f} ₺", delta=f"{(best-curr_val)/curr_val:.1%}")
        
        with t_eff:
             st.markdown("##### ⚡ Markowitz Portfolio Optimization")
             st.caption("Bu portföy sepeti için Matematiksel olarak en iyi Risk/Getiri oranına sahip ağırlıkları hesaplar.")
             if st.button("⚡ Optimize Et", key="btn_opt"):
                 with st.spinner("Matematiksel Optimizasyon Hesaplanıyor... (SLSQP Solver)"):
                      opt_results = processor.calculate_efficient_frontier(df, user_funds)
                      
                      if opt_results:
                          sim_df = opt_results['sim_df']
                          frontier_df = opt_results['frontier_df']
                          max_sharpe = opt_results['max_sharpe']
                          min_vol = opt_results['min_vol']
                          
                          # Plot
                          fig_ef = px.scatter(sim_df, x="Volatility", y="Return", color="Sharpe", title="Etkin Sınır (Efficient Frontier)", template="plotly_dark", opacity=0.3)
                          
                          # Add Frontier Line
                          fig_ef.add_trace(go.Scatter(x=frontier_df['Volatility'], y=frontier_df['Return'], mode='lines', name='Sınır Çizgisi', line=dict(color='white', width=2, dash='dot')))
                          
                          # Add Points
                          fig_ef.add_trace(go.Scatter(
                              x=[max_sharpe['Volatility']], y=[max_sharpe['Return']], 
                              mode='markers', marker=dict(color='red', size=15, symbol='star'),
                              name='Max Sharpe'
                          ))
                          
                          fig_ef.add_trace(go.Scatter(
                              x=[min_vol['Volatility']], y=[min_vol['Return']], 
                              mode='markers', marker=dict(color='yellow', size=15, symbol='square'),
                              name='Min Risk'
                          ))
                          
                          st.plotly_chart(fig_ef, use_container_width=True)
                          
                          # Display Stats
                          c_ef1, c_ef2 = st.columns(2)
                          
                          with c_ef1:
                              st.success("🚀 Max Sharpe (Agresif)")
                              st.metric("Beklenen Getiri", f"%{max_sharpe['Return']*100:.1f}")
                              st.metric("Sharpe Oranı", f"{max_sharpe['Sharpe']:.2f}")
                              # Create Pie Chart for Max Sharpe
                              df_sharpe = pd.DataFrame.from_dict(max_sharpe['Weights'], orient='index', columns=['Oran'])
                              df_sharpe = df_sharpe[df_sharpe['Oran'] > 0.01].reset_index().rename(columns={'index':'Fon'})
                              
                              fig_sharpe = px.pie(df_sharpe, values='Oran', names='Fon', title='Varlık Dağılımı', template="plotly_dark", hole=0.4)
                              fig_sharpe.update_traces(textinfo='percent+label')
                              st.plotly_chart(fig_sharpe, use_container_width=True)
                              
                          with c_ef2:
                              st.warning("🛡️ Min Volatilite (Defansif)")
                              st.metric("Beklenen Getiri", f"%{min_vol['Return']*100:.1f}")
                              st.metric("Yıllık Risk", f"%{min_vol['Volatility']*100:.1f}")
                              
                              # Create Pie Chart for Min Volatility
                              df_vol = pd.DataFrame.from_dict(min_vol['Weights'], orient='index', columns=['Oran'])
                              df_vol = df_vol[df_vol['Oran'] > 0.01].reset_index().rename(columns={'index':'Fon'})
                              
                              fig_vol = px.pie(df_vol, values='Oran', names='Fon', title='Varlık Dağılımı', template="plotly_dark", hole=0.4)
                              fig_vol.update_traces(textinfo='percent+label')
                              st.plotly_chart(fig_vol, use_container_width=True)
                      else:
                          st.error("Optimizasyon başarısız oldu (Yetersiz veri).")

# -----------------------------------------------------------------------------
# VIEW 3: AI TAHMİN
# -----------------------------------------------------------------------------
def render_ai_view(df: pd.DataFrame, ai_forecaster):
    """
    Renders the AI Forecasting view.
    """
    st.subheader("🤖 Yapay Zeka ile Fiyat Tahmini")
    st.info("Makine Öğrenimi (Gradient Boosting) kullanarak seçilen fonun 30 günlük gelecekteki olası hareketini modeller.")
    
    target_f = st.selectbox("Analiz Edilecek Fonu Seçiniz:", df['FundCode'].unique())
    
    if st.button("🔮 Tahmini Başlat", type="primary"):
        with st.spinner(f"{target_f} için geçmiş veriler işleniyor ve model eğitiliyor..."):
            sub = df[df['FundCode'] == target_f]
            preds, r2 = ai_forecaster.train_and_predict(sub, days_forward=30)
            
            if preds is not None:
                st.success(f"Model Eğitimi Tamamlandı! (Doğruluk Skoru R²: %{r2*100:.1f})")
                
                fig_ai = go.Figure()
                past = sub.iloc[-90:] # Show last 90 days context
                
                # History
                fig_ai.add_trace(go.Scatter(
                    x=past['Date'], y=past['Price'], 
                    name="Geçmiş Veri", 
                    line=dict(color='#cfd8dc', width=2)
                ))
                
                # Forecast
                fig_ai.add_trace(go.Scatter(
                    x=preds['Date'], y=preds['Predicted_Price'], 
                    name="AI Tahmin", 
                    line=dict(color='#00bfff', width=3, dash='dot')
                ))
                
                # Confidence Interval
                fig_ai.add_trace(go.Scatter(
                     x=pd.concat([preds['Date'], preds['Date'][::-1]]),
                     y=pd.concat([preds['Upper_Bound'], preds['Lower_Bound'][::-1]]),
                     fill='toself', 
                     fillcolor='rgba(0, 191, 255, 0.15)', 
                     line=dict(color='rgba(0,0,0,0)'), 
                     name='Güven Aralığı'
                ))
                
                fig_ai.update_layout(title=f"{target_f} - 30 Günlük Fiyat Projeksiyonu", template="plotly_dark", hovermode="x unified")
                st.plotly_chart(fig_ai, use_container_width=True)

            else:
                st.error("Model eğitimi için yeterli veri sağlanamadı.")

# -----------------------------------------------------------------------------
# VIEW 4: PIYASA EKRANI (MARKET DASHBOARD)
# -----------------------------------------------------------------------------
def render_market_dashboard(market_df: pd.DataFrame):
    """
    Renders the Global Market Analysis Dashboard.
    """
    st.subheader("🌍 Küresel Piyasa Göstergeleri")
    st.caption("BIST 100, Döviz ve Emtia Piyasalarının Son 1 Yıllık Performansı")
    
    if market_df.empty:
        st.warning("Piyasa verileri yüklenemedi. Lütfen internet bağlantınızı kontrol ediniz.")
        return

    # --- 1. METRICS ROW ---
    # Create 4 columns
    cols = st.columns(4)
    assets = ['BIST 100', 'Dolar/TL', 'Euro/TL', 'Gram Altın']
    
    for i, asset in enumerate(assets):
        if asset in market_df.columns:
            series = market_df[asset]
            curr_val = series.iloc[-1]
            prev_val = series.iloc[-2]
            daily_chg = (curr_val - prev_val) / prev_val
            
            with cols[i]:
                st.metric(
                    label=asset,
                    value=f"{curr_val:,.2f}",
                    delta=f"{daily_chg:+.2%}"
                )
    
    st.divider()

    # --- 2. COMPARISON CHART (NORMALIZED) ---
    st.markdown("##### 🏁 Performans Karşılaştırması (Yılbaşı = 100)")
    
    # Normalize to 100
    norm_df = market_df[assets].copy()
    norm_df = (norm_df / norm_df.iloc[0]) * 100
    
    fig_comp = px.line(norm_df, x=norm_df.index, y=assets, title="Göreceli Getiri Analizi", template="plotly_dark")
    fig_comp.update_layout(hovermode="x unified")
    st.plotly_chart(fig_comp, use_container_width=True)
    
    # --- 3. DETAILED CHARTS ---
    st.markdown("##### 🔍 Detaylı Grafik Analizi")
    tabs = st.tabs(assets)
    
    for i, asset in enumerate(assets):
        with tabs[i]:
            if asset in market_df.columns:
                series = market_df[asset]
                
                # Candlestick-like Line Chart with Range Slider
                fig_detail = go.Figure()
                fig_detail.add_trace(go.Scatter(x=series.index, y=series, line=dict(color='#3498db', width=2), name=asset))
                
                # Add Moving Averages (Idea Upgrade)
                sma50 = series.rolling(window=50).mean()
                fig_detail.add_trace(go.Scatter(x=series.index, y=sma50, line=dict(color='#f1c40f', width=1), name='50 Günlük ORT'))
                
                fig_detail.update_layout(
                    title=f"{asset} Fiyat Hareketi",
                    template="plotly_dark",
                    xaxis_rangeslider_visible=False
                )
                st.plotly_chart(fig_detail, use_container_width=True)

# -----------------------------------------------------------------------------
# VIEW 5: MAKRO ANALİZ (EVDS & FRED)
# -----------------------------------------------------------------------------
def render_macro_view(macro_df: pd.DataFrame):
    """
    Makroekonomik verileri görselleştirir.
    """
    st.subheader("🌍 Makroekonomik Göstergeler")
    st.caption("TCMB (EVDS) ve Global Piyasalar (FED/VIX) verileri.")

    if macro_df.empty:
        st.warning("Makro veri çekilemedi.")
        return

    # En güncel veriler
    last = macro_df.iloc[-1]
    
    # 1. KPI CARDS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🇹🇷 TCMB Faizi", f"%{last.get('Faiz (%)', 0):.1f}")
    c2.metric("💵 Brüt Rezerv", f"${last.get('Rezerv (Milyar $)', 0):.1f} Mr")
    c3.metric("🇺🇸 ABD 10Y Tahvil", f"%{last.get('ABD 10Y Faiz', 0):.2f}")
    c4.metric("😨 VIX (Korku)", f"{last.get('VIX (Korku Endeksi)', 0):.1f}")

    # 2. CHARTS
    t1, t2 = st.tabs(["🇹🇷 Türkiye Ekonomisi", "🌎 Küresel Piyasalar"])
    
    with t1:
        st.markdown("##### TCMB Faiz & Rezerv Dengesi")
        # Dual Axis Chart
        fig_tr = go.Figure()
        fig_tr.add_trace(go.Scatter(x=macro_df['Date'], y=macro_df['Faiz (%)'], name='Faiz (%)', line=dict(color='red', width=3)))
        fig_tr.add_trace(go.Scatter(x=macro_df['Date'], y=macro_df['Rezerv (Milyar $)'], name='Rezerv ($ Mr)', yaxis='y2', line=dict(color='green', dash='dot')))
        
        fig_tr.update_layout(
            template="plotly_dark",
            yaxis=dict(title='Faiz (%)', side='left'),
            yaxis2=dict(title='Rezerv (Milyar $)', side='right', overlaying='y', showgrid=False),
            hovermode="x unified"
        )
        st.plotly_chart(fig_tr, use_container_width=True)
        
        if 'Güven Endeksi' in macro_df.columns:
            st.markdown("##### Reel Kesim Güven Endeksi")
            fig_conf = px.line(macro_df, x='Date', y='Güven Endeksi', title='Ekonomik Güven (RKGE)', template="plotly_dark")
            fig_conf.add_hline(y=100, line_dash="dash", line_color="white", annotation_text="Eşik Değer (100)")
            st.plotly_chart(fig_conf, use_container_width=True)

    with t2:
        st.markdown("##### Küresel Likidite ve Risk")
        fig_gl = go.Figure()
        
        if 'ABD 10Y Faiz' in macro_df.columns:
            fig_gl.add_trace(go.Scatter(x=macro_df['Date'], y=macro_df['ABD 10Y Faiz'], name='ABD 10Y (%)', line=dict(color='cyan')))
            
        if 'Dolar Endeksi (DXY)' in macro_df.columns:
            fig_gl.add_trace(go.Scatter(x=macro_df['Date'], y=macro_df['Dolar Endeksi (DXY)'], name='DXY', yaxis='y2', line=dict(color='orange')))
        
        fig_gl.update_layout(
            template="plotly_dark",
            yaxis=dict(title='ABD 10Y (%)', side='left'),
            yaxis2=dict(title='DXY', side='right', overlaying='y', showgrid=False),
            hovermode="x unified"
        )
        st.plotly_chart(fig_gl, use_container_width=True)

# -----------------------------------------------------------------------------
# VIEW 6: FORMÜLLER (LaTeX)
# -----------------------------------------------------------------------------
def render_formula_view():
    """
    Renders the Financial Formulas view.
    """
    st.subheader("📚 Finansal Metrik Formülleri")
    st.markdown("FADeS tarafından kullanılan temel finansal metriklerin matematiksel hesaplamaları aşağıdadır.")
    
    with st.expander("1. Sharpe Oranı (Sharpe Ratio)"):
        st.latex(r'''
            Sharpe = \frac{R_p - R_f}{\sigma_p}
        ''')
        st.write("""
        * **Rp**: Portföy Getirisi (Return)
        * **Rf**: Riskiz Faiz Oranı (Risk Free Rate - Mevduat/Tahvil)
        * **σp**: Portföyün Standart Sapması (Volatilite)
        * **Anlamı**: Risk başına elde edilen ekstra getiri. Yüksek olması iyidir.
        """)

    with st.expander("2. Standart Sapma (Volatilite)"):
        st.latex(r'''
            \sigma_p = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (R_i - \bar{R})^2}
        ''')
        st.write("""
        * **Anlamı**: Getirilerin ortalamadan ne kadar saptığını gösterir. Yüksek olması riskin yüksek olduğunu ifade eder.
        """)

    with st.expander("3. Maksimum Düşüş (Max Drawdown)"):
        st.latex(r'''
            MDD = \min \left( \frac{P_t - P_{peak}}{P_{peak}} \right)
        ''')
        st.write("""
        * **Pt**: T anındaki Fiyat
        * **Ppeak**: T anına kadar görülen En Yüksek Fiyat
        * **Anlamı**: Zirveden dibe yaşanan en büyük kayıp oranıdır.
        """)

    with st.expander("4. Portföy Varyansı (Markowitz)"):
        st.latex(r'''
            \sigma_p^2 = \sum_{i} \sum_{j} w_i w_j \sigma_{ij}
        ''')
        st.write("""
        * **wi, wj**: Varlıkların portföydeki ağırlıkları
        * **σij**: Varlıklar arasındaki kovaryans
        * **Anlamı**: Çeşitlendirme etkisiyle portföy riskinin hesaplanması.
        """)

# -----------------------------------------------------------------------------
# VIEW 7: REEL GETİRİ (REAL RETURN)
# -----------------------------------------------------------------------------
def render_real_return_view(df: pd.DataFrame, inf_df: pd.DataFrame):
    """
    Renders the Real Return Analysis view (Inflation Adjusted).
    """
    st.subheader("💰 Enflasyon Arındırılmış (Reel) Getiri")
    st.caption("Fon getirilerinin TÜFE (Enflasyon) karşısındaki net performansı.")

    if df.empty:
        st.warning("Fon verisi yok.")
        return

    if inf_df.empty:
        st.warning("Enflasyon verisi eksik. Sol panelden EVDS anahtarı girin veya 'Şablon' butonunu kullanın.")
        return

    # Layout: Left for Selection, Right for Chart
    c_sel, c_res = st.columns([1, 3])
    
    with c_sel:
        st.markdown("##### Fon Seçimi")
        f_sel = st.selectbox("İncelenecek Fon:", df['FundCode'].unique(), key="rr_fund_select")
        
        # Show Inflation Data Table
        with st.expander("📊 Enflasyon Tablosu", expanded=True):
            # Format cols if exists
            show_inf = inf_df.copy()
            if 'Date' in show_inf.columns: show_inf['Date'] = show_inf['Date'].dt.date
            st.dataframe(show_inf, use_container_width=True, height=250)

    with c_res:
        # 1. Real Return Chart
        sub = df[df['FundCode']==f_sel]
        
        # Calculate Real Returns using Processor
        res = processor.calculate_real_returns(sub, inf_df)
        
        if not res.empty:
            fig_real = go.Figure()
            fig_real.add_trace(go.Scatter(x=res['Date'], y=res['Cumulative_Return'], name="Nominal (Görünen)", line=dict(color='#ef5350')))
            fig_real.add_trace(go.Scatter(x=res['Date'], y=res['Real_Return'], name="Reel (Net)", line=dict(color='#66bb6a', dash='dash'), fill='tonexty'))
            fig_real.update_layout(title=f"{f_sel} - Reel Getiri Analizi", template="plotly_dark", yaxis_tickformat='.1%')
            st.plotly_chart(fig_real, use_container_width=True, key="chart_real_return_main")
            
            # 2. Monthly Inflation Chart
            if 'Aylık Enflasyon' in inf_df.columns:
                st.markdown("##### 📉 Aylık Enflasyon Seyri")
                fig_inf = px.bar(inf_df, x='Date', y='Aylık Enflasyon', title="Aylık Enflasyon Oranları (%)", template="plotly_dark")
                fig_inf.update_traces(marker_color='#bfa15f')
                st.plotly_chart(fig_inf, use_container_width=True, key="chart_real_return_inflation")

