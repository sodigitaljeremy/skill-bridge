"""Énumérations du domaine et URIs canoniques xAPI associées."""

from enum import StrEnum


class ResourceType(StrEnum):
    EXERCISE = "exercise"
    LESSON = "lesson"
    QUIZ = "quiz"


class LearningVerb(StrEnum):
    ATTEMPTED = "attempted"
    COMPLETED = "completed"
    PASSED = "passed"
    FAILED = "failed"


VERB_URIS: dict[LearningVerb, str] = {
    LearningVerb.ATTEMPTED: "http://adlnet.gov/expapi/verbs/attempted",
    LearningVerb.COMPLETED: "http://adlnet.gov/expapi/verbs/completed",
    LearningVerb.PASSED: "http://adlnet.gov/expapi/verbs/passed",
    LearningVerb.FAILED: "http://adlnet.gov/expapi/verbs/failed",
}

ACTIVITY_TYPE_URIS: dict[ResourceType, str] = {
    ResourceType.EXERCISE: "http://adlnet.gov/expapi/activities/performance",
    ResourceType.LESSON: "http://adlnet.gov/expapi/activities/lesson",
    ResourceType.QUIZ: "http://adlnet.gov/expapi/activities/assessment",
}
