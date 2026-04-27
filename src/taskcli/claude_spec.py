from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SpecResult:
    spec: str
    file: str
    line: int
    acceptance_criteria: list[str]
    edge_cases: list[str]


class AutoSpecError(Exception):
    """Error during auto-spec generation."""
    pass


def generate_spec(title: str, context: str = "") -> SpecResult:
    """Call Anthropic API to generate structured spec from task title.

    Returns a SpecResult with spec text, file/line hints, acceptance criteria,
    and edge cases. Falls back to a simple spec if API key is not set or
    the request fails.

    Uses the latest Claude with prompt caching for efficiency.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        return _fallback_spec(title)

    try:
        import anthropic
    except ImportError:
        return _fallback_spec(title)

    prompt = _build_spec_prompt(title, context)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-opus-4-20251114",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        spec_text = message.content[0].text
        return _parse_spec_response(spec_text, title)
    except Exception as e:
        return _fallback_spec(title)


def _build_spec_prompt(title: str, context: str) -> str:
    return f"""Given the following task title, generate a structured specification:

Title: {title}
{f'Context: {context}' if context else ''}

Provide your response in this exact format (use --- for separators):

=== SPEC ===
[Brief spec paragraph explaining what this task accomplishes]

=== FILE_HINTS ===
file: <most_relevant_file.py>
line: <approximate_line_number>
or leave empty if unknown

=== ACCEPTANCE_CRITERIA ===
- Criterion 1
- Criterion 2
- ...

=== EDGE_CASES ===
- Edge case 1
- Edge case 2
- ...

Be concise. Focus on the most likely implementation details."""


def _parse_spec_response(response: str, title: str) -> SpecResult:
    spec_lines = []
    file_hint = ""
    line_hint = 0
    criteria = []
    edge_cases = []
    section = None

    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("=== SPEC ==="):
            section = "spec"
        elif line.startswith("=== FILE_HINTS ==="):
            section = "file"
        elif line.startswith("=== ACCEPTANCE_CRITERIA ==="):
            section = "criteria"
        elif line.startswith("=== EDGE_CASES ==="):
            section = "edge"
        elif section == "spec" and line:
            spec_lines.append(line)
        elif section == "file" and "file:" in line:
            file_hint = line.split("file:")[1].strip().split(":")[0].strip()
            try:
                parts = line.split("file:")[1].strip()
                if ":" in parts:
                    line_str = parts.split(":")[1].strip()
                    line_hint = int(line_str)
            except (ValueError, IndexError):
                pass
        elif section == "criteria" and line.startswith("-"):
            criteria.append(line.lstrip("- ").strip())
        elif section == "edge" and line.startswith("-"):
            edge_cases.append(line.lstrip("- ").strip())

    spec_text = " ".join(spec_lines)
    if spec_lines:
        spec_text += "\n\nAcceptance Criteria:\n" + "\n".join(f"- {c}" for c in criteria)
    if edge_cases:
        spec_text += "\n\nEdge Cases:\n" + "\n".join(f"- {e}" for e in edge_cases)

    return SpecResult(
        spec=spec_text,
        file=file_hint,
        line=line_hint,
        acceptance_criteria=criteria,
        edge_cases=edge_cases,
    )


def _fallback_spec(title: str) -> SpecResult:
    return SpecResult(
        spec=f"Implement: {title}",
        file="",
        line=0,
        acceptance_criteria=[],
        edge_cases=[],
    )


__all__ = ["generate_spec", "AutoSpecError", "SpecResult"]