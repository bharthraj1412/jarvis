"""JARVIS MK37 -- Deep Audit: Runtime cross-reference and logic bug test."""
import sys, os, traceback
sys.path.insert(0, '.')
os.environ['JARVIS_PERMISSION_MODE'] = 'allow_all'
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

passed = 0
failed = 0
errors = []

def test(name, func):
    global passed, failed
    try:
        func()
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        errors.append((name, traceback.format_exc()))
        failed += 1

print("=" * 60)
print("  JARVIS MK37 -- Deep Audit")
print("=" * 60)

# == 1. Permissions ==
print("\n>> Permissions")

def t_perm_allow_all():
    from permissions import PermissionMode, PermissionPolicy
    p = PermissionPolicy(mode=PermissionMode.ALLOW_ALL)
    for tool in ["keyboard_type","cursor_click","run_code","file_write",
                 "web_search","screen_find","focus_window","nmap_scan"]:
        assert p.check(tool) == True, f"{tool} should be allowed in ALLOW_ALL"
test("ALLOW_ALL permits all tools", t_perm_allow_all)

def t_perm_global_singleton():
    from permissions import PERMISSIONS, PermissionMode
    assert PERMISSIONS.mode == PermissionMode.ALLOW_ALL
test("Global PERMISSIONS is ALLOW_ALL", t_perm_global_singleton)

def t_perm_deny_list():
    from permissions import PermissionMode, PermissionPolicy
    p = PermissionPolicy(mode=PermissionMode.ALLOW_ALL, deny_names=frozenset({"evil_tool"}))
    assert p.check("evil_tool") == False
    assert p.check("web_search") == True
test("Deny list blocks tools even in ALLOW_ALL", t_perm_deny_list)

def t_perm_confirm_all_allows_safe():
    from permissions import PermissionMode, PermissionPolicy, ALWAYS_ALLOWED
    p = PermissionPolicy(mode=PermissionMode.CONFIRM_ALL)
    for tool in ALWAYS_ALLOWED:
        assert p.check(tool) == True, f"{tool} should be in ALWAYS_ALLOWED"
test("CONFIRM_ALL allows safe tools without prompt", t_perm_confirm_all_allows_safe)

# == 2. Skill Loader ==
print("\n>> Skill Loader")

def t_skill_parse_list_field():
    from skills.loader import _parse_list_field
    assert _parse_list_field("[a, b, c]") == ["a", "b", "c"]
    assert _parse_list_field("x, y") == ["x", "y"]
    assert _parse_list_field("[]") == []
    assert _parse_list_field("") == []
test("_parse_list_field", t_skill_parse_list_field)

def t_skill_substitute_named():
    from skills.loader import substitute_arguments
    r = substitute_arguments("Fix $FILE on $BRANCH", "main.py develop", ["file", "branch"])
    assert "main.py" in r and "develop" in r
    assert "$FILE" not in r and "$BRANCH" not in r
test("substitute_arguments with named args", t_skill_substitute_named)

def t_skill_substitute_missing():
    from skills.loader import substitute_arguments
    r = substitute_arguments("Fix $FILE on $BRANCH", "main.py", ["file", "branch"])
    assert "main.py" in r
    assert "$BRANCH" not in r
test("substitute_arguments missing arg = empty", t_skill_substitute_missing)

def t_skill_find_by_trigger():
    from skills import find_skill
    s = find_skill("/commit")
    assert s is not None and s.name == "commit"
    s2 = find_skill("/review")
    assert s2 is not None and s2.name == "review"
    s3 = find_skill("/nonexistent")
    assert s3 is None
test("find_skill by trigger", t_skill_find_by_trigger)

def t_skill_dedup():
    from skills import load_skills
    skills = load_skills()
    names = [s.name for s in skills]
    assert len(names) == len(set(names)), f"Duplicate skill names: {names}"
test("Skills deduplicated", t_skill_dedup)

