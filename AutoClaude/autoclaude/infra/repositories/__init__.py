"""autoclaude.infra.repositories — DAL 後端實作（Phase 5）。

  - File* 後端：薄包裝既有 CheckpointManager / FailureKnowledgeBase / yaml IO
  - InMemory* 後端：純 dict / list 包裝，供測試與 Kernel 單元測試
  - PG* 後端：Phase 6 選配（待業務需求觸發）
"""
from .file_state_repository import FileStateRepository
from .in_memory_state_repository import InMemoryStateRepository
from .file_memory_store import FileMemoryStore
from .in_memory_memory_store import InMemoryMemoryStore
from .file_playbook_repository import FilePlaybookRepository
from .in_memory_playbook_repository import InMemoryPlaybookRepository
from .dual_state_repository import DualStateRepository
from .factory import build_state_repository, canonical_playbook_id

__all__ = [
    "FileStateRepository", "InMemoryStateRepository",
    "FileMemoryStore", "InMemoryMemoryStore",
    "FilePlaybookRepository", "InMemoryPlaybookRepository",
    "DualStateRepository",
    "build_state_repository",
    "canonical_playbook_id",
]
