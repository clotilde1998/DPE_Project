import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np
from PIL import Image

# ── CONFIGURATION ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard DPE — Consommation Énergétique",
    page_icon="🏠",
    layout="wide"
)

API_URL = "https://dpe-project.onrender.com"  #  URL Render après déploiement

# ── THÈME ─────────────────────────────────────────────────────
with st.sidebar:
    try:
        logo = Image.open("logo.png")
        st.image(logo, use_container_width=True)
    except:
        st.markdown("### 🏠 DPE Predictor")

    st.markdown("---")
    theme = st.radio("🎨 Thème visuel", ["Clair", "Sombre"], index=0)

def apply_theme(theme):
    if theme == "Sombre":
        st.markdown("""
        <style>
            body, .stApp { background-color: #1e1e1e; color: #f1f1f1; }
            h1, h2, h3 { color: #f1f1f1 !important; }
            .stMetric { background-color: #2e2e2e; border-radius: 8px; padding: 10px; }
        </style>
        """, unsafe_allow_html=True)

apply_theme(theme)

BG    = "#1e1e1e" if theme == "Sombre" else "white"
FC    = "white"   if theme == "Sombre" else "black"
GRID  = "#444"    if theme == "Sombre" else "#ddd"

# ── TITRE ─────────────────────────────────────────────────────
st.title("🏠 Dashboard DPE — Prédiction de la Consommation Énergétique")
st.markdown("Ce dashboard prédit la consommation énergétique d'un logement (kWh/m²/an) "
            "et explique les facteurs qui influencent cette prédiction.")
st.markdown("---")

# ── CHARGEMENT DONNÉES TEST ───────────────────────────────────
@st.cache_data
def load_test_data():
    try:
        df = pd.read_csv("X_test_prepared.csv")
        df.pop("y_test_log") if "y_test_log" in df.columns else None
        return df
    except:
        return pd.DataFrame()

df_test = load_test_data()

# ── SIDEBAR — SAISIE LOGEMENT ─────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.header("🏡 Sélection du logement")

mode = st.sidebar.radio("Mode", ["Choisir un logement existant", "Saisir manuellement"])

input_data = {}

if mode == "Choisir un logement existant":
    if not df_test.empty:
        index = st.sidebar.number_input(
            "Index du logement (jeu de test)",
            min_value=0,
            max_value=len(df_test) - 1,
            step=1,
            help=f"Choisir entre 0 et {len(df_test)-1}"
        )
        input_data = df_test.iloc[int(index)].to_dict()
        st.sidebar.success(f"✅ Logement {int(index)} sélectionné")
    else:
        st.sidebar.error("Impossible de charger X_test_prepared.csv")

else:
    st.sidebar.markdown("#### Caractéristiques du logement")
    if not df_test.empty:
        for col in df_test.columns[:8]:   # afficher les 8 premières features
            val = float(df_test[col].median())
            input_data[col] = st.sidebar.number_input(col, value=val, format="%.4f")
    else:
        st.sidebar.warning("Données de référence non disponibles.")

# ── SECTION 1 : PRÉDICTION ────────────────────────────────────
st.header("🔮 Prédiction de la Consommation Énergétique")

col1, col2, col3 = st.columns([1, 1, 1])

CLASSE_DPE_COLORS = {
    "A": "#00c853", "B": "#64dd17", "C": "#aeea00",
    "D": "#ffd600", "E": "#ff6d00", "F": "#dd2c00", "G": "#b71c1c"
}