def t_skill_all_10_skills():
    from skills import load_skills
    skills = load_skills()
    expected = {"commit","review","edit","pc_control","research",
                "editor_open","editor_goto","editor_insert","editor_replace","editor_terminal"}
    actual = {s.name for s in skills}
    missing = expected - actual
    assert not missing, f"Missing skills: {missing}"
test("All 10 built-in skills registered", t_skill_all_10_skills)

def t_skill_editor_triggers():
    from skills import find_skill
    for trigger in ["/editor-open", "/goto", "/editor-insert", "/find-replace", "/terminal"]:
        s = find_skill(trigger)
        assert s is not None, f"Missing skill for trigger {trigger}"
test("Editor skill triggers all resolve", t_skill_editor_triggers)

# == 3. Multi-Agent ==
print("\n>> Multi-Agent")

def t_agent_all_builtins():
    from multi_agent.subagent import load_agent_definitions
    defs = load_agent_definitions()
    for name in ["general-purpose", "coder", "reviewer", "researcher", "tester", "editor", "sysadmin", "devops"]:
        assert name in defs, f"Missing built-in agent: {name}"
        assert defs[name].source == "built-in"
test("All 8 built-in agent types", t_agent_all_builtins)

def t_agent_editor_tools():
    from multi_agent.subagent import get_agent_definition
    ed = get_agent_definition("editor")
    assert "keyboard_type" in ed.tools
    assert "file_read" in ed.tools
test("Editor agent has keyboard tools", t_agent_editor_tools)

def t_agent_md_parse():
    from multi_agent.subagent import _parse_agent_md
    from pathlib import Path
    import tempfile
    md = "---\ndescription: Test agent\nmodel: gpt-4\ntools: [web_search, run_code]\n---\nYou are a test agent.\n"
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write(md)
        f.flush()
        d = _parse_agent_md(Path(f.name), source="user")
    os.unlink(f.name)
    assert d.description == "Test agent"
    assert d.model == "gpt-4"
    assert d.tools == ["web_search", "run_code"]
    assert "test agent" in d.system_prompt.lower()
test("Agent .md parsing", t_agent_md_parse)

def t_subagent_depth_limit():
    from multi_agent.subagent import SubAgentManager
    mgr = SubAgentManager(max_depth=2)
    task = mgr.spawn(prompt="test", orchestrator=None, depth=5)
    assert task.status == "failed"
    assert "depth" in task.result.lower()
test("SubAgent depth limit", t_subagent_depth_limit)

# == 4. Persistent Memory ==
print("\n>> Persistent Memory")

def t_memory_roundtrip():
    from memory.persistent_store import MemoryEntry, save_memory, search_memory, delete_memory
    e = MemoryEntry(name="deep_audit_test", description="Test", type="user",
                    content="Deep audit content", created="2026-04-20")
    save_memory(e, scope="user")
    found = search_memory("deep audit")
    assert len(found) > 0 and found[0].name == "deep_audit_test"
    from memory.persistent_store import get_index_content
    idx = get_index_content("user")
    assert "deep_audit_test" in idx
    delete_memory("deep_audit_test", scope="user")
    assert len(search_memory("deep_audit_test")) == 0
test("Memory save->search->index->delete", t_memory_roundtrip)

def t_memory_conflict():
    from memory.persistent_store import MemoryEntry, save_memory, check_conflict, delete_memory
    e1 = MemoryEntry(name="conflict_test", description="v1", type="user",
                     content="Version 1", created="2026-04-20", confidence=0.9)
    save_memory(e1, scope="user")
    e2 = MemoryEntry(name="conflict_test", description="v2", type="user",
                     content="Version 2", created="2026-04-20", confidence=0.7)
    conflict = check_conflict(e2, scope="user")
    assert conflict is not None
    assert conflict["existing_confidence"] == 0.9
    delete_memory("conflict_test", scope="user")
test("Memory conflict detection", t_memory_conflict)

def t_memory_slugify():
    from memory.persistent_store import _slugify
    assert _slugify("Hello World!") == "hello_world"
    assert _slugify("test@#$%^&*") == "test"
    assert len(_slugify("a" * 100)) <= 60
test("Memory slugify", t_memory_slugify)

