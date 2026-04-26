import streamlit as st
from risk_dashboard.core.config import load_profiles, save_profile
from copy import deepcopy

def show_risk_profiles():
    st.header("Risikoprofile")
    st.markdown("Wähle ein Preset oder erstelle ein eigenes Profil. Alle Felder haben Tooltips zur Erklärung.")

    data = load_profiles()
    presets = list(data.get("profiles", {}).keys())
    presets_display = ["-- Neues Profil --"] + presets

    choice = st.selectbox("Preset laden", presets_display, index=0)
    if choice != "-- Neues Profil --":
        profile = deepcopy(data["profiles"][choice])
    else:
        profile = {
            "name": "",
            "description": "",
            "horizon_years": 3,
            "max_volatility_pct": 10,
            "max_drawdown_pct": 15,
            "allocation": {"equity": 50, "bonds": 40, "gold": 10},
            "rebalance": "monthly",
        }

    with st.form("profile_form"):
        name = st.text_input("Name", value=profile.get("name", ""), help="Bezeichnung des Profils, z. B. Low, Medium, High")
        desc = st.text_area("Kurzbeschreibung", value=profile.get("description", ""), help="Kurztext, was das Profil bezweckt")
        horizon = st.number_input("Zeithorizont in Jahren", min_value=1, max_value=50, value=int(profile.get("horizon_years", 3)), help="Empfohlener Anlagehorizont")
        vol = st.number_input("Maximale Volatilität in %", min_value=0.0, value=float(profile.get("max_volatility_pct", 10.0)), help="Annualisierte Standardabweichung in Prozent")
        dd = st.number_input("Maximaler Drawdown in %", min_value=0.0, value=float(profile.get("max_drawdown_pct", 15.0)), help="Maximaler Verlust vom Höchststand in Prozent")
        st.markdown("**Allokation in Prozent**")
        eq = st.number_input("Equity %", min_value=0, max_value=100, value=int(profile["allocation"].get("equity", 50)), help="Anteil Aktien in Prozent")
        bd = st.number_input("Bonds %", min_value=0, max_value=100, value=int(profile["allocation"].get("bonds", 40)), help="Anteil Anleihen in Prozent")
        gd = st.number_input("Gold %", min_value=0, max_value=100, value=int(profile["allocation"].get("gold", 10)), help="Anteil Gold in Prozent")
        rebalance = st.selectbox("Rebalancing", options=["monthly", "quarterly", "semiannual", "annual"], index=["monthly","quarterly","semiannual","annual"].index(profile.get("rebalance","monthly")), help="Intervall für Rebalancing")

        submitted = st.form_submit_button("Anwenden")
        save_as = st.text_input("Als Preset speichern unter Schlüssel", value="" , help="Gib einen Schlüssel ein, um das Profil als Preset zu speichern")

        # Validierung
        total_alloc = eq + bd + gd
        errors = []
        if total_alloc != 100:
            errors.append(f"Allokation muss 100% ergeben, aktuell: {total_alloc}%")
        if vol < 0 or dd < 0:
            errors.append("Volatilität und Drawdown müssen >= 0 sein")
        if horizon <= 0:
            errors.append("Zeithorizont muss größer als 0 sein")

        if errors:
            for e in errors:
                st.error(e)
        else:
            if submitted:
                st.success("Profil angewendet")
                st.write({
                    "name": name,
                    "description": desc,
                    "horizon_years": horizon,
                    "max_volatility_pct": vol,
                    "max_drawdown_pct": dd,
                    "allocation": {"equity": eq, "bonds": bd, "gold": gd},
                    "rebalance": rebalance,
                })

                if save_as:
                    key = save_as.strip()
                    profile_to_save = {
                        "name": name,
                        "description": desc,
                        "horizon_years": horizon,
                        "max_volatility_pct": vol,
                        "max_drawdown_pct": dd,
                        "allocation": {"equity": eq, "bonds": bd, "gold": gd},
                        "rebalance": rebalance,
                    }
                    save_profile(key, profile_to_save)
                    st.success(f"Preset '{key}' gespeichert")
