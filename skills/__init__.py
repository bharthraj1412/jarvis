# skills/ — Reusable prompt-template skill system for JARVIS MK37.
"""
Skills are markdown files with YAML frontmatter that define reusable prompt
templates. They can be loaded from multiple sources:
  - Built-in skills (shipped with JARVIS)
  - User-level: ~/.jarvis/skills/*.md
  - Project-level: <cwd>/.jarvis/skills/*.md
  - OpenClaw / Claude / custom skill packs (via skills.installer)

Usage:
    from skills import load_skills, find_skill, execute_skill
"""

from skills.loader import (  # noqa: F401
    SkillDef,
    load_skills,
    find_skill,
    substitute_arguments,
    register_builtin_skill,
)
from skills.executor import execute_skill  # noqa: F401

# Importing builtin modules registers all built-in skills
from skills import builtin as _builtin  # noqa: F401
from skills import builtin_editor as _builtin_editor  # noqa: F401
from skills import builtin_extras as _builtin_extras  # noqa: F401
from skills import builtin_pro as _builtin_pro  # noqa: F401

