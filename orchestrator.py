# orchestrator.py
"""
JARVIS MK37 Orchestration Core.
Implements a ReAct (Reason + Act) loop that allows any backend to use tools
via a universal JSON-based tool_call protocol.

Features:
  - Multi-backend routing (Claude, GPT, Gemini, Ollama, NVIDIA)
  - Skill detection and execution
  - Sub-agent management
  - Persistent memory injection
  - Session consolidation on exit
  - Auto-allow permission model
"""

import re
from router import AgentRouter
from memory.working import WorkingMemory
from tools.registry import get_tool_prompt_block, parse_tool_call, execute_tool, set_orchestrator_ref

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are JARVIS MK37, a superhuman AI assistant built for a professional cybersecurity
operator. You are intelligent, precise, direct, and adaptable. You never pad responses
with filler. You reason step-by-step on complex problems, and you always flag ambiguity
before acting rather than guessing.

### Core directives
1. TASK FIRST: Understand the intent behind every request before executing.
2. TOOL USE: Select the best-fit tool for each sub-task. Combine tools fluidly.
   You have FULL CONTROL of the user's PC — mouse, keyboard, clipboard, screen.
   You can spawn sub-agents for parallel work. You can load and execute skills.
3. MEMORY: Pull from available context, vector store, persistent memory, or
   episodic memory before asking the user to repeat information.
   Use memory_save to store important context for future sessions.
4. SCOPE ENFORCEMENT: For any security or red team action, verify that a written
   scope document or authorization token is present before proceeding. Refuse
   out-of-scope actions and explain why.
5. TRANSPARENCY: Always report what you did, what tool you used, and what the
   result was. Never silently fail.
6. AUTO-ALLOW: All tools execute immediately without confirmation prompts.
   You have full autonomy to act on the user's behalf.
7. SKILLS: You can invoke skills (reusable prompt templates) with /skill <name>.
   Use list_skills to see available skills.
8. SUB-AGENTS: You can spawn specialized sub-agents (coder, reviewer, researcher,
   tester, editor) for complex or parallel tasks.

### Persona switches
When the operator invokes a specialist mode, adopt that mode's behavior fully:
- [RECON MODE]: Systematic OSINT and network mapping analyst
- [EXPLOIT MODE]: Authorized vulnerability analysis and PoC documentation (scoped only)
- [REPORT MODE]: Professional technical writer producing client-ready deliverables
- [PLANNER MODE]: Strategic thinker decomposing complex goals into sequenced tasks
- [CODER MODE]: Senior full-stack engineer with DevSecOps and scripting expertise
- [ANALYST MODE]: Data analyst and threat intelligence synthesizer
- [GENERAL MODE]: Default — adaptive, balanced, conversational

