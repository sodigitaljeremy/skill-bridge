# Régénérer le dataset (autres seeds, autre volume)

## Pourquoi

Le dataset par défaut (100 apprenants, seed=42) est reproductible et adapté à la démo.
Tu peux le re-générer avec d'autres paramètres pour :

- tester la robustesse du clustering à un volume différent ;
- explorer une seed alternative ;
- raccourcir la génération pour itérer.

## Commande

```bash
uv run python scripts/generate_dataset.py [OPTIONS]
```

Options principales :

| Flag | Défaut | Effet |
| --- | --- | --- |
| `--learners` | `100` | Nombre d'apprenants (Léa incluse) |
| `--traces-mean` | `60` | Nombre moyen de traces par apprenant |
| `--traces-std` | `15` | Écart-type du nombre de traces |
| `--window-days` | `90` | Étendue temporelle (jours) |
| `--seed` | `42` | Seed RNG (numpy + Faker) — reproductibilité totale |
| `--output-dir` | `data/generated` | Dossier de sortie |

## Exemples

### Petit dataset rapide pour itérer

```bash
uv run python scripts/generate_dataset.py --learners 20 --traces-mean 30 --seed 1
```

### Gros dataset (plus de variance dans les clusters)

```bash
uv run python scripts/generate_dataset.py --learners 500 --traces-mean 80
```

⚠️ Au-delà de 200 apprenants, le précompute des recommandations au boot de l'API
prend plus de temps. Compter ~25 s pour 100 apprenants, ~120 s pour 500.

### Régénérer en passant aussi par le LRC

```bash
uv run python scripts/generate_dataset.py --via-lrc=http://localhost:8080
```

Émet en plus `data/generated/sample_mathia.csv` et `data/generated/traces_via_lrc.jsonl`
(échantillon converti par le vrai LRC). Voir
[How-to — ingérer via le LRC](ingest-via-lrc.md).

## Effets sur la vitrine et l'API

- L'**API** charge les fichiers à son `lifespan`. Pour qu'elle voie le nouveau dataset,
  **relance l'API** (`make api` ou `make demo`).
- La **vitrine** lit `learners.jsonl` localement pour la validation cluster ↔ archétype.
  Le cache `@st.cache_data(ttl=300)` peut retenir des données stale — clique sur le
  bouton "Clear cache" du menu Streamlit, ou attends 5 minutes.
