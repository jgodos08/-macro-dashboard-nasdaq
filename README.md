# Dashboard Macro — Qué mueve al Nasdaq

Dashboard en Streamlit para hacer seguimiento diario del contexto
macroeconómico que impacta al Nasdaq (tasas, dólar, VIX, inflación,
curva de rendimientos y calendario de la Fed).

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecutar

```bash
streamlit run app.py
```

Se abrirá automáticamente en tu navegador en `http://localhost:8501`.

## Secciones

1. **📈 Nasdaq** — Precio con medias móviles (20/50/200), Nasdaq 100 vs QQQ, volatilidad diaria.
2. **💵 Tasas & Dólar** — Curva de rendimientos del Tesoro (13W/5Y/10Y/30Y), spread de curva (señal de recesión), DXY, VIX.
3. **📉 Inflación & Macro (FRED)** — CPI, PCE, desempleo, Fed Funds Rate, M2, inflación breakeven. Requiere API key gratuita de FRED.
4. **🔗 Correlaciones** — Matriz de correlación y correlación móvil de 60 días entre Nasdaq y cada factor macro.
5. **🚦 Semáforo + Calendario Fed** — Heurística simple de contexto (favorable/adverso/mixto) + fechas confirmadas de reuniones FOMC 2026.

## API key de FRED (opcional pero recomendada)

Sin ella el dashboard funciona igual con datos de mercado (Yahoo Finance).
Con ella se agregan datos oficiales (CPI, PCE, desempleo, Fed Funds Rate, M2).

1. Regístrate gratis en: https://fred.stlouisfed.org/docs/api/api_key.html
2. Pega la key en la barra lateral del dashboard (no se guarda en ningún lado, solo vive en la sesión).

## Notas

- Los datos de mercado tienen ~15-20 minutos de rezago (Yahoo Finance gratuito).
- El "semáforo macro" es una heurística educativa, **no es una señal de trading ni asesoría financiera**.
- Verifica siempre las fechas de la Fed en federalreserve.gov, ya que cada reunión es tentativa hasta confirmarse en la reunión previa.

## Ideas para extender

- Agregar alertas por Telegram/WhatsApp cuando el VIX cruce cierto nivel.
- Guardar el histórico del "score" del semáforo en un CSV para backtesting simple.
- Añadir el spread de crédito corporativo (HYG/LQD) como otro factor de risk-on/risk-off.
