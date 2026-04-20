"""JARVIS MK37 — Full Integration Test Suite."""
import sys, os
sys.path.insert(0, '.')
os.environ['JARVIS_PERMISSION_MODE'] = 'allow_all'

print('=== JARVIS MK37 Integration Test ===')
print()

# 1. Permissions
from permissions import PERMISSIONS, PermissionMode
assert PERMISSIONS.mode == PermissionMode.ALLOW_ALL
assert PERMISSIONS.check('keyboard_type') == True
assert PERMISSIONS.check('cursor_click') == True
assert PERMISSIONS.check('run_code') == True
print('[PASS] 1. Permissions: auto-allow mode working')

# 2. Skills
from skills import load_skills, find_skill, SkillDef
from skills.builtin_editor import _EDITOR_OPEN_PROMPT
skills = load_skills()
assert len(skills) >= 10, f'Expected 10 skills, got {len(skills)}'
commit_skill = find_skill('/commit')
assert commit_skill is not None
assert commit_skill.name == 'commit'
edit_skill = find_skill('/edit')
assert edit_skill is not None
pc_skill = find_skill('/pc')
assert pc_skill is not None
editor_skill = find_skill('/editor-open')
assert editor_skill is not None
print(f'[PASS] 2. Skills: {len(skills)} skills loaded, triggers work')

# 3. Skill argument substitution
from skills.loader import substitute_arguments
result = substitute_arguments('Hello $ARGUMENTS world', 'test_arg', [])
assert 'test_arg' in result
print('[PASS] 3. Skill argument substitution works')

# 4. Multi-Agent
from multi_agent import (
    AgentDefinition, SubAgentTask, SubAgentManager,
    load_agent_definitions, get_agent_definition
)
defs = load_agent_definitions()
assert len(defs) >= 6, f'Expected 6+ agent types, got {len(defs)}'
assert 'coder' in defs
assert 'reviewer' in defs
assert 'editor' in defs
coder = get_agent_definition('coder')
assert coder is not None
assert coder.source == 'built-in'
print(f'[PASS] 4. Multi-Agent: {len(defs)} agent types (coder, reviewer, editor, etc)')

# 5. Persistent Memory
from memory.persistent_store import (
    MemoryEntry, save_memory, search_memory, delete_memory, load_entries
)
test_entry = MemoryEntry(
    name='test_integration',
    description='Integration test memory',
    type='user',
    content='This is a test memory for integration testing.',
    created='2026-04-20',
)
save_memory(test_entry, scope='user')
results = search_memory('integration test')
assert len(results) > 0
assert results[0].name == 'test_integration'
delete_memory('test_integration', scope='user')
results2 = search_memory('integration test')
assert len(results2) == 0
print('[PASS] 5. Persistent Memory: save/search/delete cycle works')

# 6. Memory Scan
from memory.memory_scan import scan_all_memories, memory_age_str, memory_freshness_text
age = memory_age_str(0)
assert 'days' in age or 'today' in age
print('[PASS] 6. Memory Scan: age/freshness functions work')

# 7. Memory Context
from memory.memory_context import get_memory_context, truncate_index_content
ctx = get_memory_context()  # may be empty, that's OK
print('[PASS] 7. Memory Context: builds without error')

# 8. Tool Registry
from tools.registry import TOOL_SCHEMAS, get_tool_prompt_block, parse_tool_call
assert len(TOOL_SCHEMAS) >= 37, f'Expected 37+ tools, got {len(TOOL_SCHEMAS)}'
prompt_block = get_tool_prompt_block()
assert 'AUTO-ALLOW' in prompt_block
assert 'cursor_click' in prompt_block
assert 'spawn_agent' in prompt_block
assert 'memory_save' in prompt_block

# Test parse_tool_call
test_block = '```tool_call\n{"tool": "web_search", "args": {"query": "test"}}\n```'
name, args = parse_tool_call(test_block)
assert name == 'web_search'
assert args['query'] == 'test'
name2, args2 = parse_tool_call('No tool call here')
assert name2 is None
print(f'[PASS] 8. Tool Registry: {len(TOOL_SCHEMAS)} tools, prompt block, parser all OK')

# 9. Orchestrator
from orchestrator import JarvisOrchestrator, MAX_REACT_STEPS
assert MAX_REACT_STEPS == 15
print('[PASS] 9. Orchestrator: MAX_REACT_STEPS=15, imports clean')

# 10. Memory Types
from memory.memory_types import MEMORY_SYSTEM_PROMPT, MEMORY_TYPES
assert len(MEMORY_TYPES) == 4
print('[PASS] 10. Memory Types: 4 types defined')

# 11. Consolidator
from memory.consolidator import consolidate_session, MIN_MESSAGES_TO_CONSOLIDATE
assert MIN_MESSAGES_TO_CONSOLIDATE == 8
print('[PASS] 11. Consolidator: ready (min 8 messages)')

print()
print('=== ALL 11 TESTS PASSED ===')
print(f'Summary: 37 tools | 10 skills | {len(defs)} agent types | auto-allow permissions')