def t_memory_frontmatter_parse():
    from memory.persistent_store import parse_frontmatter
    meta, body = parse_frontmatter("---\nname: test\ntype: user\n---\nBody text")
    assert meta["name"] == "test" and meta["type"] == "user"
    assert body == "Body text"
    meta2, body2 = parse_frontmatter("Just plain text")
    assert meta2 == {} and body2 == "Just plain text"
test("Frontmatter parsing", t_memory_frontmatter_parse)

def t_memory_touch():
    from memory.persistent_store import MemoryEntry, save_memory, touch_last_used, delete_memory, parse_frontmatter
    from pathlib import Path
    from datetime import date
    e = MemoryEntry(name="touch_test", description="Test touch", type="user",
                    content="Touch content", created="2026-04-20")
    save_memory(e, scope="user")
    touch_last_used(e.file_path)
    text = Path(e.file_path).read_text(encoding="utf-8")
    meta, _ = parse_frontmatter(text)
    assert meta.get("last_used_at") == date.today().isoformat()
    delete_memory("touch_test", scope="user")
test("Memory touch_last_used", t_memory_touch)

# == 5. Memory Scan ==
print("\n>> Memory Scan")

def t_memory_scan_freshness():
    import time as _time
    from memory.memory_scan import memory_age_str, memory_freshness_text
    assert memory_age_str(_time.time()) == "today"
    assert memory_age_str(_time.time() - 86400) == "yesterday"
    assert "days" in memory_age_str(_time.time() - 86400 * 10)
    assert memory_freshness_text(_time.time()) == ""
    old = memory_freshness_text(_time.time() - 86400 * 5)
    assert "days old" in old.lower()
test("Memory freshness functions", t_memory_scan_freshness)

# == 6. Memory Context ==
print("\n>> Memory Context")

def t_memory_context_truncation():
    from memory.memory_context import truncate_index_content
    short = "line1\nline2"
    assert truncate_index_content(short) == short.strip()
    huge = "\n".join(f"line {i}" for i in range(300))
    result = truncate_index_content(huge)
    assert "WARNING" in result
test("Index truncation", t_memory_context_truncation)

def t_memory_context_builds():
    from memory.memory_context import get_memory_context
    ctx = get_memory_context(include_guidance=True)
    assert isinstance(ctx, str)
test("get_memory_context builds", t_memory_context_builds)

def t_find_relevant_memories():
    from memory.persistent_store import MemoryEntry, save_memory, delete_memory
    from memory.memory_context import find_relevant_memories
    import time as _t
    unique = f"relevance_xyzzy_{int(_t.time())}"
    e = MemoryEntry(name=unique, description="Python coding preferences xyzzy",
                    type="user", content="User prefers PEP8 xyzzy", created="2026-04-20")
    save_memory(e, scope="user")
    results = find_relevant_memories("xyzzy")
    assert len(results) > 0, f"Expected results for 'xyzzy', got 0"
    assert results[0]["name"] == unique
    assert "mtime_s" in results[0] and "freshness_text" in results[0]
    delete_memory(unique, scope="user")
test("find_relevant_memories", t_find_relevant_memories)

# == 7. Tool Registry ==
print("\n>> Tool Registry")

def t_registry_all_schemas_have_name():
    from tools.registry import TOOL_SCHEMAS
    for t in TOOL_SCHEMAS:
        assert "name" in t, f"Schema missing name: {t}"
        assert "description" in t, f"Schema {t['name']} missing description"
        assert "parameters" in t, f"Schema {t['name']} missing parameters"
test("All schemas have name+desc+params", t_registry_all_schemas_have_name)

def t_registry_tool_count():
    from tools.registry import TOOL_SCHEMAS
    count = len(TOOL_SCHEMAS)
    assert count >= 30, f"Expected 30+ tools, got {count}"
test("Tool count >= 30", t_registry_tool_count)

