# skills/executor.py
"""
Skill execution: inline (current conversation) or forked (sub-agent).
Adapted from the Claude Code collection for JARVIS MK37.
"""
from __future__ import annotations

from skills.loader import SkillDef, substitute_arguments


def execute_skill(
    skill: SkillDef,
    args: str,
    orchestrator,
    config: dict = None,
) -> str:
    """Execute a skill and return its output as a string.

    If skill.context == "fork", runs as an isolated sub-agent.
    Otherwise (inline), injects the rendered prompt into the current orchestrator.

    Args:
        skill:        SkillDef to execute
        args:         raw argument string from user (after the trigger word)
        orchestrator: JarvisOrchestrator instance
        config:       optional config overrides
    Returns:
        Result text from the skill execution.
    """
    rendered = substitute_arguments(skill.prompt, args, skill.arguments)
    message = f"[Skill: {skill.name}]\n\n{rendered}"

    if skill.context == "fork":
        return _execute_forked(skill, message, orchestrator, config)
    else:
        return _execute_inline(message, orchestrator)


def _execute_inline(message: str, orchestrator) -> str:
    """Run skill prompt inline in the current conversation."""
    return orchestrator.chat(message)


def _execute_forked(
    skill: SkillDef,
    message: str,
    orchestrator,
    config: dict = None,
) -> str:
    """Run skill as an isolated sub-agent (separate conversation context)."""
    try:
        from multi_agent.subagent import SubAgentManager, AgentDefinition

        mgr = getattr(orchestrator, '_subagent_mgr', None)
        if mgr is None:
            mgr = SubAgentManager()
            orchestrator._subagent_mgr = mgr

        # Build agent definition from skill
        agent_def = AgentDefinition(
            name=f"skill-{skill.name}",
            description=skill.description,
            system_prompt="",
            model=skill.model or "",
            tools=skill.tools,
            source="skill",
        )

        task = mgr.spawn(
            prompt=message,
            orchestrator=orchestrator,
            depth=0,
            agent_def=agent_def,
            name=f"skill-{skill.name}",
        )

        # Wait for completion
        mgr.wait(task.id, timeout=300)
        return task.result or f"(skill '{skill.name}' completed with no output)"

    except Exception as e:
        return f"Skill fork error: {e}"
