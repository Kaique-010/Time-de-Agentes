from __future__ import annotations


class ValidatorAgent:
    """Impede saída sem tenant safety."""

    REQUIRED_HINTS = (
        "slug",
        "tenant",
        "get_db_from_slug",
        "using(db)",
    )

    def validate(self, output: dict) -> tuple[bool, list[str]]:
        text = str(output).lower()
        errors: list[str] = []
        if not any(hint in text for hint in self.REQUIRED_HINTS):
            errors.append("Saída sem tenant safety: inclua slug/get_db_from_slug/.using(db).")
        return (len(errors) == 0, errors)
