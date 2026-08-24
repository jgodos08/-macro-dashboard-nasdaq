# -*- coding: utf-8 -*-
"""
Dashboard Macro para Nasdaq
============================
Dashboard en Streamlit para visualizar las variables macroeconómicas
que más mueven al Nasdaq: tasas de interés, dólar (DXY), volatilidad (VIX),
inflación, curva de rendimientos y calendario de la Fed.

Cómo correrlo:
    pip install -r requirements.txt
    streamlit run app.py

Autor: generado con Claude para Tathiana.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta

# ----------------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Macro Dashboard · Nasdaq",
    layout="wide",
    page_icon="📊",
)

TICKERS = {
    "Nasdaq Composite": "^IXIC",
    "Nasdaq 100": "^NDX",
    "QQQ (ETF)": "QQQ",
    "10Y Treasury Yield": "^TNX",   # en décimas: 45.0 => 4.50%
    "5Y Treasury Yield": "^FVX",
    "30Y Treasury Yield": "^TYX",
    "13W T-Bill (proxy corto plazo)": "^IRX",
    "Dollar Index (DXY)": "DX-Y.NYB",
    "VIX": "^VIX",
    "Oro": "GC=F",
    "Petróleo WTI": "CL=F",
}

# Calendario FOMC 2026 (confirmado por la Fed; los ítems con * incluyen
# proyecciones económicas / dot plot, suelen tener mayor impacto).
FOMC_2026 = [
    ("27-28 Ene 2026", False),
    ("17-18 Mar 2026", True),
    ("28-29 Abr 2026", False),
    ("16-17 Jun 2026", True),
    ("28-29 Jul 2026", False),
    ("15-16 Sep 2026", True),
    ("27-28 Oct 2026", False),
    ("08-09 Dic 2026", True),
]

FRED_SERIES = {
    "CPI (Índice de precios al consumidor)": "CPIAUCSL",
    "PCE (Gasto en consumo personal, precios)": "PCEPI",
    "Tasa de desempleo": "UNRATE",
    "Fed Funds Rate (efectiva)": "DFF",
    "Treasury 2Y": "DGS2",
    "Treasury 10Y": "DGS10",
    "Spread 10Y-2Y": "T10Y2Y",
    "Inflación breakeven 10Y": "T10YIE",
    "Oferta monetaria M2": "M2SL",
}

# ----------------------------------------------------------------------------
# FUNCIONES DE DATOS
# ----------------------------------------------------------------------------


@st.cache_data(ttl=900, show_spinner=False)
def fetch_yf(ticker: str, period: str = "2y", interval: str = "1d"):
    """Descarga datos de Yahoo Finance y devuelve una Serie de cierre limpia."""
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return None
        # yfinance a veces devuelve columnas MultiIndex (Ticker, Campo)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df["Close"].dropna()
        close.name = ticker
        return close
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fred(series_id: str, api_key: str, start: str = "2018-01-01"):
    """Descarga una serie de FRED (requiere API key gratuita)."""
    if not api_key:
        return None
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()["observations"]
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"]).set_index("date")["value"]
        df.name = series_id
        return df
    except Exception:
        return None


def pct_change_last(series: pd.Series, days: int = 1):
    """Cambio porcentual entre el último dato y N periodos atrás."""
    if series is None or len(series) < days + 1:
        return None
    return (series.iloc[-1] / series.iloc[-1 - days] - 1) * 100


def trend_arrow(delta):
    if delta is None:
        return "—"
    if delta > 0:
        return "🔺"
    if delta < 0:
        return "🔻"
    return "➖"


# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------

st.sidebar.title("⚙️ Configuración")

period_label = st.sidebar.selectbox(
    "Rango histórico",
    ["6mo", "1y", "2y", "5y", "10y"],
    index=2,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 FRED API (opcional)")
st.sidebar.caption(
    "Sin esta clave el dashboard funciona igual usando datos de mercado "
    "(Yahoo Finance). Con una API key gratuita de FRED "
    "(https://fred.stlouisfed.org/docs/api/api_key.html) se agregan datos "
    "oficiales: CPI, desempleo, Fed Funds Rate, M2 y el spread 10Y-2Y exacto."
)
fred_key = st.sidebar.text_input("FRED API Key", type="password")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Los datos de mercado tienen ~15-20 min de rezago. Este dashboard es "
    "una herramienta informativa de contexto macro, no constituye "
    "asesoría financiera ni una señal de entrada/salida."
)

# ----------------------------------------------------------------------------
# DESCARGA DE DATOS BASE
# ----------------------------------------------------------------------------

with st.spinner("Descargando datos de mercado..."):
    data = {name: fetch_yf(tkr, period=period_label) for name, tkr in TICKERS.items()}

nasdaq = data["Nasdaq Composite"]
ndx = data["Nasdaq 100"]
qqq = data["QQQ (ETF)"]
y10 = data["10Y Treasury Yield"]
y5 = data["5Y Treasury Yield"]
y30 = data["30Y Treasury Yield"]
tbill = data["13W T-Bill (proxy corto plazo)"]
dxy = data["Dollar Index (DXY)"]
vix = data["VIX"]
gold = data["Oro"]
oil = data["Petróleo WTI"]

fred_data = {}
if fred_key:
    with st.spinner("Descargando datos de FRED..."):
        for name, sid in FRED_SERIES.items():
            fred_data[name] = fetch_fred(sid, fred_key)

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------

st.title("📊 Dashboard Macro — Qué mueve al Nasdaq")
st.caption(
    f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
    "Fuente de mercado: Yahoo Finance" + (" + FRED" if fred_key else "")
)

if nasdaq is None:
    st.error(
        "No se pudo descargar la data del Nasdaq. Revisa tu conexión a "
        "internet o intenta de nuevo en unos minutos."
    )
    st.stop()

col1, col2, col3, col4, col5 = st.columns(5)

def metric_from_series(col, label, series, fmt="{:.2f}"):
    if series is None or len(series) < 2:
        col.metric(label, "N/D")
        return
    last = series.iloc[-1]
    delta = pct_change_last(series, 1)
    col.metric(label, fmt.format(last), f"{delta:+.2f}%" if delta is not None else None)

metric_from_series(col1, "Nasdaq Composite", nasdaq)
metric_from_series(col2, "Nasdaq 100", ndx)
metric_from_series(col3, "VIX", vix)
metric_from_series(col4, "DXY (Dólar)", dxy)
metric_from_series(col5, "10Y Yield (%)", y10 / 10 if y10 is not None else None)

st.markdown("---")

# ----------------------------------------------------------------------------
# TABS
# ----------------------------------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📈 Nasdaq",
        "💵 Tasas & Dólar",
        "📉 Inflación & Macro (FRED)",
        "🔗 Correlaciones",
        "🚦 Semáforo + Calendario Fed",
    ]
)

# ---- TAB 1: NASDAQ ----------------------------------------------------------
with tab1:
    st.subheader("Nasdaq Composite con medias móviles")
    df_n = nasdaq.to_frame("Close")
    df_n["SMA20"] = df_n["Close"].rolling(20).mean()
    df_n["SMA50"] = df_n["Close"].rolling(50).mean()
    df_n["SMA200"] = df_n["Close"].rolling(200).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_n.index, y=df_n["Close"], name="Nasdaq Composite", line=dict(color="#1f77b4")))
    fig.add_trace(go.Scatter(x=df_n.index, y=df_n["SMA20"], name="SMA 20", line=dict(color="orange", width=1)))
    fig.add_trace(go.Scatter(x=df_n.index, y=df_n["SMA50"], name="SMA 50", line=dict(color="green", width=1)))
    fig.add_trace(go.Scatter(x=df_n.index, y=df_n["SMA200"], name="SMA 200", line=dict(color="red", width=1)))
    fig.update_layout(height=480, hovermode="x unified", legend=dict(orientation="h", y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    colA, colB = st.columns(2)
    with colA:
        st.markdown("**Nasdaq 100 vs QQQ (normalizado, base 100)**")
        if ndx is not None and qqq is not None:
            norm = pd.concat([ndx, qqq], axis=1).dropna()
            norm = norm / norm.iloc[0] * 100
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=norm.index, y=norm.iloc[:, 0], name="Nasdaq 100"))
            fig2.add_trace(go.Scatter(x=norm.index, y=norm.iloc[:, 1], name="QQQ"))
            fig2.update_layout(height=350, hovermode="x unified")
            st.plotly_chart(fig2, use_container_width=True)
    with colB:
        st.markdown("**Volatilidad realizada (retorno diario %, 30 días)**")
        rets = nasdaq.pct_change().dropna() * 100
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=rets.index[-30:], y=rets.iloc[-30:], marker_color="#636EFA"))
        fig3.update_layout(height=350)
        st.plotly_chart(fig3, use_container_width=True)

# ---- TAB 2: TASAS Y DÓLAR ---------------------------------------------------
with tab2:
    st.subheader("Curva de rendimientos y tasas del Tesoro de EE.UU.")
    st.caption(
        "Los tickers ^TNX, ^FVX, ^TYX, ^IRX de Yahoo Finance vienen en "
        "décimas de punto porcentual (dividir entre 10)."
    )

    yields_df = pd.concat(
        {
            "13W (corto plazo)": tbill / 10 if tbill is not None else None,
            "5Y": y5 / 10 if y5 is not None else None,
            "10Y": y10 / 10 if y10 is not None else None,
            "30Y": y30 / 10 if y30 is not None else None,
        },
        axis=1,
    ).dropna(how="all")

    fig4 = go.Figure()
    for col in yields_df.columns:
        fig4.add_trace(go.Scatter(x=yields_df.index, y=yields_df[col], name=col))
    fig4.update_layout(height=420, hovermode="x unified", yaxis_title="% anual")
    st.plotly_chart(fig4, use_container_width=True)

    st.markdown("#### Spread de la curva (señal de recesión)")
    if fred_key and fred_data.get("Spread 10Y-2Y") is not None:
        spread = fred_data["Spread 10Y-2Y"]
        src_note = "Fuente: FRED (T10Y2Y), 10Y menos 2Y — el spread clásico."
    elif y10 is not None and tbill is not None:
        merged = pd.concat([y10 / 10, tbill / 10], axis=1).dropna()
        spread = merged.iloc[:, 0] - merged.iloc[:, 1]
        src_note = (
            "Fuente: Yahoo Finance. Como no se cargó FRED, se usa 10Y menos "
            "T-Bill 13 semanas (spread 10Y-3M), otro indicador de curva muy "
            "seguido por la Fed de NY para señales de recesión."
        )
    else:
        spread = None
        src_note = ""

    if spread is not None:
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=spread.index, y=spread, fill="tozeroy", name="Spread"))
        fig5.add_hline(y=0, line_dash="dash", line_color="red")
        fig5.update_layout(height=320, hovermode="x unified")
        st.plotly_chart(fig5, use_container_width=True)
        st.caption(src_note + " Spread negativo (curva invertida) suele anticipar recesión.")

    st.markdown("---")
    st.subheader("Dollar Index (DXY)")
    st.caption("Dólar fuerte suele presionar a la baja a las tecnológicas con ingresos globales; dólar débil suele favorecer al Nasdaq.")
    if dxy is not None:
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(x=dxy.index, y=dxy, name="DXY", line=dict(color="#2ca02c")))
        fig6.update_layout(height=350, hovermode="x unified")
        st.plotly_chart(fig6, use_container_width=True)

    st.subheader("VIX — índice de volatilidad / miedo")
    if vix is not None:
        fig7 = go.Figure()
        fig7.add_trace(go.Scatter(x=vix.index, y=vix, name="VIX", line=dict(color="#d62728")))
        fig7.add_hline(y=20, line_dash="dot", line_color="orange", annotation_text="Zona de nerviosismo (20)")
        fig7.add_hline(y=30, line_dash="dot", line_color="red", annotation_text="Zona de pánico (30)")
        fig7.update_layout(height=350, hovermode="x unified")
        st.plotly_chart(fig7, use_container_width=True)

# ---- TAB 3: INFLACIÓN / MACRO FRED -----------------------------------------
with tab3:
    if not fred_key:
        st.info(
            "Ingresa una API key gratuita de FRED en la barra lateral para "
            "ver CPI, PCE, desempleo, Fed Funds Rate y M2. Regístrate gratis "
            "en https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    else:
        cpi = fred_data.get("CPI (Índice de precios al consumidor)")
        pce = fred_data.get("PCE (Gasto en consumo personal, precios)")
        unrate = fred_data.get("Tasa de desempleo")
        fedfunds = fred_data.get("Fed Funds Rate (efectiva)")
        m2 = fred_data.get("Oferta monetaria M2")
        breakeven = fred_data.get("Inflación breakeven 10Y")

        colX, colY = st.columns(2)
        with colX:
            st.markdown("**CPI interanual (% YoY)**")
            if cpi is not None:
                cpi_yoy = cpi.pct_change(12) * 100
                fig8 = go.Figure()
                fig8.add_trace(go.Scatter(x=cpi_yoy.index, y=cpi_yoy, name="CPI YoY"))
                fig8.add_hline(y=2, line_dash="dash", line_color="green", annotation_text="Meta Fed 2%")
                fig8.update_layout(height=330, hovermode="x unified")
                st.plotly_chart(fig8, use_container_width=True)
        with colY:
            st.markdown("**PCE interanual (% YoY) — el que más mira la Fed**")
            if pce is not None:
                pce_yoy = pce.pct_change(12) * 100
                fig9 = go.Figure()
                fig9.add_trace(go.Scatter(x=pce_yoy.index, y=pce_yoy, name="PCE YoY", line=dict(color="purple")))
                fig9.add_hline(y=2, line_dash="dash", line_color="green", annotation_text="Meta Fed 2%")
                fig9.update_layout(height=330, hovermode="x unified")
                st.plotly_chart(fig9, use_container_width=True)

        colZ, colW = st.columns(2)
        with colZ:
            st.markdown("**Tasa de desempleo (%)**")
            if unrate is not None:
                fig10 = go.Figure()
                fig10.add_trace(go.Scatter(x=unrate.index, y=unrate, name="Desempleo", line=dict(color="brown")))
                fig10.update_layout(height=300, hovermode="x unified")
                st.plotly_chart(fig10, use_container_width=True)
        with colW:
            st.markdown("**Fed Funds Rate efectiva (%)**")
            if fedfunds is not None:
                fig11 = go.Figure()
                fig11.add_trace(go.Scatter(x=fedfunds.index, y=fedfunds, name="Fed Funds", line=dict(color="black")))
                fig11.update_layout(height=300, hovermode="x unified")
                st.plotly_chart(fig11, use_container_width=True)

        st.markdown("**Oferta monetaria M2 (miles de millones USD)**")
        if m2 is not None:
            fig12 = go.Figure()
            fig12.add_trace(go.Scatter(x=m2.index, y=m2, name="M2", fill="tozeroy"))
            fig12.update_layout(height=300, hovermode="x unified")
            st.plotly_chart(fig12, use_container_width=True)

        st.markdown("**Expectativa de inflación a 10 años (breakeven)**")
        if breakeven is not None:
            fig13 = go.Figure()
            fig13.add_trace(go.Scatter(x=breakeven.index, y=breakeven, name="Breakeven 10Y"))
            fig13.update_layout(height=300, hovermode="x unified")
            st.plotly_chart(fig13, use_container_width=True)

# ---- TAB 4: CORRELACIONES ---------------------------------------------------
with tab4:
    st.subheader("Correlación del Nasdaq con las variables macro")
    factors = {
        "Nasdaq": nasdaq,
        "DXY": dxy,
        "VIX": vix,
        "10Y Yield": y10,
        "Oro": gold,
        "Petróleo": oil,
    }
    combined = pd.concat(factors, axis=1).dropna()
    combined.columns = list(factors.keys())
    rets = combined.pct_change().dropna()

    if len(rets) > 30:
        corr = rets.corr()
        fig14 = go.Figure(
            data=go.Heatmap(
                z=corr.values,
                x=corr.columns,
                y=corr.columns,
                colorscale="RdBu",
                zmid=0,
                text=np.round(corr.values, 2),
                texttemplate="%{text}",
            )
        )
        fig14.update_layout(height=480, title="Matriz de correlación (retornos diarios, período seleccionado)")
        st.plotly_chart(fig14, use_container_width=True)

        st.markdown("**Correlación móvil de 60 días: Nasdaq vs cada factor**")
        window = 60
        roll_corr = pd.DataFrame(
            {
                col: rets["Nasdaq"].rolling(window).corr(rets[col])
                for col in rets.columns
                if col != "Nasdaq"
            }
        )
        fig15 = go.Figure()
        for col in roll_corr.columns:
            fig15.add_trace(go.Scatter(x=roll_corr.index, y=roll_corr[col], name=col))
        fig15.add_hline(y=0, line_dash="dash", line_color="gray")
        fig15.update_layout(height=400, hovermode="x unified", yaxis_title="Correlación")
        st.plotly_chart(fig15, use_container_width=True)

        st.caption(
            "Lectura rápida: el Nasdaq suele correlacionar negativamente con "
            "DXY, VIX y 10Y Yield (dólar fuerte, miedo alto o tasas subiendo "
            "suelen presionarlo a la baja), y positivamente con el apetito "
            "por riesgo general. Estas correlaciones no son estables: cambian "
            "según el régimen de mercado."
        )
    else:
        st.warning("No hay suficientes datos superpuestos en el rango seleccionado para calcular correlaciones.")

# ---- TAB 5: SEMÁFORO + CALENDARIO FED ---------------------------------------
with tab5:
    st.subheader("🚦 Semáforo macro (heurística simple, no es una señal de trading)")
    st.caption(
        "Este semáforo es solo una ayuda visual de contexto: resume la "
        "tendencia de 5 días de las variables clave. No reemplaza tu plan "
        "de trading ni tu gestión de riesgo, y no constituye asesoría "
        "financiera."
    )

    score = 0
    details = []

    d10y = pct_change_last(y10, 5)
    if d10y is not None:
        pts = -1 if d10y > 0 else 1
        score += pts
        details.append(("10Y Yield (5 días)", f"{d10y:+.2f}%", trend_arrow(d10y), "Tasas subiendo presiona al Nasdaq" if d10y > 0 else "Tasas bajando favorece al Nasdaq"))

    ddxy = pct_change_last(dxy, 5)
    if ddxy is not None:
        pts = -1 if ddxy > 0 else 1
        score += pts
        details.append(("DXY (5 días)", f"{ddxy:+.2f}%", trend_arrow(ddxy), "Dólar fuerte presiona al Nasdaq" if ddxy > 0 else "Dólar débil favorece al Nasdaq"))

    dvix = pct_change_last(vix, 5)
    vix_level = vix.iloc[-1] if vix is not None else None
    if dvix is not None:
        pts = -1 if dvix > 0 else 1
        score += pts
        details.append(("VIX (5 días)", f"{dvix:+.2f}%", trend_arrow(dvix), "Miedo subiendo, riesgo de más caídas" if dvix > 0 else "Miedo bajando, contexto más favorable"))

    if spread is not None and len(spread) > 0:
        curve_val = spread.iloc[-1]
        pts = -1 if curve_val < 0 else 1
        score += pts
        details.append(("Curva de rendimientos", f"{curve_val:+.2f} pts", "🔴" if curve_val < 0 else "🟢", "Curva invertida = señal de recesión" if curve_val < 0 else "Curva no invertida"))

    for label, val, arrow, note in details:
        c1, c2, c3 = st.columns([2, 1, 4])
        c1.markdown(f"**{label}**")
        c2.markdown(f"{arrow} {val}")
        c3.caption(note)

    st.markdown("---")
    if score >= 2:
        st.success(f"Score: {score} → Contexto macro relativamente FAVORABLE para el Nasdaq")
    elif score <= -2:
        st.error(f"Score: {score} → Contexto macro relativamente ADVERSO para el Nasdaq")
    else:
        st.warning(f"Score: {score} → Contexto macro MIXTO / neutral")

    st.markdown("---")
    st.subheader("📅 Calendario FOMC 2026")
    st.caption(
        "Fechas confirmadas de las reuniones de la Reserva Federal en 2026. "
        "Las marcadas con ⭐ incluyen proyecciones económicas y el 'dot plot', "
        "suelen generar más volatilidad. Verificar siempre en federalreserve.gov "
        "porque cada fecha es tentativa hasta confirmarse en la reunión previa."
    )
    for fecha, tiene_proyecciones in FOMC_2026:
        marca = "⭐" if tiene_proyecciones else "—"
        st.markdown(f"- **{fecha}** {marca}")

    st.caption(
        "Recuerda: NFP (Nóminas no agrícolas) sale el primer viernes de cada "
        "mes, CPI a mitad de mes, y el discurso de Jackson Hole suele ser en "
        "agosto — todos eventos de alta volatilidad para el Nasdaq."
    )

st.markdown("---")
st.caption(
    "Dashboard educativo/informativo. Datos de mercado vía Yahoo Finance "
    "(yfinance) y datos oficiales vía FRED (Federal Reserve Economic Data). "
    "No constituye asesoría de inversión."
)
