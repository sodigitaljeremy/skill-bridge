# Ingérer un échantillon via le LRC réel

Cette procédure démontre l'**interopérabilité** : on encode un échantillon de traces
en CSV propriétaire, on le passe au LRC Prometheus-X réel, qui le renvoie en xAPI
conforme DASES.

## Vue d'ensemble

```
LearningTrace (domain)
       │
       │ CsvTraceEncoder
       ▼
sample_mathia.csv ─┐
                   │  POST /convert_custom (multipart)
data/seed/         │   ──────────────────────────────►   LRC service
lrc_mapping_       │                                         │
mathia.yml ────────┘                                         │ stream JSONL xAPI
                                                             ▼
                                                  traces_via_lrc.jsonl
```

Détails de conception : [ADR 006](../../tech/adrs/006-csv-custom-vs-mappers-natifs.md).

## Étape 1 — Démarrer le LRC

Suis le [runbook LRC](../../lrc_runbook.md) (clone + checkout SHA pinné + `.env` + `docker
compose --profile dev up -d`).

Vérification :

```bash
curl -s -H "Host: lrc.localhost" http://localhost:8080/docs | head -1
# attendu : HTTP/1.1 200 ou un début de HTML
```

## Étape 2 — Lancer la conversion d'un échantillon

```bash
uv run python scripts/generate_dataset.py --seed 42 --via-lrc=http://localhost:8080
```

Le script :

1. Régénère le dataset complet en xapi-direct (comme `make dataset`).
2. **Sélectionne un échantillon** : Léa + 1 apprenant par archetype distinct. Soit 4
   apprenants, ~199 traces.
3. Encode l'échantillon en CSV "Mathia" via `CsvTraceEncoder` →
   `data/generated/sample_mathia.csv`.
4. Pinge `GET /docs` du LRC (sanity check).
5. POSTe le CSV + le mapping YAML versionné
   (`data/seed/lrc_mapping_mathia.yml`) à `POST /convert_custom`.
6. Stream la sortie JSONL vers `data/generated/traces_via_lrc.jsonl`.

Sortie console attendue :

```
=== Échantillon via LRC (http://localhost:8080) ===
Apprenants : 4 (Léa + 1 par archetype distinct). Traces à envoyer : 199.
Écrit 199 lignes dans data/generated/sample_mathia.csv.
Reçu 199 statements xAPI depuis le LRC -> data/generated/traces_via_lrc.jsonl.
Profils DASES : aucun (meta absent du flux /convert_custom).
```

Le `Profils DASES : aucun` est attendu — voir [ADR 005](../../tech/adrs/005-profil-dases-null.md).

## Étape 3 — Vérifier la sortie

```bash
head -1 data/generated/traces_via_lrc.jsonl | python3 -m json.tool
```

Tu dois voir un statement xAPI complet :

```json
{
  "actor": {
    "account": {"name": "Léa Martin", "homePage": "https://mathia.example.com"}
  },
  "object": {
    "id": "https://mathia.example.com/resource/EX011",
    "definition": {"name": {"fr-FR": "Fractions simples - colorier"},
                   "type": "http://adlnet.gov/expapi/activities/interaction"}
  },
  "verb": {"id": "http://adlnet.gov/expapi/verbs/passed",
           "display": {"en-US": "passed"}},
  "result": {"score": {"scaled": 0.567}, "completion": true},
  "timestamp": "2026-03-06T09:59:26+00:00"
}
```

L'**encart "Interopérabilité" de la vitrine** (Vue d'ensemble) lit ces fichiers et
montre l'avant/après en live.

## Étape 4 — Arrêter le LRC

```bash
cd ~/Desktop/lrc
docker compose --profile dev down
```

Libère les ports et les conteneurs ; le cache des images et le code restent en place
pour la prochaine fois.

## Limites assumées

- 95 % du dataset reste **généré en xapi-direct** (rapidité + reproductibilité). Seul
  l'échantillon démonstratif passe par le LRC. Voir [ADR 006](../../tech/adrs/006-csv-custom-vs-mappers-natifs.md).
- Le mapping YAML **n'écrit pas `result.success`** à cause d'un bug LRC à ce SHA. Le
  consommateur déduit `success` du `verb.id` en aval.
