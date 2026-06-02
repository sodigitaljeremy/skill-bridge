"""Profilage : dérivation d'un ``LearnerProfile`` à partir des traces enrichies.

Le profil est **observé** (calculé sur les traces), jamais lu depuis ``Learner.ability``.
Pour clustering on n'expose que ``mean_score_per_domain`` et ``success_rate_per_domain`` ;
``mean_score_per_skill`` est conservé en interne pour le ciblage fin de la recommandation.
"""

from collections import defaultdict
from typing import Final

from skill_bridge.application.enrichment import EnrichedTrace
from skill_bridge.domain.entities import Learner, LearnerProfile, Skill

NEUTRAL_DEFAULT: Final[float] = 0.5  # quand on n'a pas d'évidence dans un domaine/skill


class LearnerProfileBuilder:
    """Construit un profil par apprenant à partir des traces enrichies."""

    def __init__(self, skills: list[Skill]) -> None:
        self._skills = skills
        self._domains = sorted({s.domain for s in skills})
        self._all_skill_ids = sorted(s.id for s in skills)

    def build_all(
        self, learners: list[Learner], enriched_traces: list[EnrichedTrace]
    ) -> list[LearnerProfile]:
        by_learner: dict[str, list[EnrichedTrace]] = defaultdict(list)
        for trace in enriched_traces:
            by_learner[trace.learner_id].append(trace)
        return [
            self._build_one(learner, by_learner.get(learner.mbox_sha1sum, []))
            for learner in learners
        ]

    def _build_one(self, learner: Learner, traces: list[EnrichedTrace]) -> LearnerProfile:
        # On ne compte que les attempts scorés pour mean_score et success_rate
        # (les leçons n'ont pas de score et ne différencient pas la maîtrise).
        scores_per_domain: dict[str, list[float]] = defaultdict(list)
        passed_per_domain: dict[str, int] = defaultdict(int)
        total_per_domain: dict[str, int] = defaultdict(int)
        scores_per_skill: dict[str, list[float]] = defaultdict(list)
        attempted: list[str] = []

        for trace in traces:
            attempted.append(trace.resource_id)
            if trace.score is None or not trace.skills:
                continue
            primary_domain = trace.skills[0].domain
            scores_per_domain[primary_domain].append(trace.score)
            total_per_domain[primary_domain] += 1
            if trace.verb == "passed":
                passed_per_domain[primary_domain] += 1
            for skill in trace.skills:
                scores_per_skill[skill.id].append(trace.score)

        mean_score_per_domain = {
            d: (sum(scores_per_domain[d]) / len(scores_per_domain[d]))
            if scores_per_domain[d]
            else NEUTRAL_DEFAULT
            for d in self._domains
        }
        success_rate_per_domain = {
            d: (passed_per_domain[d] / total_per_domain[d])
            if total_per_domain[d]
            else NEUTRAL_DEFAULT
            for d in self._domains
        }
        mean_score_per_skill = {
            sid: (sum(scores_per_skill[sid]) / len(scores_per_skill[sid]))
            if scores_per_skill[sid]
            else NEUTRAL_DEFAULT
            for sid in self._all_skill_ids
        }

        return LearnerProfile(
            learner_id=learner.learner_id,
            mbox_sha1sum=learner.mbox_sha1sum,
            grade_level=learner.grade_level,
            mean_score_per_domain=mean_score_per_domain,
            success_rate_per_domain=success_rate_per_domain,
            mean_score_per_skill=mean_score_per_skill,
            attempted_resource_ids=sorted(set(attempted)),
            n_traces=len(traces),
        )
