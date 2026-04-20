# memory/persistent_store.py
"""
File-based persistent memory storage with user-level and project-level scopes.
Ported from the Claude Code collection for JARVIS MK37.

Storage layout:
  user scope    : ~/.jarvis/memory/<slug>.md
  project scope : .jarvis/memory/<slug>.md  (relative to cwd)

MEMORY.md in each directory is the index file — rebuilt automatically after
every save/delete.

Optional ChromaDB vector embeddings for semantic similarity search.
Falls back to keyword search if chromadb is not installed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


# ── Paths ──────────────────────────────────────────────────────────────────

USER_MEMORY_DIR = Path.home() / ".jarvis" / "memory"
INDEX_FILENAME = "MEMORY.md"

MAX_INDEX_LINES = 200
MAX_INDEX_BYTES = 25_000


def get_project_memory_dir() -> Path:
    """Return the project-local memory directory (relative to cwd)."""
    return Path.cwd() / ".jarvis" / "memory"


def get_memory_dir(scope: str = "user") -> Path:
    """Return the memory directory for the given scope."""
    if scope == "project":
        return get_project_memory_dir()
    return USER_MEMORY_DIR


# ── Data model ─────────────────────────────────────────────────────────────

@dataclass
class MemoryEntry:
    """A single memory entry loaded from a .md file."""
    name: str
    description: str
    type: str                   # "user" | "feedback" | "project" | "reference"
    content: str
    file_path: str = ""
    created: str = ""
    scope: str = "user"
    confidence: float = 1.0     # 0.0–1.0; 1.0 = explicit user statement
    source: str = "user"        # "user" | "model" | "tool" | "consolidator"
    last_used_at: str = ""
    conflict_group: str = ""


# ── Helpers ────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """Convert name to a filesystem-safe slug (max 60 chars)."""
    s = name.lower().strip().replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s[:60]


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse ---\\nkey: value\\n---\\nbody format."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    return meta, parts[2].strip()


def _format_entry_md(entry: MemoryEntry) -> str:
    """Render a MemoryEntry as a markdown file with YAML frontmatter."""
    lines = [
        "---",
        f"name: {entry.name}",
        f"description: {entry.description}",
        f"type: {entry.type}",
        f"created: {entry.created}",
    ]
    if entry.confidence != 1.0:
        lines.append(f"confidence: {entry.confidence:.2f}")
    if entry.source and entry.source != "user":
        lines.append(f"source: {entry.source}")
    if entry.last_used_at:
        lines.append(f"last_used_at: {entry.last_used_at}")
    if entry.conflict_group:
        lines.append(f"conflict_group: {entry.conflict_group}")
    lines.append("---")
    lines.append(entry.content)
    return "\n".join(lines) + "\n"


# ── Core storage operations ────────────────────────────────────────────────

def save_memory(entry: MemoryEntry, scope: str = "user") -> None:
    """Write/update a memory file and rebuild the index for that scope."""
    mem_dir = get_memory_dir(scope)
    mem_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(entry.name)
    fp = mem_dir / f"{slug}.md"
    fp.write_text(_format_entry_md(entry), encoding="utf-8")
    entry.file_path = str(fp)
    entry.scope = scope
    _rewrite_index(scope)
    _sync_to_vector(entry)


def delete_memory(name: str, scope: str = "user") -> None:
    """Remove the memory file matching name and rebuild the index."""
    mem_dir = get_memory_dir(scope)
    slug = _slugify(name)
    fp = mem_dir / f"{slug}.md"
    if fp.exists():
        fp.unlink()
    _rewrite_index(scope)
    _remove_from_vector(name)


def load_entries(scope: str = "user") -> list[MemoryEntry]:
    """Scan all .md files (except MEMORY.md) in a scope and return entries."""
    mem_dir = get_memory_dir(scope)
    if not mem_dir.exists():
        return []
    entries: list[MemoryEntry] = []
    for fp in sorted(mem_dir.glob("*.md")):
        if fp.name == INDEX_FILENAME:
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except Exception:
            continue
        meta, body = parse_frontmatter(text)
        entries.append(MemoryEntry(
            name=meta.get("name", fp.stem),
            description=meta.get("description", ""),
            type=meta.get("type", "user"),
            content=body,
            file_path=str(fp),
            created=meta.get("created", ""),
            scope=scope,
            confidence=float(meta.get("confidence", 1.0)),
            source=meta.get("source", "user"),
            last_used_at=meta.get("last_used_at", ""),
            conflict_group=meta.get("conflict_group", ""),
        ))
    return entries


def load_index(scope: str = "all") -> list[MemoryEntry]:
    """Load memory entries from one or both scopes."""
    if scope == "all":
        return load_entries("user") + load_entries("project")
    return load_entries(scope)


def search_memory(query: str, scope: str = "all") -> list[MemoryEntry]:
    """Search memories using vector similarity (if ChromaDB available) + keyword fallback."""
    all_entries = load_index(scope)
    if not all_entries:
        return []

    # Build a set of valid entry names from disk (ground truth)
    valid_names = {e.name for e in all_entries}

    # Attempt vector search first
    vector_results = _vector_search(query, all_entries, top_k=10)
    # Filter vector results to only include entries that exist on disk
    vector_results = [e for e in vector_results if e.name in valid_names]
    if vector_results:
        return vector_results

    # Fallback: case-insensitive keyword match
    q = query.lower()
    results = []
    for entry in all_entries:
        haystack = f"{entry.name} {entry.description} {entry.content}".lower()
        if q in haystack:
            results.append(entry)
    return results


# ── Optional ChromaDB vector layer ─────────────────────────────────────────

_chroma_collection = None
_chroma_available = False

try:
    import chromadb
    _chroma_available = True
except ImportError:
    pass


def _get_chroma_collection():
    """Lazy-load ChromaDB collection."""
    global _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection
    if not _chroma_available:
        return None
    try:
        db_path = str(USER_MEMORY_DIR / ".chromadb")
        client = chromadb.PersistentClient(path=db_path)
        _chroma_collection = client.get_or_create_collection(
            name="jarvis_memory",
            metadata={"hnsw:space": "cosine"}
        )
        return _chroma_collection
    except Exception:
        return None


def _sync_to_vector(entry: MemoryEntry):
    """Add/update a memory entry in the vector store."""
    coll = _get_chroma_collection()
    if coll is None:
        return
    try:
        doc_text = f"{entry.name} {entry.description} {entry.content}"
        coll.upsert(
            ids=[_slugify(entry.name)],
            documents=[doc_text],
            metadatas=[{
                "name": entry.name,
                "type": entry.type,
                "scope": entry.scope,
                "source": entry.source,
                "confidence": str(entry.confidence),
            }]
        )
    except Exception:
        pass


def _remove_from_vector(name: str):
    """Remove a memory from the vector store."""
    coll = _get_chroma_collection()
    if coll is None:
        return
    try:
        coll.delete(ids=[_slugify(name)])
    except Exception:
        pass


def _vector_search(query: str, all_entries: list[MemoryEntry], top_k: int = 10) -> list[MemoryEntry]:
    """Search using ChromaDB vector similarity. Returns empty list if unavailable."""
    coll = _get_chroma_collection()
    if coll is None:
        return []
    try:
        count = coll.count()
        if count == 0:
            # Seed the vector store from existing entries
            for e in all_entries:
                _sync_to_vector(e)
            count = coll.count()
        if count == 0:
            return []
        results = coll.query(query_texts=[query], n_results=min(top_k, count))
        if not results or not results["ids"] or not results["ids"][0]:
            return []
        # Map vector results back to MemoryEntry objects
        matched_slugs = set(results["ids"][0])
        entry_map = {_slugify(e.name): e for e in all_entries}
        return [entry_map[slug] for slug in results["ids"][0] if slug in entry_map]
    except Exception:
        return []


def _rewrite_index(scope: str) -> None:
    """Rebuild MEMORY.md for the given scope from all .md files in that dir."""
    mem_dir = get_memory_dir(scope)
    if not mem_dir.exists():
        return
    index_path = mem_dir / INDEX_FILENAME
    entries = load_entries(scope)
    lines = [
        f"- [{e.name}]({Path(e.file_path).name}) — {e.description}"
        for e in entries
    ]
    index_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def get_index_content(scope: str = "user") -> str:
    """Return raw MEMORY.md content for the given scope, or '' if absent."""
    mem_dir = get_memory_dir(scope)
    index_path = mem_dir / INDEX_FILENAME
    if not index_path.exists():
        return ""
    return index_path.read_text(encoding="utf-8").strip()


def check_conflict(entry: MemoryEntry, scope: str = "user") -> dict | None:
    """Check whether a same-named memory already exists with different content."""
    mem_dir = get_memory_dir(scope)
    slug = _slugify(entry.name)
    fp = mem_dir / f"{slug}.md"
    if not fp.exists():
        return None
    try:
        meta, existing_content = parse_frontmatter(fp.read_text(encoding="utf-8"))
    except Exception:
        return None
    if existing_content.strip() == entry.content.strip():
        return None
    return {
        "existing_content": existing_content.strip(),
        "existing_confidence": float(meta.get("confidence", 1.0)),
        "existing_created": meta.get("created", ""),
        "existing_source": meta.get("source", "user"),
    }


def touch_last_used(file_path: str) -> None:
    """Update the last_used_at frontmatter field of a memory file to today."""
    from datetime import date
    fp = Path(file_path)
    if not fp.exists():
        return
    try:
        text = fp.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        today = date.today().isoformat()
        if meta.get("last_used_at") == today:
            return
        meta["last_used_at"] = today
        fm_lines = ["---"]
        for k in ("name", "description", "type", "created", "confidence",
                   "source", "last_used_at", "conflict_group"):
            v = meta.get(k)
            if v is not None and str(v):
                fm_lines.append(f"{k}: {v}")
        fm_lines.append("---")
        new_text = "\n".join(fm_lines) + "\n" + body + "\n"
        fp.write_text(new_text, encoding="utf-8")
    except Exception:
        pass
