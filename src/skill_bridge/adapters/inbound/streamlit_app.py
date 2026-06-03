"""SkillBridge — vitrine Streamlit consommant l'API FastAPI.

Trois écrans :
1. **Vue d'ensemble** : pitch, fil rouge, encart interopérabilité (CSV brut → xAPI via LRC,
   mapping ESCO) — rend visibles les Lots 1 et 3.
2. **Apprenant** : profil de maîtrise observé, cluster assigné, top-5 recos expliquées.
3. **Clustering** : sélection de k par silhouette, clusters découverts, projection PCA 2D,
   et **validation cluster ↔ archétype** sur la vérité-terrain de simulation.

L'app consomme l'API FastAPI pour TOUTES les données publiques (profils, clusters, recos).
Seul ``learners.jsonl`` est lu localement, et UNIQUEMENT pour le bloc de validation
"vérité-terrain de simulation" sur la vue clustering — étiqueté comme tel.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.decomposition import PCA

API_URL: str = os.environ.get("SKILLBRIDGE_API_URL", "http://localhost:8000")
# streamlit_app.py est à src/skill_bridge/adapters/inbound/streamlit_app.py
# → parents[4] = racine du repo (un niveau de moins que api/app.py qui descend dans api/).
REPO_ROOT = Path(__file__).resolve().parents[4]

# Fixtures committées dans data/seed/ — utilisées en PROD (où le LRC n'est pas en ligne
# et où data/generated/ n'est pas regénéré). Le local dev privilégie data/generated/.
GENERATED_LEARNERS = REPO_ROOT / "data" / "generated" / "learners.jsonl"
FIXTURE_LEARNERS = REPO_ROOT / "data" / "seed" / "learners_fixture.jsonl"
GENERATED_CSV = REPO_ROOT / "data" / "generated" / "sample_mathia.csv"
FIXTURE_CSV = REPO_ROOT / "data" / "seed" / "interop_example" / "mathia_row.csv"
GENERATED_LRC_JSONL = REPO_ROOT / "data" / "generated" / "traces_via_lrc.jsonl"
FIXTURE_LRC_JSON = REPO_ROOT / "data" / "seed" / "interop_example" / "lrc_statement.json"

st.set_page_config(
    page_title="SkillBridge — Data & AI provider",
    page_icon="🎓",
    layout="wide",
)


# --- Présentation : libellés et couleurs centralisés ---

# Mapping snake_case (côté domain/data) → libellé humain (côté UI).
# La présentation est la responsabilité du front : ne pas demander à l'API de servir
# les libellés humains, et ne PAS parser ``cluster_label`` côté API (qui contient les
# snake_case). Les labels de clusters sont **regénérés** côté front à partir des
# centroïdes (cf. ``_cluster_label_from_centroid``).
DOMAIN_LABELS: dict[str, str] = {
    "calcul_de_base": "Calcul de base",
    "calcul_avance": "Calcul avancé",
    "fractions_decimaux": "Fractions & décimaux",
    "geometrie_mesures": "Géométrie & mesures",
    "unites_temps": "Unités & temps",
    "resolution_problemes": "Résolution de problèmes",
}

# Palette qualitative cohérente : C0 = même teinte sur scatter, heatmap (axe Y), cards.
# Source : Set2 de ColorBrewer (pastel, sobre, lisible en RGB et imprimé).
CLUSTER_COLORS: tuple[str, ...] = (
    "#66c2a5",  # C0 — vert d'eau
    "#fc8d62",  # C1 — orange
    "#8da0cb",  # C2 — lavande
    "#e78ac3",  # C3 — rose
    "#a6d854",  # C4 — vert lime
    "#ffd92f",  # C5 — jaune
    "#e5c494",  # C6 — beige
    "#b3b3b3",  # C7 — gris
)

# Seuils de "fort" / "faible" pour la regénération des libellés de cluster côté front.
# Alignés sur src/skill_bridge/application/clustering.py.
STRONG_THRESHOLD: float = 0.70
WEAK_THRESHOLD: float = 0.55


def _domain_label(snake: str) -> str:
    """Libellé humain d'un domaine (fallback : snake_case en clair)."""
    return DOMAIN_LABELS.get(snake, snake.replace("_", " ").capitalize())


