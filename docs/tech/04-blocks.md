# 04 — Vue des blocs (C4)

## Niveau 1 — Contexte système

```mermaid
flowchart TB
    subgraph users[Utilisateurs]
        L[Léa et apprenants]
        E[Évaluateur / recruteur]
    end

    SB[SkillBridge<br/>Data & AI provider]:::system

    subgraph dataspace[Écosystème Prometheus-X / DASES]
        LRC[learning-records-converter<br/>service de normalisation xAPI]:::ext
        PDC[dataspace-connector<br/>échange consenti]:::ext
        ESCO[ESCO<br/>référentiel européen]:::ext
    end

    App[Application Mathia<br/>simulée]:::ext

    L -->|utilise| App
    App -->|événements CSV| LRC
    LRC -->|xAPI DASES| PDC
    PDC -->|trace consentie| SB
    SB -.->|mapping sortant| ESCO
    E -->|consomme vitrine| SB

    classDef system fill:#e0f2f1,stroke:#00897b,stroke-width:2px
    classDef ext fill:#fff3e0,stroke:#e65100
```

## Niveau 2 — Containers

```mermaid
flowchart TB
    user[Utilisateur<br/>navigateur]

    subgraph skillbridge[SkillBridge — déployé sur VPS Hetzner / Coolify]
        ST[Vitrine Streamlit<br/>port 8501]:::container
        API[API FastAPI<br/>port 8000, lifespan préchargé]:::container
        FILES[(Artefacts JSONL<br/>data/generated/)]:::store
        SEEDS[(Seeds versionnés<br/>data/skills, data/seed)]:::store
    end

    LRC[LRC<br/>service externe HTTP]:::ext
    HF[Hugging Face<br/>modèle ST téléchargé au 1er boot]:::ext

    user -->|HTTP| ST
    ST -->|HTTP REST| API
    API --> FILES
    API --> SEEDS
    API -.->|au démarrage| HF
    %% Le LRC n'est pas appelé en chemin chaud de l'API ; il est invoqué par
    %% le script generate_dataset.py --via-lrc au moment de la génération.
    SEEDS -.->|sample CSV| LRC
    LRC -.->|xAPI JSONL| FILES

    classDef container fill:#e0f2f1,stroke:#00897b,stroke-width:1.5px
    classDef store fill:#eceff1,stroke:#607d8b
    classDef ext fill:#fff3e0,stroke:#e65100
```

### Lecture

- **Vitrine Streamlit** : seul l'utilisateur la voit. Elle consomme l'API en HTTP, plus
  une lecture locale de `learners.jsonl` pour la **validation cluster ↔ archétype**
  (étiquetée "vérité-terrain de simulation, indisponible en production réelle").
- **API FastAPI** : tout est calculé une fois au `lifespan` (profilage, clustering,
  embeddings, top-10 reco par apprenant). Chaque requête HTTP est un lookup en mémoire.
- **LRC** : pas dans le chemin chaud. Invoqué par `generate_dataset.py --via-lrc` pour
  produire `traces_via_lrc.jsonl` (échantillon démontré). Voir
  [ADR 004](adrs/004-lrc-runbook-vs-submodule.md).
- **Modèle ST** (`paraphrase-multilingual-MiniLM-L12-v2`) téléchargé une fois (~470 MB),
  ensuite chargé depuis le cache. Coût payé au démarrage, jamais par requête.

## Niveau 3 — Composants internes de l'API

```mermaid
flowchart LR
    subgraph inbound[adapters/inbound/api]
        ROUTES[Routes FastAPI<br/>health, learners, profile,<br/>clusters, recommend]
        STATE[PreloadedState<br/>dataclass frozen]
    end

    subgraph application[application/]
        PROFILE[LearnerProfileBuilder]
        CLUSTER[ClusteringService]
        RECO[RecommendationService]
    end

    subgraph outbound[adapters/outbound/]
        FILES[FileSkillRepository<br/>FileResourceRepository<br/>FileLearnersLoader<br/>FileEnrichedTraceLoader]
        EMB[SentenceTransformersEmbeddingProvider]
    end

    LIFESPAN[lifespan]:::lifecycle
    LIFESPAN --> FILES
    LIFESPAN --> PROFILE
    LIFESPAN --> CLUSTER
    LIFESPAN --> EMB
    LIFESPAN --> RECO
    LIFESPAN --> STATE

    ROUTES --> STATE

    classDef lifecycle fill:#f3e5f5,stroke:#7b1fa2
```

Les composants `domain/` (entités Pydantic, ports Protocol) ne sont pas représentés —
ils sont importés par toutes les couches mais n'ont pas de dépendance sortante.

## Structure des packages

```
src/skill_bridge/
├── domain/
│   ├── entities.py        # Skill, LearningResource, Learner, LearningTrace,
│   │                      # LearnerProfile, ClusterAssignment, Recommendation
│   ├── enums.py           # ResourceType, LearningVerb, URIs canoniques xAPI
│   └── ports.py           # 5 Protocols : SkillRepository, LearningResourceRepository,
│                          # TraceEncoder, EmbeddingProvider, TraceConverter
├── application/
│   ├── trace_generation.py    # archétypes + sampling stratifié
│   ├── enrichment.py          # join trace ↔ skills
│   ├── profiling.py           # features par apprenant
│   ├── clustering.py          # KMeans + silhouette + naming
│   └── recommendation.py      # détection faiblesses + scoring + explication
└── adapters/
    ├── inbound/
    │   ├── api/ …              # FastAPI (factory create_app)
    │   └── streamlit_app.py    # Vitrine (single file)
    └── outbound/
        ├── file_skill_repository.py
        ├── file_resource_repository.py
        ├── jsonl_loaders.py
        ├── xapi_encoder.py
        ├── csv_trace_encoder.py
        ├── csv_writer.py
        ├── dataset_writer.py
        ├── lrc_http_converter.py
        ├── stub_lrc_converter.py
        ├── sentence_transformers_provider.py
        └── stub_embedding_provider.py
```