def t_registry_pc_actions_match():
    actions_used = [
        "move", "click", "double_click", "smart_type", "hotkey", "press",
        "screen_find", "screen_click", "copy", "paste", "focus_window",
        "screenshot", "scroll", "drag",
    ]
    import inspect
    from actions.computer_control import computer_control
    source = inspect.getsource(computer_control)
    for action in actions_used:
        assert f'"{action}"' in source or f"'{action}'" in source, \
            f"Action '{action}' not found in computer_control dispatch"
test("Registry PC actions match computer_control", t_registry_pc_actions_match)

def t_registry_parse_tool_call():
    from tools.registry import parse_tool_call
    n, a = parse_tool_call('```tool_call\n{"tool": "web_search", "args": {"query": "test"}}\n```')
    assert n == "web_search" and a["query"] == "test"
    n2, a2 = parse_tool_call("Hello world")
    assert n2 is None and a2 is None
    n3, a3 = parse_tool_call('Let me search.\n```tool_call\n{"tool": "file_read", "args": {"path": "x.py"}}\n```\n')
    assert n3 == "file_read" and a3["path"] == "x.py"
    n4, a4 = parse_tool_call('```tool_call\n{bad json}\n```')
    assert n4 is None
test("parse_tool_call edge cases", t_registry_parse_tool_call)

def t_registry_execute_unknown():
    from tools.registry import execute_tool
    r = execute_tool("nonexistent_tool", {})
    assert "Unknown tool" in r or "ERROR" in r
test("execute_tool unknown tool", t_registry_execute_unknown)

# == 8. Orchestrator ==
print("\n>> Orchestrator")

def t_orchestrator_mode_switch():
    from orchestrator import JarvisOrchestrator
    orch = JarvisOrchestrator.__new__(JarvisOrchestrator)
    orch.current_mode = "general"
    orch.router = None
    orch.working_memory = None
    orch.vector_memory = None
    orch._subagent_mgr = None
    result = orch._parse_mode("/mode coder")
    assert "CODER" in result
    assert orch.current_mode == "coder"
    result2 = orch._parse_mode("/mode invalid_mode_xyz")
    assert "Unknown" in result2
    result3 = orch._parse_mode("normal chat message")
    assert result3 is None
test("Mode switching", t_orchestrator_mode_switch)

def t_orchestrator_keyword_extraction():
    from orchestrator import JarvisOrchestrator
    orch = JarvisOrchestrator.__new__(JarvisOrchestrator)
    kw = orch._extract_keywords("write a python script to scan ports")
    assert "code" in kw and "security" in kw
    kw2 = orch._extract_keywords("search for information about AI")
    assert "search" in kw2
    kw3 = orch._extract_keywords("hello how are you")
    assert len(kw3) == 0
test("Keyword extraction", t_orchestrator_keyword_extraction)

def t_orchestrator_system_prompt():
    from orchestrator import JarvisOrchestrator
    orch = JarvisOrchestrator.__new__(JarvisOrchestrator)
    orch.current_mode = "general"
    orch.router = None
    orch.working_memory = None
    orch.vector_memory = None
    orch._subagent_mgr = None
    system = orch._build_system()
    assert "JARVIS MK37" in system
    assert "tool_call" in system
    assert "cursor_click" in system
    assert "spawn_agent" in system
    assert "memory_save" in system
test("System prompt has all tool blocks", t_orchestrator_system_prompt)

# == 9. Working Memory ==
print("\n>> Working Memory")

def t_working_memory_trim():
    from memory.working import WorkingMemory
    wm = WorkingMemory(max_tokens=100)
    for i in range(50):
        wm.add("user", "x" * 100)
    assert len(wm.history) < 50
    total_chars = sum(len(m["content"]) for m in wm.history)
    assert total_chars / 4 <= 100
test("WorkingMemory trimming", t_working_memory_trim)

# == 10. Consolidator ==
print("\n>> Consolidator")

def t_consolidator_short_session():
    from memory.consolidator import consolidate_session
    short = [{"role": "user", "content": "hi"}]
    assert consolidate_session(short, router=None) == []
test("Consolidator skips short sessions", t_consolidator_short_session)

def t_consolidator_no_router():
    from memory.consolidator import consolidate_session
    msgs = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
    assert consolidate_session(msgs, router=None) == []