def _cluster_color(cluster_id: int) -> str:
    return CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]


def _cluster_label_from_centroid(centroid: dict[str, float]) -> str:
    """Regénère un libellé lisible à partir du centroïde (côté front, pas via l'API).

    Même logique que ``ClusteringService._label_from_centroid``, mais avec les libellés
    humains du mapping ``DOMAIN_LABELS`` — pour éviter d'afficher du snake_case à
    l'écran.
    """
    strong = sorted(
        (d for d, s in centroid.items() if s >= STRONG_THRESHOLD),
        key=lambda d: -centroid[d],
    )
    weak = sorted(
        (d for d, s in centroid.items() if s <= WEAK_THRESHOLD),
        key=lambda d: centroid[d],
    )
    if not strong and not weak:
        return "Profil équilibré moyen"
    if not weak and len(strong) >= 4:
        return "Profil équilibré, fort partout"
    if not strong and len(weak) >= 4:
        return "En difficulté générale"
    parts: list[str] = []
    if strong:
        parts.append("fort en " + ", ".join(_domain_label(d) for d in strong[:2]))
    if weak:
        parts.append("faible en " + ", ".join(_domain_label(d) for d in weak[:2]))
    return " · ".join(parts).capitalize()


# --- Clients & caches ---


@st.cache_resource
def api() -> httpx.Client:
    return httpx.Client(base_url=API_URL, timeout=15.0)


def _get(path: str) -> Any:
    response = api().get(path)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300)
def fetch_health() -> dict[str, Any]:
    return _get("/health")


@st.cache_data(ttl=300)
def fetch_learners() -> list[dict[str, Any]]:
    return _get("/learners")


@st.cache_data(ttl=300)
def fetch_clusters() -> dict[str, Any]:
    return _get("/clusters")


@st.cache_data(ttl=300)
def fetch_profile(learner_id: str) -> dict[str, Any]:
    return _get(f"/profile/{learner_id}")


@st.cache_data(ttl=300)
def fetch_assignment(learner_id: str) -> dict[str, Any]:
    return _get(f"/clusters/assignment/{learner_id}")


@st.cache_data(ttl=300)
def fetch_recommendations(learner_id: str, n: int) -> list[dict[str, Any]]:
    return _get(f"/recommend/{learner_id}?n={n}")


@st.cache_data(ttl=300)
def load_ground_truth_local() -> dict[str, dict[str, Any]]:
    """Charge ``learners.jsonl`` LOCALEMENT (pas via l'API).

    Vérité-terrain de simulation. Priorité :
    1. ``data/generated/learners.jsonl`` (régénéré en local dev avec la seed courante)
    2. ``data/seed/learners_fixture.jsonl`` (fixture committée pour la prod, seed=42)

    Indisponible en production réelle — affichage explicite côté UI.
    """
    path = GENERATED_LEARNERS if GENERATED_LEARNERS.exists() else FIXTURE_LEARNERS
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            payload = json.loads(line)
            out[payload["learner_id"]] = payload
    return out


