"""
prompt_builder.py

Purpose
-------
Build the complete FieldOps AI system prompt by combining
multiple Markdown files.

Instead of maintaining one huge prompt inside Python,
the prompt is assembled from separate Markdown documents.

Benefits
--------
- Easy to maintain
- Easy to update
- Non-developers can edit prompts
- Clean separation of concerns
"""

from pathlib import Path
from typing import List


class PromptBuilder:
    """
    Responsible for assembling the complete
    FieldOps AI system prompt.
    """

    PROMPT_FILES: List[str] = [
        "IDENTITY.md",
        "SOUL.md",
        "knowledge/business_rules.md",
        "knowledge/lifecycle.md",
        "knowledge/roles.md",
        "knowledge/validation.md",

    ]

    def __init__(self):
        """
        Automatically locate the FieldOpsAI root directory.

        No caller should have to provide the path manually.
        """

        self.base_directory = Path(__file__).resolve().parent.parent

    # ---------------------------------------------------------

    def _read_markdown(self, relative_path: str) -> str:
        """
        Read a Markdown file.

        Parameters
        ----------
        relative_path
            Path relative to the FieldOpsAI directory.

        Returns
        -------
        str
            Markdown file contents.

        Raises
        ------
        FileNotFoundError
            If the required Markdown file is missing.
        """

        file_path = self.base_directory / relative_path

        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing AI configuration file: {file_path}"
            )

        return file_path.read_text(
            encoding="utf-8"
        ).strip()

    # ---------------------------------------------------------

    def build(self) -> str:
        """
        Build the complete system prompt.

        The prompt is assembled in a fixed order:

        Identity
            ↓
        Soul
            ↓
        Business Rules
            ↓
        Knowledge
            ↓
        Shared Communication Rules

        Returns
        -------
        str
            Complete system prompt.
        """

        sections: List[str] = [
            self._read_markdown(file)
            for file in self.PROMPT_FILES
        ]

        return "\n\n".join(sections)