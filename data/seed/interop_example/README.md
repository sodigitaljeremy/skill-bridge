# Fixture interopérabilité — capture LRC réelle

Cette fixture est utilisée par l'encart "Interopérabilité" de la vitrine Streamlit en
**production** (où le LRC n'est pas déployé en ligne). Les deux fichiers sont une
**capture réelle** d'une conversion `/convert_custom` du LRC à un instant donné :

- [`mathia_row.csv`](mathia_row.csv) — 1 en-tête + 1 ligne de trace brute Mathia
  (Léa Martin, EX011 « Fractions simples – colorier », passed, score 0.567).
- [`lrc_statement.json`](lrc_statement.json) — le statement xAPI exact retourné par le
  LRC pour cette ligne, joliment formaté pour affichage.

## Reproductibilité

Pour régénérer ces fichiers à partir d'une démo locale :

```bash
# Démarrer le LRC (cf. docs/lrc_runbook.md)
cd ~/Desktop/lrc
docker compose --profile dev up -d
sleep 15

# Générer le dataset complet + l'échantillon LRC
cd ~/Desktop/skill-bridge
uv run python scripts/generate_dataset.py --seed 42 --via-lrc=http://localhost:8080

# Extraire la fixture
{ head -1 data/generated/sample_mathia.csv; sed -n '2p' data/generated/sample_mathia.csv; } \
  > data/seed/interop_example/mathia_row.csv
head -1 data/generated/traces_via_lrc.jsonl | python3 -m json.tool \
  > data/seed/interop_example/lrc_statement.json

# Arrêter le LRC
cd ~/Desktop/lrc
docker compose --profile dev down
```

## Pourquoi une fixture committée

Au Lot 5d, l'API + le front sont déployés sur Hetzner. Le LRC, lui, **n'est pas
déployé en ligne** — il est consommé uniquement en local pour la démo
d'interopérabilité. Pour que l'encart de la vitrine reste fonctionnel en prod sans
LRC up, on lit cette fixture committée à la place de `data/generated/`.

Cf. [ADR 004](../../../docs/tech/adrs/004-lrc-runbook-vs-submodule.md) et
[ADR 006](../../../docs/tech/adrs/006-csv-custom-vs-mappers-natifs.md).
