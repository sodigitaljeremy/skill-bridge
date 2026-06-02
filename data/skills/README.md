# Référentiel de compétences — numératie primaire

## Pourquoi un référentiel maison ?

ESCO est conçu pour le marché du travail. Sa granularité ne descend pas au niveau d'une
compétence de cycle 2 ou 3 (« addition à deux chiffres avec retenue », « lecture de l'heure »...).

Pour le démonstrateur **SkillBridge**, on choisit donc :

1. Un **référentiel maison** fin, calé sur le programme de l'Éducation nationale (cycles 2 et 3),
   versionné dans [`numeracy_primary.json`](numeracy_primary.json) — **source de vérité** des
   compétences utilisées dans le scénario maths primaire.
2. Un **mapping vers ESCO**, versionné dans [`esco_mapping.json`](esco_mapping.json), qui aligne
   chaque compétence maison vers un ou plusieurs nœuds ESCO quand une correspondance utile existe.

Cela démontre l'**interopérabilité sémantique** — cœur de la promesse Prometheus-X /
dataspace — sans forcer un mapping ESCO inadéquat.

## Structure des fichiers

### `numeracy_primary.json`

```json
{
  "version": "0.1.0",
  "source": "Référentiel maison inspiré du programme français cycles 2 et 3",
  "license": "CC0-1.0",
  "skills": [
    {
      "id": "addition_entiers",
      "preferred_label": "Addition d'entiers naturels",
      "description": "Calculer la somme...",
      "domain": "calcul_de_base"
    }
  ]
}
```

Champs :
- `id` : identifiant maison, snake_case, stable (référencé par les ressources et les traces).
- `preferred_label`, `description` : libellés humains FR.
- `domain` : groupe de compétences (clé du **vecteur d'ability** des apprenants). Domaines actuels :
  `calcul_de_base`, `calcul_avance`, `fractions_decimaux`, `geometrie_mesures`, `unites_temps`,
  `resolution_problemes`.

### `esco_mapping.json`

```json
{
  "mappings": {
    "calcul_mental": ["http://data.europa.eu/esco/skill/<uuid>"]
  }
}
```

Pour chaque `id` maison : 0..N URIs ESCO. Une compétence sans mapping a un tableau vide
côté `Skill.esco_uris` après chargement.

> ⚠️ Les URIs présentes au niveau 1 sont **illustratives**. Elles suivent la forme canonique
> ESCO (`http://data.europa.eu/esco/skill/<uuid>`) mais doivent être **vérifiées** via
> [esco.ec.europa.eu](https://esco.ec.europa.eu/) avant tout usage en production.

## Régénération / édition

C'est un fichier édité à la main. Pour ajouter une compétence :

1. Ajouter une entrée dans `numeracy_primary.json` (id stable, domaine cohérent).
2. Si pertinent, ajouter une entrée dans `esco_mapping.json`.
3. Si la compétence est utilisée par une ressource, la référencer dans
   [`../seed/resources_catalog.json`](../seed/resources_catalog.json) — les tests vérifient la
   cohérence (`tests/unit/test_resource_catalog.py`).

## Sources de référence

- **Programmes scolaires français** : [eduscol.education.fr](https://eduscol.education.fr/) —
  programmes cycles 2 et 3.
- **ESCO** : [esco.ec.europa.eu](https://esco.ec.europa.eu/) — taxonomie européenne des
  compétences, qualifications et professions.
