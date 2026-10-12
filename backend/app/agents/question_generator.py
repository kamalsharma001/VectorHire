"""
VectorHire Evidence-Grounded Interview Question Generator Agent.
Generates targeted, professional interview questions tailored to a specific candidate's
evaluation scorecard and job requirements.
Guarantees:
- Strictly grounded in verified claims, uncertain evidence, or unevidenced requirements.
- Never asserts unsupported candidate deficiencies or incapacity.
- Probes depth of execution for strong claims, clarifies ambiguous mentions, and respectfully
  inquires about unevidenced requirements.
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.exceptions import ProviderAPIError
from app.providers.base_llm import BaseLLMProvider
from app.providers.provider_factory import get_llm_provider
from app.schemas.api import InterviewQuestion
from app.schemas.common import CandidateId, EvidenceStatus, RequirementCategory
from app.schemas.evaluation import CandidateScorecard, CriterionEvaluation
from app.schemas.job import JobSpecification

logger = logging.getLogger(__name__)

QUESTION_GENERATOR_SYSTEM_PROMPT = """You are a senior talent assessment specialist for VectorHire.
Your task is to generate professional, evidence-grounded interview questions tailored to a specific candidate's evaluation scorecard.

CRITICAL INSTRUCTIONS & ETHICAL GUIDELINES:
1. Every interview question must be grounded in actual resume evidence, partial evidence gaps, or specific job requirements.
2. DO NOT assert that the candidate lacks capability or is deficient. The absence of evidence in a resume is simply unevidenced, not proof of inability.
3. Focus Areas:
   - "Uncertain Evidence Clarification": When a skill is only listed in a skills list or coursework, ask how they applied it in professional production.
   - "Requirement Inquiry": When a requirement (especially a mandatory license or hard gate) was not evidenced in the resume, ask respectfully to clarify their background or current status.
   - "Technical/Clinical Depth": When a competency was explicitly supported, ask about advanced trade-offs, architecture decisions, or complex challenges.
4. Output professional, respectful, actionable questions that allow the candidate to demonstrate their true competence.

