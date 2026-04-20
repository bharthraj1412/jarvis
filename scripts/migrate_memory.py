# scripts/migrate_memory.py
"""
Migration script: seed ChromaDB vector store from existing JSON/file memory.

Reads all .md memory files from ~/.jarvis/memory/ and indexes them into
the ChromaDB persistent store for semantic similarity search.

Usage:
    python scripts/migrate_memory.py
    python scripts/migrate_memory.py --dry-run    # preview only

Rollback:
    Delete ~/.jarvis/memory/.chromadb/ directory to revert to keyword-only search.
    The JSON/file store is never modified — this is purely additive.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def migrate(dry_run: bool = False):
    from memory.persistent_store import (
        load_entries, _sync_to_vector, _get_chroma_collection, _chroma_available,
        USER_MEMORY_DIR
    )

    print("=" * 55)
    print("  JARVIS MK37 — Memory Migration to ChromaDB")
    print("=" * 55)

    if not _chroma_available:
        print("\n[ERROR] ChromaDB is not installed.")
        print("        Run: pip install chromadb")
        print("        The system will continue using keyword search until installed.")
        return

    # Load all existing entries
    user_entries = load_entries("user")
    project_entries = load_entries("project")
    all_entries = user_entries + project_entries

    print(f"\n  Found {len(user_entries)} user memories")
    print(f"  Found {len(project_entries)} project memories")
    print(f"  Total: {len(all_entries)}")

    if not all_entries:
        print("\n  No memories to migrate.")
        return

    if dry_run:
        print("\n  [DRY RUN] Would index the following memories:")
        for e in all_entries:
            print(f"    - [{e.type}] {e.name}: {e.description[:60]}")
        print("\n  Run without --dry-run to execute.")
        return

    # Index into ChromaDB
    coll = _get_chroma_collection()
    if coll is None:
        print("\n[ERROR] Could not create ChromaDB collection.")
        return

    indexed = 0
    for entry in all_entries:
        try:
            _sync_to_vector(entry)
            indexed += 1
            print(f"  ✓ {entry.name}")
        except Exception as e:
            print(f"  ✗ {entry.name}: {e}")

    print(f"\n  Indexed: {indexed}/{len(all_entries)} memories")
    print(f"  ChromaDB path: {USER_MEMORY_DIR / '.chromadb'}")
    print(f"\n  Migration complete. Vector search is now active.")
    print(f"\n  Rollback: delete {USER_MEMORY_DIR / '.chromadb'} to revert to keyword-only.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    migrate(dry_run=dry)