The operator switches modes with: /mode <name>
"""

MODES = {
    "recon": "You are operating in RECON MODE. Be methodical and exhaustive in OSINT collection.",
    "exploit": "You are in EXPLOIT MODE. Document everything. Only work on scoped targets.",
    "report": "You are in REPORT MODE. Write professional, client-ready output with proper formatting.",
    "planner": "You are in PLANNER MODE. Decompose goals into ordered, actionable tasks.",
    "coder": "You are in CODER MODE. Write clean, tested, documented code. Follow PEP 8 for Python.",
    "analyst": "You are in ANALYST MODE. Synthesize data into clear, actionable insights.",
    "general": "",
}

MAX_REACT_STEPS = 15  # Increased from 8 for complex multi-tool tasks


class JarvisOrchestrator:
    def __init__(self, router: AgentRouter, use_vector_memory: bool = True):
        self.router = router
        self.working_memory = WorkingMemory()
        self.vector_memory = None
        self.current_mode = "general"
        self._subagent_mgr = None

        # Register self as the orchestrator reference for tools
        set_orchestrator_ref(self)

        if use_vector_memory:
            try:
                from memory.vector_store import VectorMemory
                self.vector_memory = VectorMemory()
            except Exception as e:
                print(f"[JARVIS] Vector memory unavailable: {e}")

    def _parse_mode(self, user_input: str) -> str | None:
        m = re.match(r"^/mode\s+(\w+)", user_input.strip())
        if m:
            mode = m.group(1).lower()
            if mode in MODES:
                self.current_mode = mode
                return f"[Mode switched to {mode.upper()}]"
            else:
                return f"[Unknown mode: {mode}. Available: {', '.join(MODES.keys())}]"
        return None

    def _build_system(self) -> str:
        parts = [SYSTEM_PROMPT]

        mode_addendum = MODES.get(self.current_mode, "")
        if mode_addendum:
            parts.append(f"\n### Active Mode\n{mode_addendum}")

        # Inject persistent memory context
        try:
            from memory.memory_context import get_memory_context
            mem_ctx = get_memory_context(include_guidance=True)
            if mem_ctx:
                parts.append(f"\n{mem_ctx}")
        except Exception:
            pass

        # Inject tool definitions
        parts.append(get_tool_prompt_block())

        return "\n".join(parts)

    def _extract_keywords(self, text: str) -> list[str]:
        keywords = []
        low = text.lower()
        if any(w in low for w in ["code", "script", "function", "debug", "write a", "program"]):
            keywords.append("code")
        if any(w in low for w in ["scan", "recon", "pentest", "vuln", "exploit", "nmap", "port"]):
            keywords.append("security")
        if any(w in low for w in ["search", "find", "look up", "google", "what is", "who is"]):
            keywords.append("search")
        if any(w in low for w in ["private", "local", "offline", "no cloud"]):
            keywords.append("local_private")
        if any(w in low for w in ["creative", "story", "poem", "imagine"]):
            keywords.append("creative")
        return keywords

    def _recall_context(self, user_input: str) -> str:
        """Pull relevant memories from vector store if available."""
        if not self.vector_memory:
            return ""
        try:
            memories = self.vector_memory.recall(user_input, n=3)
            if memories:
                return "[Recalled context from memory]:\n" + "\n---\n".join(memories) + "\n\n"
        except Exception:
            pass
        return ""

    def _store_exchange(self, user_input: str, response: str):
        """Store the Q&A pair in vector memory for future recall."""
        if not self.vector_memory:
            return
        try:
            self.vector_memory.store(
                f"Q: {user_input}\nA: {response[:500]}",
                metadata={"mode": self.current_mode},
            )
        except Exception:
            pass

    def _check_skill(self, user_input: str) -> str | None:
        """Check if input matches a skill trigger and execute it."""
        try:
            from skills import find_skill, execute_skill
            # Check for /skill <name> syntax
            skill_match = re.match(r"^/skill\s+(\S+)\s*(.*)", user_input.strip())
            if skill_match:
                skill_name = skill_match.group(1)
                skill_args = skill_match.group(2).strip()
                from skills import load_skills
                skill = None
                for s in load_skills():
                    if s.name == skill_name:
                        skill = s
                        break
                if skill is None:
                    skill = find_skill(f"/{skill_name}")
                if skill:
                    return execute_skill(skill, skill_args, self)
                return f"[Unknown skill: {skill_name}]"

            # Check for direct trigger match (e.g., /commit, /review)
            skill = find_skill(user_input.split()[0] if user_input.strip() else "")
            if skill:
                # Extract args after the trigger
                trigger_len = len(user_input.split()[0])
                skill_args = user_input[trigger_len:].strip()
                return execute_skill(skill, skill_args, self)
        except Exception as e:
            print(f"[JARVIS] Skill check error: {e}")
        return None

    def chat(self, user_input: str) -> str:
        """
        Main chat method with ReAct tool execution loop.
        The LLM can output tool_call blocks which are executed and fed back
        until the LLM produces a final text-only response.
        """
        # Check for mode switch commands
        mode_switch = self._parse_mode(user_input)
        if mode_switch:
            return mode_switch

        # Check for skill invocation
        skill_result = self._check_skill(user_input)
        if skill_result:
            return skill_result

        # Augment with recalled context
        memory_context = self._recall_context(user_input)
        augmented = f"{memory_context}[User]: {user_input}" if memory_context else user_input

        self.working_memory.add("user", augmented)

        # Route to best backend
        keywords = self._extract_keywords(user_input)
        profile = self.router.route(keywords)

        # Fallback: if routed backend not available, use default
        if profile not in self.router.backends:
            profile = self.router.default

        system = self._build_system()

        # ── ReAct Loop ────────────────────────────────────────────────────
        final_response = ""
        for step in range(MAX_REACT_STEPS):
            try:
                response = self.router.run(profile, self.working_memory.get(), system)
            except Exception as e:
                final_response = f"Backend error ({profile.value}): {e}"
                break

            # Check if the response contains a tool call
            tool_name, tool_args = parse_tool_call(response)

            if tool_name:
                # Execute the tool — AUTO-ALLOW, no permission checks
                print(f"[JARVIS] 🔧 Step {step+1}: Executing tool '{tool_name}' with args: {tool_args}")
                tool_result = execute_tool(tool_name, tool_args)

                # Strip the tool_call block from the response to get any reasoning text
                clean_response = re.sub(
                    r'```tool_call\s*\n\s*\{.*?\}\s*\n\s*```',
                    '', response, flags=re.DOTALL
                ).strip()

                if clean_response:
                    self.working_memory.add("assistant", clean_response)

                # Feed the tool result back as a system message
                tool_feedback = f"[Tool Result for '{tool_name}']:\n{tool_result}"
                self.working_memory.add("user", tool_feedback)
                continue
            else:
                # No tool call — this is the final response
                final_response = response
                break
        else:
            # Hit max steps
            final_response += "\n\n[JARVIS: Max tool execution steps reached. Returning current results.]"

        self.working_memory.add("assistant", final_response)
        self._store_exchange(user_input, final_response)

        return final_response

    def consolidate_on_exit(self):
        """Run session consolidation to extract long-term memories."""
        try:
            from memory.consolidator import consolidate_session
            saved = consolidate_session(self.working_memory.get(), router=self.router)
            if saved:
                print(f"[JARVIS] 💾 Consolidated {len(saved)} memories: {', '.join(saved)}")
        except Exception as e:
            print(f"[JARVIS] Consolidation skipped: {e}")

    def shutdown(self):
        """Clean up resources on exit."""
        self.consolidate_on_exit()
        if self._subagent_mgr:
            self._subagent_mgr.shutdown()
