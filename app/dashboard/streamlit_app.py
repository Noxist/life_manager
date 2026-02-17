"""
Streamlit Bio-Dashboard -- Leandro Edition.
Hauptseite: Schnelle Inputs (Einnahme, Befinden, Essen).
Sidebar (Hamburger): Kurven, Vitals, Modell, Analyse, System.
Mobile-first, no emojis.
"""

import json
from datetime import datetime, timedelta, time as dt_time

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import os

# --- Config ---
API_BASE = os.getenv("BIO_API_URL", "http://localhost:8000")
API_KEY = os.getenv("BIO_API_KEY", "")
HEADERS = {"x-api-key": API_KEY} if API_KEY else {}


def api_get(path: str, params: dict | None = None) -> dict | list:
    try:
        r = httpx.get(f"{API_BASE}{path}", params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return {}


def api_post(path: str, data: dict) -> dict:
    try:
        r = httpx.post(f"{API_BASE}{path}", json=data, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return {}


def api_delete(path: str) -> dict:
    try:
        r = httpx.delete(f"{API_BASE}{path}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return {}


# --- Page Config ---
st.set_page_config(
    page_title="Bio-Dashboard",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Mobile-first CSS
st.markdown("""
<style>
    .block-container {
        padding-top: 0.3rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        max-width: 100%;
    }
    div[data-testid="stMetric"] {
        background-color: #1e1e2e;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 8px 10px;
    }
    div[data-testid="stMetric"] label { font-size: 0.7rem; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.3rem; }
    .stButton > button {
        min-height: 52px;
        font-size: 1rem;
        border-radius: 10px;
    }
    section[data-testid="stSidebar"] { width: 280px !important; }
    hr { margin-top: 0.4rem; margin-bottom: 0.4rem; }
    [data-testid="column"] { padding: 0 3px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# SIDEBAR -- Hamburger Menu (Detail-Ansichten)
# =========================================================
PAGES = ["Logging", "Kurven & Timeline", "Vitals & Health", "Persoenl. Modell", "Korrelation", "System"]
PAGE_MAP = {
    "Logging": "main",
    "Kurven & Timeline": "kurven",
    "Vitals & Health": "vitals",
    "Persoenl. Modell": "modell",
    "Korrelation": "korrelation",
    "System": "system",
}

with st.sidebar:
    st.header("Bio-Dashboard")
    sidebar_page = st.radio("Navigation", PAGES, index=0, label_visibility="collapsed")
    st.divider()
    # Quick bio-score in sidebar
    bio_sidebar = api_get("/api/bio-score")
    if isinstance(bio_sidebar, dict) and "score" in bio_sidebar:
        sc = bio_sidebar["score"]
        ph = bio_sidebar.get("phase", "?")
        st.metric("Bio-Score", f"{sc:.0f}/100")
        st.caption(f"Phase: {ph}")
        cns = bio_sidebar.get("cns_load", 0)
        if cns > 1.5:
            st.warning(f"CNS-Last: {cns:.1f}")

current_page = PAGE_MAP.get(sidebar_page, "main")


# =========================================================
# PAGE: Main Logging (default)
# =========================================================
if current_page == "main":
    # --- Log Reminder ---
    reminder = api_get("/api/log-reminder")
    if isinstance(reminder, dict) and reminder.get("next_due"):
        next_due = reminder["next_due"]
        logs_done = reminder.get("logs_today", 0)
        target_logs = reminder.get("target_logs", 5)

        progress = min(logs_done / max(target_logs, 1), 1.0)
        st.progress(progress, text=f"Logs: {logs_done}/{target_logs}")

        if next_due["status"] == "due":
            st.warning(f"Log faellig: {next_due['label']} ({next_due['target_time']})")
        else:
            st.info(f"Naechster Log: {next_due['label']} um {next_due['target_time']}")

    # ---- SECTION 1: Einnahme ----
    st.subheader("1 -- Einnahme")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("Elvanse 40mg", use_container_width=True, type="primary"):
            r = api_post("/api/intake", {"substance": "elvanse", "dose_mg": 40})
            if r.get("status") == "ok":
                st.success("Elvanse geloggt")
                st.rerun()
    with b2:
        if st.button("Lamate 76mg", use_container_width=True, type="primary"):
            r = api_post("/api/intake", {"substance": "mate", "dose_mg": 76})
            if r.get("status") == "ok":
                st.success("Lamate geloggt")
                st.rerun()

    b3, b4 = st.columns(2)
    with b3:
        if st.button("Lamate x2", use_container_width=True):
            r = api_post("/api/intake", {"substance": "mate", "dose_mg": 152})
            if r.get("status") == "ok":
                st.success("Doppel-Lamate geloggt")
                st.rerun()
    with b4:
        if st.button("Medikinet 10mg", use_container_width=True):
            r = api_post("/api/intake", {"substance": "medikinet", "dose_mg": 10})
            if r.get("status") == "ok":
                st.success("Medikinet geloggt")
                st.rerun()

    with st.expander("Nachtragen / Andere"):
        hc1, hc2 = st.columns(2)
        with hc1:
            hist_sub = st.selectbox("Substanz", ["elvanse", "mate", "medikinet", "medikinet_retard", "other"], key="hsub")
        with hc2:
            dmap = {"elvanse": 40.0, "mate": 76.0, "medikinet": 10.0, "medikinet_retard": 30.0, "other": 0.0}
            hist_dose = st.number_input("mg", min_value=0.0, step=10.0, value=dmap.get(hist_sub, 0.0), key="hdose")
        dc1, dc2 = st.columns(2)
        with dc1:
            hdate = st.date_input("Datum", value=datetime.now().date(), key="hdate")
        with dc2:
            htime = st.time_input("Uhrzeit", value=datetime.now().time().replace(second=0, microsecond=0), key="htime")
        if st.button("Nachtragen", type="primary", use_container_width=True):
            ts = datetime.combine(hdate, htime).isoformat()
            r = api_post("/api/intake", {"substance": hist_sub, "dose_mg": hist_dose or None, "timestamp": ts})
            if r.get("status") == "ok":
                st.success("Nachgetragen")
                st.rerun()

    # ---- SECTION 2: Wie fuehle ich mich ----
    st.divider()
    st.subheader("2 -- Wie fuehlst du dich?")

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        focus = st.slider("Fokus", 1, 10, 5, key="f")
    with fc2:
        mood = st.slider("Laune", 1, 10, 5, key="m")
    with fc3:
        energy = st.slider("Energie", 1, 10, 5, key="e")

    fc4, fc5 = st.columns(2)
    with fc4:
        appetite = st.slider("Appetit", 1, 10, 5, key="a")
    with fc5:
        inner_unrest = st.slider("Innere Unruhe", 1, 10, 1, key="u")

    tag_options = [
        "migraene", "kopfschmerzen", "uebelkeit",
        "muede", "unruhig", "motiviert",
        "klar", "brain-fog", "angespannt", "entspannt",
        "kreativ", "gereizt", "produktiv", "abgelenkt",
    ]
    tags = st.multiselect("Tags (optional)", tag_options, key="tags")

    if st.button("Bewertung speichern", type="primary", use_container_width=True):
        r = api_post("/api/log", {
            "focus": focus, "mood": mood, "energy": energy,
            "appetite": appetite, "inner_unrest": inner_unrest,
            "tags": tags,
        })
        if r.get("status") == "ok":
            st.success("Gespeichert")
            st.rerun()

    # ---- SECTION 3: Essen ----
    st.divider()
    st.subheader("3 -- Essen")
    meal_notes = st.text_input("Was? (optional)", key="mnotes", placeholder="Pizza, Salat...")
    ec1, ec2 = st.columns(2)
    with ec1:
        if st.button("Mittagessen", use_container_width=True):
            r = api_post("/api/meal", {"meal_type": "mittagessen", "notes": meal_notes})
            if r.get("status") == "ok":
                st.success("Mittagessen geloggt")
                st.rerun()
        if st.button("Fruehstueck", use_container_width=True):
            r = api_post("/api/meal", {"meal_type": "fruehstueck", "notes": meal_notes})
            if r.get("status") == "ok":
                st.success("Fruehstueck geloggt")
                st.rerun()
    with ec2:
        if st.button("Abendessen", use_container_width=True):
            r = api_post("/api/meal", {"meal_type": "abendessen", "notes": meal_notes})
            if r.get("status") == "ok":
                st.success("Abendessen geloggt")
                st.rerun()
        if st.button("Snack", use_container_width=True):
            r = api_post("/api/meal", {"meal_type": "snack", "notes": meal_notes})
            if r.get("status") == "ok":
                st.success("Snack geloggt")
                st.rerun()

    # ---- Heutiger Verlauf (kompakt) ----
    st.divider()
    st.subheader("Heute")
    tc1, tc2 = st.columns(2)
    with tc1:
        st.caption("Intakes")
        intakes = api_get("/api/intake", {"today": True})
        if isinstance(intakes, list) and intakes:
            for i in intakes:
                ts = i.get("timestamp", "")[11:16]
                sub = i.get("substance", "?")
                dose = i.get("dose_mg", "")
                lbl = {"elvanse": "ELV", "mate": "MAT", "medikinet": "MED", "medikinet_retard": "MR"}.get(sub, sub[:3].upper())
                iid = i.get("id")
                ec, dc = st.columns([5, 1])
                with ec:
                    st.text(f"{ts} [{lbl}] {dose}mg")
                with dc:
                    if st.button("X", key=f"di_{iid}"):
                        api_delete(f"/api/intake/{iid}")
                        st.rerun()
        else:
            st.caption("--")

    with tc2:
        st.caption("Logs")
        logs = api_get("/api/log", {"today": True})
        if isinstance(logs, list) and logs:
            for lg in logs:
                ts = lg.get("timestamp", "")[11:16]
                lid = lg.get("id")
                f = lg.get("focus", "?")
                m = lg.get("mood", "?")
                e = lg.get("energy", "?")
                a = lg.get("appetite", "-")
                u = lg.get("inner_unrest", "-")
                ec, dc = st.columns([5, 1])
                with ec:
                    st.text(f"{ts} F:{f} M:{m} E:{e} A:{a} U:{u}")
                with dc:
                    if st.button("X", key=f"dl_{lid}"):
                        api_delete(f"/api/log/{lid}")
                        st.rerun()
        else:
            st.caption("--")

    # Meals today
    meals = api_get("/api/meal", {"today": "true"})
    if isinstance(meals, list) and meals:
        st.caption("Mahlzeiten")
        for meal in meals:
            ts = meal.get("timestamp", "")[11:16]
            mt = meal.get("meal_type", "?")
            mn = meal.get("notes", "")
            mid = meal.get("id")
            ns = f" ({mn})" if mn else ""
            ec, dc = st.columns([5, 1])
            with ec:
                st.text(f"{ts} {mt}{ns}")
            with dc:
                if st.button("X", key=f"dm_{mid}"):
                    api_delete(f"/api/meal/{mid}")
                    st.rerun()


# =========================================================
# PAGE: Kurven & Timeline
# =========================================================
if current_page == "kurven":
    st.header("Kurven & Timeline")

    date = st.date_input("Datum", value=datetime.now().date(), key="tl_date")
    date_str = date.isoformat()

    curve_data = api_get("/api/bio-score/curve", {"date": date_str, "interval": 15})

    if isinstance(curve_data, dict) and "points" in curve_data:
        points = curve_data["points"]
        df = pd.DataFrame(points)

        if not df.empty:
            df["time"] = pd.to_datetime(df["timestamp"])
            now = datetime.now()
            is_today = date == now.date()

            # -- Bio-Score + Substanz-Kurven --
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["time"], y=df["score"],
                mode="lines", name="Bio-Score",
                line=dict(color="#4CAF50", width=3),
                fill="tozeroy", fillcolor="rgba(76,175,80,0.08)",
            ))
            fig.add_trace(go.Scatter(
                x=df["time"], y=df["circadian"],
                mode="lines", name="Circadian",
                line=dict(color="#9E9E9E", width=1, dash="dot"),
            ))
            fig.add_trace(go.Scatter(
                x=df["time"], y=df["elvanse_boost"],
                mode="lines", name="Elvanse",
                line=dict(color="#2196F3", width=2),
            ))
            if "medikinet_boost" in df.columns:
                fig.add_trace(go.Scatter(
                    x=df["time"], y=df["medikinet_boost"],
                    mode="lines", name="Medikinet",
                    line=dict(color="#AB47BC", width=2),
                ))
            fig.add_trace(go.Scatter(
                x=df["time"], y=df["caffeine_boost"],
                mode="lines", name="Koffein",
                line=dict(color="#FF9800", width=2),
            ))

            def _vmark(fig, x, color, dash, w, text, pos="top right"):
                fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1,
                    yref="paper", line=dict(color=color, width=w, dash=dash))
                fig.add_annotation(x=x, y=1, yref="paper", text=text,
                    showarrow=False, font=dict(color=color, size=9),
                    xanchor="left" if "left" in pos else "right", yanchor="bottom")

            if is_today:
                _vmark(fig, now, "#F44336", "solid", 2, "Jetzt", "top left")

            # Intake markers
            day_intakes = api_get("/api/intake", {"start": f"{date_str}T00:00:00", "end": f"{date_str}T23:59:59"})
            if isinstance(day_intakes, list):
                cmap = {"elvanse": "#2196F3", "mate": "#FF9800", "medikinet": "#AB47BC", "medikinet_retard": "#7B1FA2"}
                lmap = {"elvanse": "ELV", "mate": "MAT", "medikinet": "MED", "medikinet_retard": "MR"}
                for itk in day_intakes:
                    t = itk["timestamp"]
                    s = itk.get("substance", "?")
                    d = itk.get("dose_mg", "")
                    _vmark(fig, t, cmap.get(s, "#9C27B0"), "dash", 1, f"{lmap.get(s, s[:3])} {d}mg")

            # Fokus diamonds
            day_logs = api_get("/api/log", {"start": f"{date_str}T00:00:00", "end": f"{date_str}T23:59:59"})
            if isinstance(day_logs, list):
                for lg in day_logs:
                    t = pd.to_datetime(lg["timestamp"])
                    foc = lg.get("focus", 5)
                    fig.add_trace(go.Scatter(
                        x=[t], y=[foc * 10], mode="markers",
                        marker=dict(size=12, color="#E91E63", symbol="diamond"),
                        showlegend=False, hovertext=f"Fokus: {foc}/10",
                    ))

            fig.update_layout(
                title=f"Tagesverlauf -- {date_str}",
                xaxis_title="Uhrzeit", yaxis_title="Score / Boost",
                yaxis=dict(range=[0, 105]), height=420,
                template="plotly_dark",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin=dict(l=40, r=20, t=55, b=35),
            )
            st.plotly_chart(fig, use_container_width=True)

            # -- Einzelne Substanz-Level-Kurven --
            st.subheader("Substanz-Level (normalisiert 0-1)")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df["time"], y=df["elvanse_level"],
                mode="lines", name="Elvanse",
                line=dict(color="#2196F3", width=2),
            ))
            if "medikinet_level" in df.columns:
                fig2.add_trace(go.Scatter(
                    x=df["time"], y=df["medikinet_level"],
                    mode="lines", name="Medikinet",
                    line=dict(color="#AB47BC", width=2),
                ))
            fig2.add_trace(go.Scatter(
                x=df["time"], y=df["caffeine_level"],
                mode="lines", name="Koffein",
                line=dict(color="#FF9800", width=2),
            ))
            if "cns_load" in df.columns:
                fig2.add_trace(go.Scatter(
                    x=df["time"], y=df["cns_load"],
                    mode="lines", name="CNS-Last (Summe)",
                    line=dict(color="#F44336", width=2, dash="dash"),
                ))
                fig2.add_hline(y=1.5, line=dict(color="#FFC107", width=1, dash="dot"),
                    annotation_text="Warnschwelle")

            if is_today:
                _vmark(fig2, now, "#F44336", "solid", 1, "Jetzt", "top left")

            fig2.update_layout(
                xaxis_title="Uhrzeit", yaxis_title="Level (0-1)",
                yaxis=dict(range=[0, 2.5]), height=350,
                template="plotly_dark",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin=dict(l=40, r=20, t=30, b=35),
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Keine Daten")

    # PK-Erklaerung
    st.divider()
    st.subheader("So funktioniert das Modell")
    st.markdown("""
**Bateman-Funktion**: Jede Substanz hat eine Absorptionsrate (ka) und Eliminationsrate (ke).
Die Konzentrationskurve ergibt sich aus:

`C(t) = (ka / (ka - ke)) * (exp(-ke*t) - exp(-ka*t))`

Normalisiert auf Peak = 1.0. Bei Mehrfacheinnahmen werden die Kurven linear ueberlagert (Superposition).

Der **Bio-Score** kombiniert:
- Circadian-Rhythmus (Tageszeit-abhaengige Baseline, 0-60 Punkte)
- Elvanse-Boost (0-30 Punkte bei voller Wirkung)
- Medikinet-Boost (0-25 Punkte)
- Koffein-Boost (0-15 Punkte)
- Schlaf-Modifier (-20 bis +10 Punkte)

Die **CNS-Last** ist die Summe aller normalisierten Substanz-Level. Ueber 1.5 = erhoehte Belastung.
""")

    pk_data = {
        "Elvanse": {"ka": "0.78 h-1", "ke": "0.088 h-1", "Tmax": "3.8h", "t1/2": "~10h"},
        "Medikinet IR": {"ka": "1.72 h-1", "ke": "0.28 h-1", "Tmax": "1.5h", "t1/2": "2.5h"},
        "Med. retard": {"ka": "1.2 h-1 (nuechtern)", "ke": "0.28 h-1", "Tmax": "2h", "t1/2": "2.5h"},
        "Koffein": {"ka": "2.5 h-1", "ke": "0.16 h-1", "Tmax": "0.75h", "t1/2": "4.3h"},
    }
    st.dataframe(pd.DataFrame(pk_data).T, use_container_width=True)


# =========================================================
# PAGE: Vitals & Health
# =========================================================
if current_page == "vitals":
    st.header("Vitals & Health")

    # Latest snapshot
    latest_h = api_get("/api/health/latest")
    if isinstance(latest_h, dict) and latest_h.get("found"):
        v1, v2, v3, v4 = st.columns(4)
        hr = latest_h.get("heart_rate")
        rhr = latest_h.get("resting_hr")
        hrv = latest_h.get("hrv")
        sleep = latest_h.get("sleep_duration")
        spo2 = latest_h.get("spo2")
        steps = latest_h.get("steps")
        cals = latest_h.get("calories")

        if hr: v1.metric("HR", f"{hr:.0f} bpm")
        if rhr: v2.metric("Resting HR", f"{rhr:.0f} bpm")
        if hrv: v3.metric("HRV", f"{hrv:.0f} ms")
        if sleep: v4.metric("Schlaf", f"{sleep/60:.1f}h")

        v5, v6, v7, v8 = st.columns(4)
        if spo2: v5.metric("SpO2", f"{spo2:.0f}%")
        if steps: v6.metric("Schritte", f"{int(steps)}")
        if cals: v7.metric("Kalorien", f"{cals:.0f} kcal")

        ts_str = latest_h.get("timestamp", "")
        st.caption(f"Aktualisiert: {ts_str[11:16] if len(ts_str)>16 else ts_str} (alle 15 Min)")
    else:
        st.info("Noch keine Daten")

    # Day charts
    st.divider()
    date = st.date_input("Tag", value=datetime.now().date(), key="v_date")
    ds = date.isoformat()
    health = api_get("/api/health", {"start": f"{ds}T00:00:00", "end": f"{ds}T23:59:59"})
    if isinstance(health, list) and health:
        hdf = pd.DataFrame(health)
        hdf["time"] = pd.to_datetime(hdf["timestamp"])

        h1, h2 = st.columns(2)
        with h1:
            if "heart_rate" in hdf.columns and hdf["heart_rate"].notna().any():
                fig_hr = go.Figure()
                fig_hr.add_trace(go.Scatter(x=hdf["time"], y=hdf["heart_rate"],
                    mode="lines+markers", line=dict(color="#F44336")))
                fig_hr.update_layout(title="Herzfrequenz", yaxis_title="bpm",
                    height=280, template="plotly_dark", margin=dict(l=40,r=20,t=40,b=30))
                st.plotly_chart(fig_hr, use_container_width=True)
        with h2:
            if "hrv" in hdf.columns and hdf["hrv"].notna().any():
                fig_hrv = go.Figure()
                fig_hrv.add_trace(go.Scatter(x=hdf["time"], y=hdf["hrv"],
                    mode="lines+markers", line=dict(color="#3F51B5")))
                fig_hrv.update_layout(title="HRV", yaxis_title="ms",
                    height=280, template="plotly_dark", margin=dict(l=40,r=20,t=40,b=30))
                st.plotly_chart(fig_hrv, use_container_width=True)

        if "steps" in hdf.columns and hdf["steps"].notna().any():
            fig_steps = go.Figure()
            fig_steps.add_trace(go.Bar(x=hdf["time"], y=hdf["steps"],
                marker_color="#4CAF50"))
            fig_steps.update_layout(title="Schritte", yaxis_title="Steps",
                height=250, template="plotly_dark", margin=dict(l=40,r=20,t=40,b=30))
            st.plotly_chart(fig_steps, use_container_width=True)
    else:
        st.info("Keine Daten fuer diesen Tag")


# =========================================================
# PAGE: Persoenliches Modell
# =========================================================
if current_page == "modell":
    st.header("Persoenliches Modell")
    st.caption(
        "Analysiert deine Fokus-Ratings relativ zu Elvanse-Einnahmen. "
        "Je mehr Daten, desto praeziser die persoenliche Wirkungskurve."
    )

    model_data = api_get("/api/model/fit")

    if isinstance(model_data, dict):
        ms = model_data.get("status", "error")
        pc = model_data.get("pairs", 0)
        req = model_data.get("required", 15)

        st.progress(min(pc / max(req, 1), 1.0), text=f"Datenpunkte: {pc}/{req}")

        if ms == "insufficient_data":
            st.warning(model_data.get("message", "Nicht genug Daten."))
            collected = model_data.get("collected_pairs", [])
            if collected:
                cpdf = pd.DataFrame(collected)
                fig_m = go.Figure()
                fig_m.add_trace(go.Scatter(x=cpdf["offset_h"], y=cpdf["focus"],
                    mode="markers", marker=dict(size=10, color="#2196F3", opacity=0.7),
                    name="Fokus-Rating"))
                fig_m.add_trace(go.Scatter(x=cpdf["offset_h"],
                    y=cpdf["predicted_level"].apply(lambda x: x * 10),
                    mode="lines", line=dict(color="#FF9800", width=2, dash="dash"),
                    name="Theoretische Kurve"))
                fig_m.update_layout(xaxis_title="h nach Elvanse",
                    yaxis_title="Fokus / Level x10",
                    height=350, template="plotly_dark",
                    margin=dict(l=40,r=20,t=30,b=40))
                st.plotly_chart(fig_m, use_container_width=True)

        elif ms == "ok":
            st.success("Modell berechnet!")
            r1, r2, r3 = st.columns(3)
            r1.metric("Korrelation", f"{model_data.get('correlation', 0):.2f}")
            r2.metric("Peak", f"{model_data.get('personal_peak_offset_h', '?')}h")
            thr = model_data.get("personal_threshold")
            r3.metric("Schwelle", f"{thr:.2f}" if thr else "?")
            st.info(model_data.get("recommendation", ""))

            collected = model_data.get("collected_pairs", [])
            if collected:
                cpdf = pd.DataFrame(collected)
                fig_m = go.Figure()
                fig_m.add_trace(go.Scatter(x=cpdf["offset_h"], y=cpdf["focus"],
                    mode="markers", marker=dict(size=10, color="#2196F3", opacity=0.7),
                    name="Deine Ratings"))
                fig_m.add_trace(go.Scatter(x=cpdf["offset_h"],
                    y=cpdf["predicted_level"].apply(lambda x: x * 10),
                    mode="lines", line=dict(color="#FF9800", width=2),
                    name="Modell"))
                if thr:
                    fig_m.add_hline(y=7, line=dict(color="#4CAF50", width=1, dash="dash"),
                        annotation_text="Fokus >= 7")
                fig_m.update_layout(xaxis_title="h nach Elvanse",
                    yaxis_title="Fokus / Level x10",
                    height=400, template="plotly_dark",
                    margin=dict(l=40,r=20,t=30,b=40))
                st.plotly_chart(fig_m, use_container_width=True)


# =========================================================
# PAGE: Korrelation
# =========================================================
if current_page == "korrelation":
    st.header("Korrelationsanalyse")

    days_back = st.slider("Tage zurueck", 7, 90, 30, key="corr_d")
    now = datetime.now()
    start = (now - timedelta(days=days_back)).isoformat()
    end = now.isoformat()

    intakes = api_get("/api/intake", {"start": start, "end": end})
    logs = api_get("/api/log", {"start": start, "end": end})
    health = api_get("/api/health", {"start": start, "end": end})

    if not isinstance(intakes, list) or not isinstance(logs, list):
        st.warning("Nicht genuegend Daten")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Elvanse vs. Fokus")
            pairs = []
            ei_list = [i for i in intakes if i.get("substance") == "elvanse"]
            for lg in logs:
                lt = datetime.fromisoformat(lg["timestamp"])
                foc = lg.get("focus")
                if foc is None: continue
                best = None
                for ei in ei_list:
                    et = datetime.fromisoformat(ei["timestamp"])
                    off = (lt - et).total_seconds() / 3600
                    if 0 <= off <= 16:
                        if best is None or off < best: best = off
                if best is not None:
                    pairs.append({"offset_h": best, "focus": foc})

            if pairs:
                pdf = pd.DataFrame(pairs)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=pdf["offset_h"], y=pdf["focus"],
                    mode="markers", marker=dict(size=8, color="#2196F3", opacity=0.7)))
                fig.update_layout(xaxis_title="h nach Elvanse", yaxis_title="Fokus",
                    height=350, template="plotly_dark", margin=dict(l=40,r=20,t=30,b=40))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Noch keine Paare")

        with c2:
            st.subheader("Schlaf vs. Fokus")
            if isinstance(health, list) and health:
                sbd = {}
                for h in health:
                    d = h["timestamp"][:10]
                    sd = h.get("sleep_duration")
                    if sd: sbd[d] = sd
                sfp = []
                for lg in logs:
                    ld = lg["timestamp"][:10]
                    pd_day = (datetime.fromisoformat(ld) - timedelta(days=1)).strftime("%Y-%m-%d")
                    foc = lg.get("focus")
                    if foc and pd_day in sbd:
                        sfp.append({"sleep_h": sbd[pd_day]/60, "focus": foc})
                if sfp:
                    sdf = pd.DataFrame(sfp)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=sdf["sleep_h"], y=sdf["focus"],
                        mode="markers", marker=dict(size=8, color="#4CAF50", opacity=0.7)))
                    fig.update_layout(xaxis_title="Schlaf (h Vornacht)", yaxis_title="Fokus",
                        height=350, template="plotly_dark", margin=dict(l=40,r=20,t=30,b=40))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Noch keine Paare")
            else:
                st.info("Keine Health-Daten")

        st.divider()
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Intakes", len(intakes) if isinstance(intakes, list) else 0)
        mc2.metric("Logs", len(logs) if isinstance(logs, list) else 0)
        mc3.metric("Health", len(health) if isinstance(health, list) else 0)


# =========================================================
# PAGE: System
# =========================================================
if current_page == "system":
    st.header("System")

    status = api_get("/api/status")
    if isinstance(status, dict):
        sc1, sc2 = st.columns(2)
        sc1.metric("Service", status.get("service", "?"))
        sc2.metric("Status", status.get("status", "?"))
        st.caption(f"Server: {status.get('timestamp', '?')}")

        ui = status.get("user", {})
        if ui:
            uc1, uc2, uc3, uc4 = st.columns(4)
            uc1.metric("Gewicht", f"{ui.get('weight_kg', '?')} kg")
            uc2.metric("Groesse", f"{ui.get('height_cm', '?')} cm")
            uc3.metric("Alter", f"{ui.get('age', '?')}")
            uc4.metric("Fasten", "Ja" if ui.get("fasting") else "Nein")

    st.divider()
    st.subheader("Letzte Intakes")
    for sn, sl in [("elvanse", "Elvanse"), ("medikinet", "Medikinet IR"), ("medikinet_retard", "Med. retard")]:
        lat = api_get("/api/intake/latest", {"substance": sn})
        if isinstance(lat, dict) and lat.get("found"):
            ts = lat.get("timestamp", "?")
            dose = lat.get("dose_mg", "?")
            try:
                it = datetime.fromisoformat(ts)
                hrs = (datetime.now() - it).total_seconds() / 3600
                st.text(f"{sl}: {dose}mg -- vor {hrs:.1f}h ({ts[11:16]})")
            except Exception:
                st.text(f"{sl}: {dose}mg @ {ts}")
        else:
            st.text(f"{sl}: --")

    st.divider()
    st.subheader("Log-Schedule")
    rem = api_get("/api/log-reminder")
    if isinstance(rem, dict):
        sch = rem.get("schedule", [])
        for s in sch:
            icon = "[x]" if s["status"] == "done" else (">>>" if s["status"] == "due" else "[ ]")
            st.text(f"{icon} {s['target_time']} -- {s['label']}")

    st.divider()
    st.code(f"API: {API_BASE}\nKey: {'***' + API_KEY[-4:] if len(API_KEY) > 4 else '(nicht gesetzt)'}")