@st.cache_data(ttl=300)
def load_interop_sample() -> tuple[str | None, dict[str, Any] | None]:
    """Charge un avant/après réel d'une conversion LRC.

    Priorité : ``data/generated/`` (frais d'un run local) puis fallback sur la fixture
    ``data/seed/interop_example/`` (capture committée d'une vraie conversion LRC).
    """
    csv_line: str | None = None
    if GENERATED_CSV.exists():
        with GENERATED_CSV.open(encoding="utf-8") as f:
            header = f.readline()
            first = f.readline()
            csv_line = header + first if first else None
    elif FIXTURE_CSV.exists():
        csv_line = FIXTURE_CSV.read_text(encoding="utf-8")

    xapi_stmt: dict[str, Any] | None = None
    if GENERATED_LRC_JSONL.exists():
        with GENERATED_LRC_JSONL.open(encoding="utf-8") as f:
            first = f.readline()
            if first.strip():
                xapi_stmt = json.loads(first)
    elif FIXTURE_LRC_JSON.exists():
        xapi_stmt = json.loads(FIXTURE_LRC_JSON.read_text(encoding="utf-8"))
    return csv_line, xapi_stmt


# --- Helpers ---


def _score_color(score: float) -> str:
    if score >= 0.70:
        return "#2ecc71"
    if score < 0.55:
        return "#e74c3c"
    return "#f39c12"


def _format_pct(x: float) -> str:
    return f"{x * 100:.0f}%"


# --- Screens ---


def render_home() -> None:
    st.title("SkillBridge")
    st.markdown(
        "###### **Data & AI provider** pour le dataspace éducation & compétences "
        "(écosystème Prometheus-X / DASES)"
    )
    st.markdown(
        "> À partir de traces d'apprentissage normalisées en xAPI, **SkillBridge** "
        "construit un profil de maîtrise par apprenant, segmente la population en "
        "profils pédagogiques (clustering non supervisé), et émet des recommandations "
        "explicables, exposées via une API HTTP."
    )

    st.markdown("### Fil rouge")
    st.markdown(
        """
| Étape | Brique | Sortie |
| --- | --- | --- |
| 1. Émission | Application éducative (persona « Léa », maths primaire) | événements bruts |
| 2. Normalisation | **LRC** (Prometheus-X) | statements xAPI (profils DASES) |
| 3. Coffre apprenant | PLRS *(simulé au niveau 1)* | trace consentie |
| 4. Échange souverain | **PDC** *(Lot 4, à venir)* | trace transmise au provider |
| 5. **Provider** | **SkillBridge** (cette démo) | profil + cluster + recommandations |
"""
    )

    st.markdown("### Interopérabilité — d'un format brut au statement xAPI")
    csv_line, xapi_stmt = load_interop_sample()
    if csv_line is None or xapi_stmt is None:
        st.info(
            "Lance `make dataset` puis `--via-lrc=http://localhost:8080` pour peupler "
            "cet encart avec un échantillon réellement converti."
        )
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Avant** — CSV propriétaire *Mathia* (1 ligne)")
            st.code(csv_line.strip(), language="text")
        with col_b:
            st.markdown("**Après** — statement xAPI produit par le **LRC**")
            st.code(json.dumps(xapi_stmt, indent=2, ensure_ascii=False), language="json")
        st.caption(
            "Conversion réelle via `POST /convert_custom` du `learning-records-converter` "
            "(Prometheus-X), avec un mapping YAML maison versionné dans "
            "`data/seed/lrc_mapping_mathia.yml`. Le LRC supporte aussi nativement Matomo, "
            "SCORM 2004 et IMS Caliper."
        )

    st.markdown("### Mapping sémantique vers ESCO")
    st.markdown(
        "Chaque compétence du **référentiel maison numératie** (calé sur les programmes "
        "français cycles 2/3) est **mappée vers le référentiel pivot européen ESCO**, "
        "rendant le profil portable au-delà du périmètre Mathia."
    )
    st.markdown(
        """
| Compétence (maison) | Domaine | URI ESCO (illustrative) |
| --- | --- | --- |
| Calcul mental | calcul avancé | `…/esco/skill/2ec70df4-…` |
| Résolution de problèmes | résolution | `…/esco/skill/0c0fe33d-…` |
| Périmètres / Aires | géométrie | `…/esco/skill/a8c1c2d3-…` |
"""
    )

    st.markdown("---")
    st.markdown(
        f"🔗 **API live** : [`/docs`]({API_URL}/docs) — Swagger interactif · "
        "Code source : [github.com/sodigitaljeremy/skill-bridge]"
        "(https://github.com/sodigitaljeremy/skill-bridge)"
    )