test("Consolidator skips without router", t_consolidator_no_router)

# == 11. Router ==
print("\n>> Router")

def t_router_fallback():
    from router import AgentRouter, AgentProfile
    class MockBackend:
        def complete(self, messages, system): return "ok"
    r = AgentRouter({AgentProfile.GEMINI: MockBackend()})
    r.default = AgentProfile.GEMINI
    p = r.route(["code"])
    assert p == AgentProfile.GEMINI
test("Router fallback to default", t_router_fallback)

def t_router_run():
    from router import AgentRouter, AgentProfile
    class MockBackend:
        def complete(self, messages, system): return "test response"
    r = AgentRouter({AgentProfile.GEMINI: MockBackend()})
    result = r.run(AgentProfile.GEMINI, [{"role": "user", "content": "hi"}], "sys")
    assert result == "test response"
test("Router.run works", t_router_run)

def t_router_run_missing():
    from router import AgentRouter, AgentProfile
    r = AgentRouter({})
    try:
        r.run(AgentProfile.CLAUDE, [], "")
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "not available" in str(e).lower()
test("Router.run raises on missing backend", t_router_run_missing)

# == 12. Cross-module Integration ==
print("\n>> Cross-module Integration")

def t_skill_executor_inline():
    from skills import load_skills, execute_skill
    skill = None
    for s in load_skills():
        if s.name == "commit":
            skill = s
            break
    assert skill is not None
    class MockOrch:
        def chat(self, message):
            return f"executed: {message[:20]}"
    result = execute_skill(skill, "test commit", MockOrch())
    assert "executed" in result
    assert "Skill: commit" in result
test("Skill executor inline mode", t_skill_executor_inline)

def t_full_syntax_check():
    import py_compile
    py_compile.compile("main_mk37.py", doraise=True)
    py_compile.compile("orchestrator.py", doraise=True)
    py_compile.compile("router.py", doraise=True)
    py_compile.compile("permissions.py", doraise=True)
test("Key files syntax-valid", t_full_syntax_check)

def t_backend_complete_signature():
    """Verify all backends have the correct complete(messages, system) signature."""
    import inspect
    for mod_name, cls_name in [
        ("anthropic_backend", "ClaudeBackend"),
        ("openai_backend", "OpenAIBackend"),
        ("gemini_backend", "GeminiBackend"),
        ("ollama_backend", "OllamaBackend"),
        ("nvidia_backend", "NvidiaBackend"),
        ("mistral_backend", "MistralBackend"),
    ]:
        mod = __import__(mod_name)
        cls = getattr(mod, cls_name)
        sig = inspect.signature(cls.complete)
        params = list(sig.parameters.keys())
        assert "messages" in params, f"{cls_name}.complete missing 'messages' param"
        assert "system" in params, f"{cls_name}.complete missing 'system' param"
test("All backends have complete(messages, system)", t_backend_complete_signature)

def t_redteam_scope_enforcer():
    from redteam.scope import ScopeEnforcer
    se = ScopeEnforcer("current_scope.json")
    # IPs from current_scope.json: 192.168.100.0/24 and 10.10.20.0/28
    assert se.is_authorized("192.168.100.50") == True, "192.168.100.50 should be in scope"
    assert se.is_authorized("10.10.20.5") == True, "10.10.20.5 should be in scope"
    # Domains from scope: test.acmecorp.internal, staging.acmecorp.com
    assert se.is_authorized("test.acmecorp.internal") == True
    assert se.is_authorized("staging.acmecorp.com") == True
    # Out of scope
    assert se.is_authorized("evil.com") == False
    assert se.is_authorized("8.8.8.8") == False
test("ScopeEnforcer auth checks", t_redteam_scope_enforcer)

# == Summary ==
print("\n" + "=" * 60)
print(f"  Results: {passed} passed, {failed} failed")
print("=" * 60)

if errors:
    print("\nFailed test details:")
    for name, tb in errors:
        print(f"\n--- {name} ---")
        print(tb)

sys.exit(1 if failed else 0)