if st.button("⚡ Lancer la prédiction", type="primary"):
    try:
        response = requests.post(
            f"{API_URL}/prediction",
            json={"data": input_data},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        conso  = result["consommation_kwh_m2_an"]
        classe = result["classe_dpe_estimee"]
        color  = CLASSE_DPE_COLORS.get(classe, "gray")

        with col1:
            st.metric(
                label="Consommation prédite",
                value=f"{conso} kWh/m²/an"
            )
        with col2:
            st.markdown(
                f"""
                <div style='text-align:center; padding:20px; border-radius:12px;
                            background-color:{color}; color:white;'>
                    <h2 style='margin:0'>Classe DPE</h2>
                    <h1 style='font-size:60px; margin:0'>{classe}</h1>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col3:
            # Jauge DPE
            classes = ["A", "B", "C", "D", "E", "F", "G"]
            seuils = [50, 90, 150, 230, 330, 450, 1000]  # kWh/m²/an
            colors_dpe= [CLASSE_DPE_COLORS[c] for c in classes]

            fig, ax = plt.subplots(figsize=(4, 3))
            fig.patch.set_facecolor(BG)
            ax.set_facecolor(BG)
            for i, (cl, col_dpe) in enumerate(zip(classes, colors_dpe)):
                alpha = 1.0 if cl == classe else 0.3
                ax.barh(cl, seuils[i], color=col_dpe, alpha=alpha, edgecolor="white")
            ax.axvline(conso, color="black", linestyle="--", linewidth=2, label=f"{conso} kWh/m²")
            ax.set_xlabel("kWh/m²/an", color=FC)
            ax.set_title("Position dans l'échelle DPE", color=FC)
            ax.tick_params(colors=FC)
            ax.legend(fontsize=8, labelcolor=FC, facecolor=BG)
            st.pyplot(fig)

        # Interprétation textuelle
        st.markdown("---")
        interpretations = {
            "A": "🟢 Logement **très économe** en énergie. Performance excellente.",
            "B": "🟢 Logement **économe**. Bonne performance énergétique.",
            "C": "🟡 Performance **assez bonne**. Quelques améliorations possibles.",
            "D": "🟡 Performance **moyenne**. Des travaux pourraient réduire la consommation.",
            "E": "🟠 Performance **médiocre**. Travaux recommandés.",
            "F": "🔴 Logement **énergivore**. Rénovation fortement conseillée.",
            "G": "🔴 Logement **très énergivore**. Passoire thermique.",
        }
        st.info(interpretations.get(classe, ""))

    except Exception as e:
        st.error(f"Erreur API : {e}")

st.markdown("---")

# ── SECTION 2 : SHAP LOCAL ────────────────────────────────────
st.header("📌 Explication de la prédiction (SHAP)")
st.markdown("Les valeurs SHAP indiquent la **contribution de chaque variable** "
            "à la prédiction pour ce logement.")

if mode == "Choisir un logement existant" and not df_test.empty:
    index_shap = int(index) if "index" in dir() else 0

    if st.button("🔍 Obtenir l'explication SHAP"):
        try:
            response = requests.get(
                f"{API_URL}/interpretabilite/{index_shap}",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            shap_records = data["top10_shap_values"]
            shap_df = pd.DataFrame(shap_records)

            col_s1, col_s2 = st.columns([2, 1])

            with col_s1:
                fig, ax = plt.subplots(figsize=(9, 5))
                fig.patch.set_facecolor(BG)
                ax.set_facecolor(BG)
                colors_shap = ["#e74c3c" if v > 0 else "#3498db"
                               for v in shap_df["shap_value"]]
                ax.barh(shap_df["feature"], shap_df["shap_value"],
                        color=colors_shap, edgecolor="white")
                ax.axvline(0, color=FC, linewidth=0.8, linestyle="--")
                ax.set_xlabel("Valeur SHAP (impact sur la prédiction)", color=FC)
                ax.set_title("Top 10 variables — Impact sur la consommation", color=FC)
                ax.tick_params(colors=FC)
                red_patch  = mpatches.Patch(color="#e74c3c", label="↑ Augmente la conso")
                blue_patch = mpatches.Patch(color="#3498db", label="↓ Réduit la conso")
                ax.legend(handles=[red_patch, blue_patch],
                          facecolor=BG, labelcolor=FC)
                st.pyplot(fig)

            with col_s2:
                st.markdown("#### Valeurs des variables")
                st.dataframe(
                    shap_df[["feature", "feature_value", "shap_value"]]
                    .rename(columns={
                        "feature":       "Variable",
                        "feature_value": "Valeur",
                        "shap_value":    "Impact SHAP"
                    }).style.format({"Valeur": "{:.3f}", "Impact SHAP": "{:.4f}"}),
                    use_container_width=True
                )
                st.caption(f"Valeur de base SHAP : {data['valeur_base_shap']}")

        except Exception as e:
            st.error(f"Erreur SHAP : {e}")
else:
    st.info("ℹ️ Le mode 'Choisir un logement existant' est requis pour les explications SHAP.")

st.markdown("---")

# ── SECTION 3 : FEATURE IMPORTANCE GLOBALE ───────────────────
st.header("🌐 Importance globale des variables")
st.markdown("Variables les plus déterminantes dans le modèle XGBoost, "
            "tous logements confondus.")

top_n = st.slider("Nombre de variables à afficher", min_value=5, max_value=30, value=15)

if st.button("📊 Afficher l'importance globale"):
    try:
        response = requests.get(
            f"{API_URL}/feature_importance?top_n={top_n}",
            timeout=30
        )
        response.raise_for_status()
        fi_data = response.json()

        fi_df = pd.DataFrame(fi_data["feature_importance"])

        fig, ax = plt.subplots(figsize=(10, max(5, top_n * 0.4)))
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        sns.barplot(
            data=fi_df,
            y="feature",
            x="importance",
            palette="viridis",
            ax=ax
        )
        ax.set_xlabel("Importance", color=FC)
        ax.set_ylabel("Variable", color=FC)
        ax.set_title(f"Top {top_n} variables — Modèle XGBoost", color=FC)
        ax.tick_params(colors=FC)
        ax.grid(axis="x", linestyle="--", alpha=0.4, color=GRID)
        st.pyplot(fig)

        with st.expander("📋 Voir le tableau complet"):
            st.dataframe(
                fi_df.style.format({"importance": "{:.6f}"}),
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Erreur feature importance : {e}")

st.markdown("---")

# ── FOOTER ────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center; color:gray; font-size:12px;'>"
    "Dashboard DPE — Modèle XGBoost | "
    "Données : Dpe_post_2021 | "
    "API : FastAPI + SHAP"
    "</div>",
    unsafe_allow_html=True
)