OUTPUT SCHEMA:
You MUST respond with a single valid JSON object formatted as follows:
{
  "questions": [
    {
      "requirement_id": "req_01",
      "requirement_name": "Requirement Name",
      "category": "mandatory_competencies | license_registration | experience_tenure | education | preferred_competencies",
      "question": "Clear, professional, evidence-probing question.",
      "rationale": "Why this question is being asked based on the candidate's evaluation evidence.",
      "focus_area": "Uncertain Evidence Clarification | Requirement Inquiry | Technical/Clinical Depth"
    }
  ]
}
"""


class QuestionGeneratorAgent:
    """
    Generates tailored, evidence-grounded interview questions for an evaluated candidate.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or get_llm_provider()
        self.settings = get_settings()

    def _build_prompt(
        self,
        candidate_name: str,
        job_spec: JobSpecification,
        scorecard: CandidateScorecard,
        max_questions: int,
    ) -> str:
        eval_summaries = []
        for ev in scorecard.evaluations:
            quote = ""
            if ev.evidence and ev.evidence.provenance and ev.evidence.provenance.exact_span_quote:
                quote = f" (Quote: '{ev.evidence.provenance.exact_span_quote[:150]}')"

            eval_summaries.append(
                f"- [{ev.requirement_id}] {ev.requirement_name} ({ev.category.value}): "
                f"Status={ev.status.value}, HardGate={ev.is_hard_gate}{quote}"
            )

        evals_text = "\n".join(eval_summaries)

        return f"""Generate at most {max_questions} interview questions for candidate {candidate_name} applying for {job_spec.job_title}.

CRITERIA EVALUATION SUMMARY:
{evals_text}

Generate {max_questions} evidence-grounded interview questions following the required JSON schema:"""

    def _fallback_deterministic_questions(
        self,
        scorecard: CandidateScorecard,
        max_questions: int,
    ) -> List[InterviewQuestion]:
        """Generates deterministic evidence-grounded template questions if LLM is unavailable."""
        questions: List[InterviewQuestion] = []

        # 1. Prioritize uncertain evidence and hard gates
        sorted_evals = sorted(
            scorecard.evaluations,
            key=lambda e: (e.is_hard_gate, e.status == EvidenceStatus.RELEVANT_BUT_UNCERTAIN),
            reverse=True,
        )

        for ev in sorted_evals:
            if len(questions) >= max_questions:
                break

            if ev.status == EvidenceStatus.RELEVANT_BUT_UNCERTAIN:
                q_text = (
                    f"In your resume, you referenced experience related to {ev.requirement_name}. "
                    f"Could you elaborate on a specific professional project where you applied this capability?"
                )
                rationale = f"Evidence for {ev.requirement_name} was partial or incidental; clarifying operational depth."
                focus = "Uncertain Evidence Clarification"
            elif ev.status == EvidenceStatus.NOT_MENTIONED:
                q_text = (
                    f"The role involves {ev.requirement_name}. Could you describe any background, "
                    f"training, or practical experience you have with this requirement?"
                )
                rationale = f"Requirement {ev.requirement_name} was not evidenced in the submitted resume."
                focus = "Requirement Inquiry"
            else:
                q_text = (
                    f"Your resume indicates strong experience with {ev.requirement_name}. "
                    f"What was one of the most challenging obstacles you navigated when applying this skill?"
                )
                rationale = f"Verifying advanced problem-solving depth for verified competency {ev.requirement_name}."
                focus = "Technical/Clinical Depth"

            questions.append(
                InterviewQuestion(
                    requirement_id=ev.requirement_id,
                    requirement_name=ev.requirement_name,
                    category=ev.category,
                    question=q_text,
                    rationale=rationale,
                    focus_area=focus,
                )
            )

        return questions

    def _sanitize_questions(
        self,
        raw_questions: List[Dict[str, Any]],
        scorecard: CandidateScorecard,
        max_questions: int,
    ) -> List[InterviewQuestion]:
        eval_map = {e.requirement_id: e for e in scorecard.evaluations}
        valid_questions: List[InterviewQuestion] = []

        for q in raw_questions:
            if not isinstance(q, dict):
                continue

            req_id = str(q.get("requirement_id", "")).strip()
            eval_record = eval_map.get(req_id)

            req_name = str(q.get("requirement_name", "")).strip()
            if eval_record and not req_name:
                req_name = eval_record.requirement_name
            elif not req_name:
                req_name = "Job Requirement"

            category = eval_record.category if eval_record else RequirementCategory.MANDATORY_COMPETENCY
            question_text = str(q.get("question", "")).strip()
            rationale_text = str(q.get("rationale", "")).strip()
            focus_area = str(q.get("focus_area", "General Inquiry")).strip()

            if len(question_text) >= 10 and len(rationale_text) >= 5:
                valid_questions.append(
                    InterviewQuestion(
                        requirement_id=req_id or (eval_record.requirement_id if eval_record else "req_01"),
                        requirement_name=req_name[:150],
                        category=category,
                        question=question_text[:1000],
                        rationale=rationale_text[:1000],
                        focus_area=focus_area[:100],
                    )
                )

            if len(valid_questions) >= max_questions:
                break

        return valid_questions or self._fallback_deterministic_questions(scorecard, max_questions)

    def generate_interview_questions(
        self,
        candidate_id: CandidateId,
        candidate_name: str,
        job_spec: JobSpecification,
        scorecard: CandidateScorecard,
        max_questions: int = 5,
    ) -> List[InterviewQuestion]:
        """
        Synchronously generates tailored interview questions for an evaluated candidate.
        """
        messages = [
            {"role": "system", "content": QUESTION_GENERATOR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": self._build_prompt(candidate_name, job_spec, scorecard, max_questions),
            },
        ]

        try:
            response_json = self.provider.generate_json(messages)
            raw_list = response_json.get("questions", [])
            return self._sanitize_questions(raw_list, scorecard, max_questions)
        except Exception as exc:
            logger.warning("QuestionGeneratorAgent LLM call failed: %s. Using deterministic fallback.", str(exc)[:200])
            return self._fallback_deterministic_questions(scorecard, max_questions)

    async def generate_interview_questions_async(
        self,
        candidate_id: CandidateId,
        candidate_name: str,
        job_spec: JobSpecification,
        scorecard: CandidateScorecard,
        max_questions: int = 5,
    ) -> List[InterviewQuestion]:
        """
        Asynchronously generates tailored interview questions for an evaluated candidate.
        """
        messages = [
            {"role": "system", "content": QUESTION_GENERATOR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": self._build_prompt(candidate_name, job_spec, scorecard, max_questions),
            },
        ]

        try:
            response_json = await self.provider.generate_json_async(messages)
            raw_list = response_json.get("questions", [])
            return self._sanitize_questions(raw_list, scorecard, max_questions)
        except Exception as exc:
            logger.warning("QuestionGeneratorAgent async LLM failed: %s. Using deterministic fallback.", str(exc)[:200])
            return self._fallback_deterministic_questions(scorecard, max_questions)
