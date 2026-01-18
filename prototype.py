import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Swing Hunter Pro", layout="wide", page_icon="🏹")

# --- JUDUL & SIDEBAR ---
st.title("🏹 Swing Stock Hunter")
st.markdown("### Asisten Screening Saham Swing Trading")

st.sidebar.header("Konfigurasi Scanner")

# Input Ticker Saham
default_tickers = "PNLF, SCMA, BKSL, SMGR, HUMI, BBCA, ADRO, ANTM, BRMS, PANI"
ticker_input = st.sidebar.text_area("Masukkan Kode Saham (pisahkan koma):", value=default_tickers, height=100)

# Tombol Mulai
start_scan = st.sidebar.button("Mulai Scan Pasar", type="primary")

# --- FUNGSI ANALISIS (LOGIKA SWING) ---
def analyze_stock(ticker):
    # Auto-add .JK jika lupa
    if not ticker.endswith(".JK"):
        symbol = f"{ticker.upper()}.JK"
    else:
        symbol = ticker.upper()
    
    try:
        # Ambil data 6 bulan (biar chart enak dilihat)
        df = yf.download(symbol, period="6mo", interval="1d", progress=False)
        
        if len(df) < 20: return None

        # Indikator Teknikal
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['VolMA20'] = df['Volume'].rolling(window=20).mean()
        
        # RSI Calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # Data Terakhir
        last_close = float(df['Close'].iloc[-1])
        last_ma20 = float(df['MA20'].iloc[-1])
        last_rsi = float(df['RSI'].iloc[-1])
        last_vol = float(df['Volume'].iloc[-1])
        last_vol_ma = float(df['VolMA20'].iloc[-1])

        # Logika Sinyal (Sesuai Strategi Kita)
        status = "NEUTRAL"
        score = 0
        
        # 1. SWING BUY (Uptrend + Diskon)
        if last_close > last_ma20 and last_rsi < 55:
            status = "✅ SWING BUY (DIP)"
            score = 2
        # 2. BREAKOUT (Volume Meledak)
        elif last_vol > (1.5 * last_vol_ma) and last_close > last_ma20:
            status = "🚀 BREAKOUT"
            score = 3
        # 3. DOWNTREND (Bahaya)
        elif last_close < last_ma20:
            status = "❌ AVOID / DOWNTREND"
            score = -1

        return {
            "Ticker": symbol.replace(".JK", ""),
            "Harga": int(last_close),
            "MA20": int(last_ma20),
            "RSI": round(last_rsi, 2),
            "Vol Ratio": round(last_vol / last_vol_ma, 2),
            "Status": status,
            "Score": score, # Untuk sorting
            "History": df # Simpan data untuk charting
        }

    except Exception as e:
        return None

# --- FUNGSI CHARTING (PLOTLY) ---
def plot_chart(data_dict):
    df = data_dict['History']
    ticker = data_dict['Ticker']
    
    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'],
                name='Harga'))

    # MA20 Line
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], 
                             line=dict(color='orange', width=2), name='MA 20'))

    fig.update_layout(
        title=f"Chart {ticker} - {data_dict['Status']}",
        xaxis_title="Tanggal",
        yaxis_title="Harga",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_rangeslider_visible=False
    )
    return fig

# --- MAIN APP LOGIC ---
if start_scan:
    # 1. Parsing Input
    tickers_list = [t.strip() for t in ticker_input.split(',')]
    
    results = []
    progress_bar = st.progress(0)
    
    # 2. Scanning Loop
    for i, ticker in enumerate(tickers_list):
        if ticker:
            data = analyze_stock(ticker)
            if data:
                results.append(data)
        # Update progress bar
        progress_bar.progress((i + 1) / len(tickers_list))

    # 3. Display Results
    if results:
        df_results = pd.DataFrame(results)
        
        # Urutkan: Breakout > Swing Buy > Neutral > Avoid
        df_results = df_results.sort_values(by='Score', ascending=False)
        
        # Tampilkan Tabel Ringkasan
        st.subheader("📊 Hasil Screening")
        
        # Styling Tabel (Highlight Hijau/Merah)
        def color_status(val):
            color = 'white'
            if 'SWING BUY' in val: color = '#90ee90' # Light Green
            elif 'BREAKOUT' in val: color = '#00ff00' # Green
            elif 'AVOID' in val: color = '#ffcccb' # Red
            return f'background-color: {color}; color: black'

        st.dataframe(
            df_results[['Ticker', 'Harga', 'Status', 'RSI', 'Vol Ratio', 'MA20']]
            .style.applymap(color_status, subset=['Status']),
            use_container_width=True
        )

        # 4. Tampilkan Chart untuk Saham Potensial
        st.subheader("📈 Chart Analisis (Khusus Sinyal Buy)")
        
        col1, col2 = st.columns(2) # Bikin 2 kolom biar rapi
        
        potential_stocks = [r for r in results if r['Score'] > 0] # Ambil yg score positif
        
        for i, stock in enumerate(potential_stocks):
            # Tampilkan chart bergantian kiri-kanan
            with (col1 if i % 2 == 0 else col2):
                st.plotly_chart(plot_chart(stock), use_container_width=True)
                
                # Tambahan Advice
                if "SWING BUY" in stock['Status']:
                    st.success(f"💡 **Saran:** {stock['Ticker']} sedang Uptrend & Diskon (RSI {stock['RSI']}). Cek Broxsum untuk konfirmasi akumulasi!")
                elif "BREAKOUT" in stock['Status']:
                    st.warning(f"🔥 **Saran:** {stock['Ticker']} volume meledak ({stock['Vol Ratio']}x rata-rata). Cek Broxsum untuk melihat siapa bandarnya!!!")

    else:
        st.error("Tidak ada data ditemukan. Cek koneksi atau kode saham.")

