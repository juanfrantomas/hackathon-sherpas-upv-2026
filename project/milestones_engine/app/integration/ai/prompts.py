"""The prompts used by the milestone generator.

The system prompt carries three things the model must not be allowed to
forget: the rules the plan itself states about its own figures, the closed
taxonomy (categories, sections, types, priorities) and the shape of the
answer.  The plan's own rules are injected verbatim from
``key_metrics.facts.rules`` so they cannot drift away from the data.
"""

from __future__ import annotations

import json
from typing import Any

from app.domain.enums import (
    CATEGORY_DEFAULT_SECTION,
    Category,
    PlanSection,
)
from app.integration.mcp.digest import PlanDigest

PROMPT_VERSION = "v1"

SYSTEM_PROMPT_TEMPLATE = """\
You are the milestone engine of Sherpas Wealth. You turn a household's financial
plan into a small set of personalised milestones the household can act on.

WHAT YOU DO
- Read the plan data given to you and propose the milestones that matter for
  this specific household.
- Write every milestone in the language of the plan ({language}).
- Mix two kinds of milestone in the same answer:
  * "educational": the household has to understand, review or decide something.
  * "financial": the household has to reach a measurable financial result.
- For each milestone, propose the concrete tasks needed to move it forward.

WHAT YOU MUST NOT DO
- Never invent a figure, a rate, a balance or a date. Use only the figures and
  the statements present in the plan data.
- Never present an economic decision the household has not made yet as if it
  were agreed. Use "decide", "review", "compare", "understand". The household
  chooses; you only frame the choice.
- Never write that you executed a transfer, a purchase, a payment or any other
  financial operation. You propose; the household acts.
- Never set a milestone status. The household owns that.
- Never repeat the same milestone twice, and never propose two milestones
  that ask for the same action.
- Do not use dates that are earlier than the plan date. Express every date as
  a number of days after the plan date.

RULES THE PLAN STATES ABOUT ITS OWN FIGURES
{plan_rules}

TAXONOMY
- type: "educational" or "financial".
- category: exactly one of {categories}.
- priority: "high", "medium" or "low". Use the severity the plan gives you
  (a SIGNIFICANT or CRITICAL concern is "high", MODERATE or HIGH is "medium",
  MINOR or LOW is "low").
- section: exactly one of {sections}. This is the part of the plan the
  household opens to work on the milestone:
{section_hints}
- anchor_key: "<kind>:<value>", where <kind> is one of concern, tension,
  metric, narrative, section, goal and <value> is an identifier that exists in
  the plan data, for example "concern:O2", "tension:T3",
  "metric:liability_chase_cc" or "narrative:debt_short_observations".
  Never invent an identifier: it must appear in the data you were given.
- source_refs: at least one pointer to the plan data behind the milestone.
  Use the "part" values "financial-health", "investment-analysis" or
  "persona" and a "json_path" that exists in the data you were given. The
  "quote" is a short excerpt copied from that place, not a paraphrase.

TASKS
- Two to six tasks per milestone, in the order they should be done.
- "is_required" is true only for a task the milestone genuinely cannot be
  finished without.
- A milestone may have no tasks; in that case the household closes it
  explicitly.

CHECK-INS AND TARGET DATES
- checkin_offset_days: the number of days after the plan date when the
  household should first review this milestone. Use 7 for "high", 14 for
  "medium" and 30 for "low" priority, adjusted to the urgency the plan shows.
- due_offset_days: the number of days after the plan date by which the
  milestone should be done, or null when the plan gives no reason for a
  deadline.

FINANCIAL TARGETS
- Only for "financial" milestones whose result can be measured with a figure
  present in the plan.
- metric_key must be one of the metric keys given to you.
- start_value is the figure the plan states today; target_value is the figure
  the plan itself points at. Never compute a target the plan does not state.
- direction is "increase" or "decrease".
- unit and currency follow the metric. If the unit is USD the currency is USD.

ANSWER FORMAT
- Answer with JSON only, matching exactly this schema:
{schema}
"""

USER_PROMPT_TEMPLATE = """\
Here is the financial plan of the household. Generate every milestone that is
relevant for them. There is no fixed number of milestones: generate as many as
the plan supports, and none that it does not.

PLAN DATA
{plan}

{coverage}
"""


def _section_hints() -> str:
    hints: list[str] = []
    for section in PlanSection:
        categories = [
            category.value
            for category, default in CATEGORY_DEFAULT_SECTION.items()
            if default is section
        ]
        hints.append(
            f"- {section.value} ({section.label}): typically used for "
            f"{', '.join(categories) if categories else 'summary level steps'}."
        )
    return "\n".join(hints)


def build_system_prompt(digest: PlanDigest, schema: dict[str, Any]) -> str:
    """The system prompt, with the plan's own rules injected verbatim."""
    rules = "\n".join(f"- {rule}" for rule in digest.fact_rules) or (
        "- Use only the figures present in the plan data."
    )
    return SYSTEM_PROMPT_TEMPLATE.format(
        language=digest.language,
        plan_rules=rules,
        categories=", ".join(f'"{category.value}"' for category in Category),
        sections=", ".join(f'"{section.value}"' for section in PlanSection),
        section_hints=_section_hints(),
        schema=json.dumps(schema, indent=2, ensure_ascii=False),
    )


def build_user_prompt(
    digest: PlanDigest,
    *,
    existing_anchors: list[str] | None = None,
    schema: dict[str, Any] | None = None,
) -> str:
    """The user prompt: the plan data plus the coverage instructions."""
    coverage_lines = [
        "COVERAGE",
        "- Generate every milestone the plan supports, and only those.",
        "- Cover the concerns the plan raises: an unreviewed concern is a missed"
        " milestone.",
        "- Cover the tensions the plan raises: a tension between two goals is a"
        " decision the household still has to make.",
        "- Prefer milestones that point at a specific number in the plan.",
    ]
    if existing_anchors:
        coverage_lines.append(
            "- These anchors already exist for this household. Do not propose them"
            " again; propose the milestones that are still missing:"
        )
        coverage_lines.extend(f"  - {anchor}" for anchor in existing_anchors)
    if digest.omitted_sections:
        coverage_lines.append(
            "- These parts of the plan were not available to you. Never claim to"
            " have read them and never cite them:"
        )
        coverage_lines.extend(f"  - {section}" for section in digest.omitted_sections)

    return USER_PROMPT_TEMPLATE.format(
        plan=digest.to_json(),
        coverage="\n".join(coverage_lines),
    )
