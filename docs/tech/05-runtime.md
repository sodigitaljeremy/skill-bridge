# 05 — Vue runtime

Deux séquences clés : **génération du dataset** (préalable, batch) et **consommation
par la vitrine** (chemin chaud, runtime de l'API).

## Séquence A — Génération du dataset enrichi (batch)

Exécutée via `make dataset` (ou `python scripts/generate_dataset.py`). Reproductible
via la seed unique `42`.

```mermaid
sequenceDiagram
    autonumber
    participant CLI as scripts/generate_dataset.py
    participant Seeds as data/skills + data/seed
    participant Gen as TraceGenerationService
    participant Enr as EnrichmentService
    participant FS as data/generated/

    CLI->>Seeds: load skills + resources
    CLI->>Gen: generate(ScenarioConfig(n=100, seed=42))
    Gen-->>Gen: tirer 4 archetypes + jitter σ=0.10
    Gen-->>Gen: échantillonnage stratifié par domaine
    Gen-->>CLI: 100 learners + 5800 LearningTrace
    CLI->>FS: traces.jsonl (xAPI direct)
    CLI->>Enr: enrich(trace) pour chaque
    Enr-->>CLI: EnrichedTrace (+ skills résolues)
    CLI->>FS: enriched.jsonl
    CLI->>FS: learners.jsonl (ground truth, archetype inclus)
```

### Variante — via le LRC réel (échantillon)

Si l'opérateur passe `--via-lrc=http://localhost:8080`, le script ajoute :

```mermaid
sequenceDiagram
    autonumber
    participant CLI as generate_dataset.py
    participant Enc as CsvTraceEncoder
    participant LRC as "LRC (HTTP)"
    participant FS as data/generated/

    CLI->>CLI: pick (Léa + 1/archetype) — 4 apprenants, 199 traces
    CLI->>Enc: encode chaque trace en ligne CSV "Mathia"
    CLI->>FS: sample_mathia.csv
    CLI->>LRC: POST /convert_custom (multipart)
    LRC-->>CLI: stream JSONL xAPI (199 statements)
    CLI->>FS: traces_via_lrc.jsonl
```

Voir [How-to — ingest via LRC](../user/how-to/ingest-via-lrc.md) et
[ADR 006](adrs/006-csv-custom-vs-mappers-natifs.md).

## Séquence B — Boot de l'API (lifespan)

Au démarrage de `uvicorn ... --factory`, **avant** que le serveur accepte la première
requête :

```mermaid
sequenceDiagram
    autonumber
    participant U as uvicorn
    participant APP as "create_app()"
    participant LIFE as lifespan
    participant FS as data/generated/
    participant Prof as LearnerProfileBuilder
    participant Clu as ClusteringService
    participant ST as SentenceTransformers
    participant Reco as RecommendationService

    U->>APP: instancie FastAPI
    APP->>LIFE: enter
    LIFE->>FS: load skills, resources, learners, enriched
    LIFE->>Prof: build_all → 100 profils
    LIFE->>Clu: fit (k_min=2, k_max=8, seed=42)
    Clu-->>LIFE: k=4, silhouette=0.309, assignations
    LIFE->>ST: charger MiniLM multilingue (≈ 5-15 s au 1er boot)
    LIFE->>Reco: instancier + embed 33 ressources
    loop pour chaque profil
        LIFE->>Reco: recommend(top_n=10)
    end
    LIFE-->>APP: PreloadedState sur app.state
    APP-->>U: prêt à servir
```

Coût total : ~5 s en chaud, **~25 s au tout premier boot** (download du modèle ST).
Les requêtes HTTP ne touchent **jamais** sklearn ni le modèle ST.

## Séquence C — Visualisation pour Léa (chemin chaud)

L'utilisateur sélectionne « Léa Martin » dans la vitrine Streamlit.

```mermaid
sequenceDiagram
    autonumber
    participant Browser
    participant ST as Vitrine Streamlit
    participant API as API FastAPI
    participant State as PreloadedState

    Browser->>ST: ouvre /, navigue "Apprenant"
    ST->>API: GET /learners
    API->>State: list[Learner]
    State-->>API: 100 entrées
    API-->>ST: JSON
    ST->>ST: cache (@st.cache_data, ttl=300)
    Note over ST: Léa sélectionnée par défaut

    par En parallèle
        ST->>API: GET /profile/{lea_id}
        ST->>API: GET /clusters/assignment/{lea_id}
        ST->>API: GET /clusters
        ST->>API: GET /recommend/{lea_id}?n=5
    end

    API->>State: lookup direct (aucun calcul)
    State-->>API: profil + assignation + cluster meta + recos préchargées
    API-->>ST: JSON

    ST-->>Browser: rendu — profil + cluster + 5 recos avec explication
```

Les 4 appels sont parallélisés par le navigateur (HTTP/2 ou pipelining), et chacun est
caché par Streamlit côté front. Temps d'affichage perçu : < 200 ms après le 1er load.