def render_learner() -> None:
    st.title("Exploration d'un apprenant")
    st.markdown(
        "###### Profil de maîtrise observé, cluster assigné par le système, et "
        "**top 5 recommandations expliquées**."
    )

    learners = fetch_learners()
    names_sorted = sorted(learners, key=lambda x: x["display_name"])
    lea_idx = next(
        (i for i, ln in enumerate(names_sorted) if ln["display_name"] == "Léa Martin"),
        0,
    )
    selected = st.selectbox(
        "Apprenant",
        names_sorted,
        index=lea_idx,
        format_func=lambda ln: f"{ln['display_name']} (grade {ln['grade_level']})",
    )

    profile = fetch_profile(selected["learner_id"])
    assignment = fetch_assignment(selected["learner_id"])
    clusters = fetch_clusters()
    recos = fetch_recommendations(selected["learner_id"], n=5)

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("Profil de maîtrise par domaine")
        st.caption(
            "Score moyen observé (vert ≥ 0.70 fort · orange [0.55, 0.70] · rouge < 0.55 faible)"
        )
        scores = profile["mean_score_per_domain"]
        domains = sorted(scores.keys())
        values = [scores[d] for d in domains]
        labels = [_domain_label(d) for d in domains]
        colors = [_score_color(v) for v in values]
        fig = go.Figure(
            go.Bar(
                x=values,
                y=labels,
                orientation="h",
                marker_color=colors,
                text=[f"{v:.2f}" for v in values],
                textposition="outside",
                hovertemplate="%{y} : %{x:.2f}<extra></extra>",
            )
        )
        fig.update_layout(
            xaxis_range=[0, 1.05],
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
        )
        st.plotly_chart(fig, width="stretch")

    with col_right:
        st.subheader("Cluster assigné")
        cluster_id = assignment["cluster_id"]
        cluster = next(c for c in clusters["clusters"] if c["cluster_id"] == cluster_id)
        readable = _cluster_label_from_centroid(cluster["centroid_per_domain"])
        color = _cluster_color(cluster_id)
        # Carte HTML markdown (et non st.metric) pour éviter la troncature CSS
        # du libellé complet, et pour porter la couleur de cluster cohérente avec
        # le scatter et la heatmap.
        st.markdown(
            f"""
<div style="border-left: 6px solid {color}; background: #f8f9fa;
            padding: 10px 14px; border-radius: 4px;">
  <div style="font-size: 0.85em; color: #666;">Cluster C{cluster_id}</div>
  <div style="font-weight: 500; font-size: 1.0em; margin-top: 2px;">{readable}</div>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        st.caption(f"**Niveau scolaire** : grade {profile['grade_level']}")
        st.caption(f"**Traces observées** : {profile['n_traces']}")
        st.caption(f"**Distance au centroïde** : {assignment['distance_to_centroid']:.2f}")

    st.markdown("---")
    st.subheader("Top 5 recommandations")
    st.caption(
        "Score = combinaison transparente : 0.50 · skill_overlap + 0.20 · grade_fit + "
        "0.20 · similarité sémantique + 0.10 · signal cluster (réussite des pairs)."
    )

    for i, r in enumerate(recos, start=1):
        with st.container(border=True):
            top_l, top_r = st.columns([3, 1])
            with top_l:
                st.markdown(f"**{i}. {r['title']}** · `{r['resource_id']}`")
                st.caption(r["explanation"])
            with top_r:
                st.metric(label="Score", value=f"{r['score']:.2f}")


def render_clustering() -> None:
    clusters = fetch_clusters()
    learners = fetch_learners()
    ground_truth = load_ground_truth_local()

    # Calcule la pureté archétype↔cluster (si vérité-terrain dispo) AVANT le titre.
    purity_min, purity_max = _compute_purity_range(learners, ground_truth)

    st.title("Clustering pédagogique")
    if purity_min is not None and purity_max is not None:
        purity_str = (
            f"**{_format_pct(purity_min)}-{_format_pct(purity_max)}**"
            if purity_min < purity_max
            else f"**{_format_pct(purity_min)}**"
        )
        st.markdown(
            f"###### Le système a découvert **{clusters['k']} profils pédagogiques** "
            "sans connaître les vrais — et il les retrouve à "
            f"{purity_str} de précision sur la vérité-terrain de simulation."
        )
    else:
        st.markdown(
            f"###### Le système a découvert **{clusters['k']} profils pédagogiques** "
            "par clustering non supervisé sur les profils de maîtrise observés."
        )

    st.markdown("### Sélection de **k** par silhouette")
    st.caption(
        "Aucune valeur de k n'est imposée : le score de silhouette est calculé pour "
        "k=2..8 sur les 12 features (mean_score + success_rate par domaine), et le "
        "système retient le **maximum empirique**."
    )
    _render_silhouette_chart(clusters)

    st.markdown("### Clusters découverts")
    cluster_list = clusters["clusters"]
    cols = st.columns(len(cluster_list))
    for cluster, col in zip(cluster_list, cols, strict=False):
        readable = _cluster_label_from_centroid(cluster["centroid_per_domain"])
        color = _cluster_color(cluster["cluster_id"])
        with col:
            st.markdown(
                f"""
<div style="border-left: 6px solid {color}; background: #f8f9fa;
            padding: 10px 14px; border-radius: 4px; height: 120px;">
  <div style="font-size: 0.85em; color: #666;">
    Cluster C{cluster["cluster_id"]} · {cluster["size"]} apprenants
  </div>
  <div style="font-weight: 500; font-size: 0.95em; margin-top: 4px;">{readable}</div>
</div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### Centroïdes par domaine")
    st.caption(
        "Chaque ligne est un profil pédagogique découvert. On y voit ses forces "
        "(vert) et ses faiblesses (rouge) propres."
    )
    _render_centroid_heatmap(clusters)

    st.markdown("### Projection 2D des apprenants (PCA, *illustrative*)")
    _render_pca_scatter(learners, clusters)

    if ground_truth:
        st.markdown("---")
        st.markdown("### Validation : correspondance cluster ↔ archétype")
        st.warning(
            "**Vérité-terrain de simulation** — issue de `data/generated/learners.jsonl`. "
            "Indisponible en production réelle. Affichée ici **uniquement** pour valider "
            "que le clustering non supervisé retrouve les archétypes avec lesquels le "
            "dataset a été généré."
        )
        _render_purity_table(learners, ground_truth, clusters)


# --- Clustering screen helpers ---


def _compute_purity_range(
    learners: list[dict[str, Any]],
    ground_truth: dict[str, dict[str, Any]],
) -> tuple[float | None, float | None]:
    if not ground_truth:
        return None, None
    archetype_to_cluster: dict[str, Counter] = defaultdict(Counter)
    for learner in learners:
        gt = ground_truth.get(learner["learner_id"])
        if gt is None:
            continue
        archetype = gt.get("archetype")
        if not archetype:
            continue
        assignment = fetch_assignment(learner["learner_id"])
        archetype_to_cluster[archetype][assignment["cluster_id"]] += 1
    purities = []
    for counts in archetype_to_cluster.values():
        if not counts:
            continue
        purities.append(max(counts.values()) / sum(counts.values()))
    if not purities:
        return None, None
    return min(purities), max(purities)


def _render_silhouette_chart(clusters: dict[str, Any]) -> None:
    sil = clusters["silhouette_by_k"]
    chosen_k = int(clusters["k"])
    ks = sorted(int(k) for k in sil)
    scores = [sil[str(k)] for k in ks]
    colors = ["#2980b9" if k == chosen_k else "#bdc3c7" for k in ks]
    fig = go.Figure(
        go.Bar(
            x=[f"k={k}" for k in ks],
            y=scores,
            marker_color=colors,
            text=[f"{s:.3f}" for s in scores],
            textposition="outside",
            hovertemplate="%{x}: %{y:.3f}<extra></extra>",
        )
    )
    fig.update_layout(
        yaxis_title="Silhouette score",
        height=260,
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=False,
    )
    fig.add_annotation(
        x=f"k={chosen_k}",
        y=clusters["silhouette"],
        text="★ retenu",
        showarrow=True,
        arrowhead=2,
        yshift=20,
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(f"k retenu : **k = {chosen_k}** (silhouette = {clusters['silhouette']:.3f})")


def _render_centroid_heatmap(clusters: dict[str, Any]) -> None:
    """Heatmap 4 clusters x 6 domaines, couleur = score du centroïde (rouge -> vert)."""
    cluster_list = clusters["clusters"]
    # Ordre des domaines stable (alphabétique des snake_case) et identique partout.
    domains_snake = sorted(cluster_list[0]["centroid_per_domain"].keys())
    domain_labels = [_domain_label(d) for d in domains_snake]
    z_matrix = [[c["centroid_per_domain"][d] for d in domains_snake] for c in cluster_list]
    y_labels = [
        f"C{c['cluster_id']} — {_cluster_label_from_centroid(c['centroid_per_domain'])}"
        for c in cluster_list
    ]

    fig = go.Figure(
        go.Heatmap(
            z=z_matrix,
            x=domain_labels,
            y=y_labels,
            colorscale="RdYlGn",
            zmin=0.30,
            zmax=0.90,
            text=[[f"{v:.2f}" for v in row] for row in z_matrix],
            texttemplate="%{text}",
            textfont=dict(size=12, color="#222"),
            hovertemplate="%{y}<br>%{x} : %{z:.2f}<extra></extra>",
            colorbar=dict(title="Score", thickness=12, len=0.85),
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(side="top", tickangle=-15),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, width="stretch")


def _render_pca_scatter(learners: list[dict[str, Any]], clusters: dict[str, Any]) -> None:
    rows: list[tuple[str, str, list[float], int]] = []
    for learner in learners:
        profile = fetch_profile(learner["learner_id"])
        assignment = fetch_assignment(learner["learner_id"])
        domains = sorted(profile["mean_score_per_domain"].keys())
        features = [profile["mean_score_per_domain"][d] for d in domains]
        features += [profile["success_rate_per_domain"][d] for d in domains]
        rows.append(
            (learner["learner_id"], learner["display_name"], features, assignment["cluster_id"])
        )

    features_arr = np.array([row[2] for row in rows])
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(features_arr)

    pc1_var = float(pca.explained_variance_ratio_[0])
    pc2_var = float(pca.explained_variance_ratio_[1])
    total_var = pc1_var + pc2_var
    st.caption(
        f"La projection 2D n'explique que **{total_var:.0%}** de la variance des profils "
        f"(PC1 {pc1_var:.0%} · PC2 {pc2_var:.0%}). La séparation réelle se joue sur les "
        "**12 dimensions** — la heatmap des centroïdes (ci-dessus) et la table de "
        "pureté (ci-dessous) sont plus informatives. Léa est annotée."
    )

    # Libellés lisibles regénérés depuis le centroïde — pas depuis ``label`` de l'API.
    cluster_readable_by_id = {
        c["cluster_id"]: _cluster_label_from_centroid(c["centroid_per_domain"])
        for c in clusters["clusters"]
    }
    cluster_strings = [f"C{row[3]} — {cluster_readable_by_id[row[3]]}" for row in rows]
    # category_orders + color_discrete_map garantissent l'ordre stable C0..Cn et
    # la même couleur que les cards et la heatmap.
    sorted_cluster_ids = sorted(cluster_readable_by_id)
    category_order = [f"C{cid} — {cluster_readable_by_id[cid]}" for cid in sorted_cluster_ids]
    color_map = {
        f"C{cid} — {cluster_readable_by_id[cid]}": _cluster_color(cid) for cid in sorted_cluster_ids
    }

    df: dict[str, list[Any]] = {
        "x": coords[:, 0].tolist(),
        "y": coords[:, 1].tolist(),
        "Cluster": cluster_strings,
        "Apprenant": [row[1] for row in rows],
    }
    fig = px.scatter(
        df,
        x="x",
        y="y",
        color="Cluster",
        hover_name="Apprenant",
        color_discrete_map=color_map,
        category_orders={"Cluster": category_order},
    )
    fig.update_traces(marker=dict(size=10, line=dict(width=1, color="white")))

    lea_idx = next((i for i, row in enumerate(rows) if row[1] == "Léa Martin"), None)
    if lea_idx is not None:
        fig.add_annotation(
            x=coords[lea_idx, 0],
            y=coords[lea_idx, 1],
            text="<b>Léa</b>",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.5,
            font=dict(size=14),
            bgcolor="rgba(255,255,255,0.85)",
        )

    fig.update_layout(
        height=500,
        xaxis_title=f"PC1 ({pc1_var:.0%} variance expliquée)",
        yaxis_title=f"PC2 ({pc2_var:.0%} variance expliquée)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, width="stretch")


def _render_purity_table(
    learners: list[dict[str, Any]],
    ground_truth: dict[str, dict[str, Any]],
    clusters: dict[str, Any],
) -> None:
    archetype_to_cluster: dict[str, Counter] = defaultdict(Counter)
    for learner in learners:
        gt = ground_truth.get(learner["learner_id"])
        if gt is None or not gt.get("archetype"):
            continue
        assignment = fetch_assignment(learner["learner_id"])
        archetype_to_cluster[gt["archetype"]][assignment["cluster_id"]] += 1

    cluster_readable_by_id = {
        c["cluster_id"]: _cluster_label_from_centroid(c["centroid_per_domain"])
        for c in clusters["clusters"]
    }

    rows = []
    for archetype, counts in sorted(archetype_to_cluster.items()):
        dominant_cluster, dominant_count = counts.most_common(1)[0]
        total = sum(counts.values())
        purity = dominant_count / total
        cluster_text = f"C{dominant_cluster} — {cluster_readable_by_id[dominant_cluster]}"
        rows.append(
            {
                "Archétype (vérité-terrain)": archetype,
                "Cluster dominant": cluster_text,
                "Pureté": _format_pct(purity),
                "Détail": ", ".join(f"C{cid}={n}" for cid, n in counts.most_common()),
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)


# --- Main ---


def main() -> None:
    st.sidebar.title("SkillBridge")
    st.sidebar.caption("Data & AI provider — vitrine")

    try:
        health = fetch_health()
    except httpx.HTTPError as e:
        st.sidebar.error(
            f"⚠️ API indisponible sur `{API_URL}`\n\n"
            f"`make api` dans un autre terminal, puis rafraîchis."
        )
        st.error(f"Impossible de joindre l'API : {e}")
        return

    if health.get("preloaded"):
        st.sidebar.success(
            f"API OK · {health['n_learners']} apprenants · k = {health['n_clusters']}"
        )
    else:
        st.sidebar.warning("API démarrée mais pas encore préchargée.")

    page = st.sidebar.radio(
        "Navigation",
        ["Vue d'ensemble", "Apprenant", "Clustering"],
    )
    st.sidebar.markdown("---")
    st.sidebar.caption(f"API : `{API_URL}`")

    if page == "Vue d'ensemble":
        render_home()
    elif page == "Apprenant":
        render_learner()
    elif page == "Clustering":
        render_clustering()


if __name__ == "__main__":
    main()
else:
    # `streamlit run` exécute le module au top-level.
    main()