else:
    st.info("👈 Masukkan kode saham di sidebar dan klik 'Mulai Scan Pasar'")
    st.markdown("""
    ### 📝 Cara Membaca Dashboard:
    1. **✅ SWING BUY (DIP):** Harga di atas MA20 (Uptrend) tapi RSI < 55 (Lagi Murah). **Strategi Favorit.**
    2. **🚀 BREAKOUT:** Harga naik & Volume meledak > 1.5x rata-rata.
    3. **❌ AVOID:** Harga di bawah MA20 (Downtrend). Jangan disentuh.
    
    ⚠️ **Peringatan:** Alat ini hanya melihat **Teknikal**. Wajib cek **Broxsum (Bandarmologi)** manual sebelum beli!
    """)

# --- DI DALAM APP.PY ---

# ... (Kode chart di atas) ...

st.markdown("---")
st.header("🕵️‍♂️ Bandar Detector (Kalkulator Manual)")

# Kita bagi kolom: Kiri Input, Kanan Hasil Analisis
col_input, col_result = st.columns([1, 1])

with col_input:
    with st.form("broxsum_form"):
        st.write("Masukkan Data Top 1/3 Broker (Dalam Miliar Rupiah)")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🟢 Top Buyer")
            buyer_val = st.number_input("Total Value Buyer (M)", min_value=0.0, step=0.1, help="Contoh: 15.5 Miliar")
            buyer_avg = st.number_input("Avg Price Buyer", min_value=0, step=1)
        
        with c2:
            st.markdown("### 🔴 Top Seller")
            seller_val = st.number_input("Total Value Seller (M)", min_value=0.0, step=0.1, help="Contoh: 10.2 Miliar")
            seller_avg = st.number_input("Avg Price Seller", min_value=0, step=1)
            
        submitted = st.form_submit_button("Analisis Bandarmologi")

with col_result:
    if submitted:
        # 1. Hitung Net
        net_val = buyer_val - seller_val
        
        # 2. Tentukan Status
        if net_val > 0:
            status = "BIG ACCUMULATION" if net_val > 5 else "SMALL ACCUMULATION"
            color = "green"
            emoji = "bull" # Custom logic visual
        elif net_val < 0:
            status = "BIG DISTRIBUTION" if net_val < -5 else "SMALL DISTRIBUTION"
            color = "red"
            emoji = "bear"
        else:
            status = "NEUTRAL"
            color = "gray"
            
        # 3. Tampilkan Visual HTML Keren
        st.markdown(f"""
        <div style="
            background-color: #1E1E1E;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 2px solid {color};
        ">
            <h2 style="color: white; margin:0;">VONIS:</h2>
            <h1 style="color: {color}; margin:0; font-size: 3em;">{status}</h1>
            <h3 style="color: white;">Net Flow: Rp {net_val:.1f} Miliar</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # 4. Analisis Avg Price (Posisi Bandar)
        if buyer_avg > 0:
            # Hitung Jarak Harga Sekarang vs Modal Bandar
            # (Asumsi kita ambil harga terakhir dari variabel global 'last_close' kalau ada, 
            #  atau manual input harga sekarang)
            st.info(f"💡 **Insight:** Modal Buyer di {buyer_avg}. Jika harga sekarang di bawah {buyer_avg}, Bandar sedang Floating Loss (Potensi Rebound).")

    else:
        st.info("👈 Masukkan data dari aplikasi sekuritas Anda untuk melihat analisis.")