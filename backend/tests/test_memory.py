import pytest
import os
import shutil
import tempfile
from app.memory.memory_models import MemoryCategory, MemoryCreate, MemoryUpdate, ProjectCreate
from app.memory.long_term_memory import LongTermMemoryDB
from app.memory.semantic_search import SemanticSearchEngine
from app.memory.project_memory import ProjectMemoryManager
from app.memory.memory_extractor import MemoryExtractor
from app.memory.conversation_summarizer import ConversationSummarizer
from app.memory.memory_manager import MemoryManager

@pytest.fixture
def temp_memory_db():
    """Create a clean isolated SQLite database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_nova_memory.db")
    db = LongTermMemoryDB(db_path=db_path)
    yield db
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_memory_crud(temp_memory_db):
    """Test creating, reading, updating, and deleting memories."""
    # 1. Create
    created = temp_memory_db.create_memory(
        MemoryCreate(
            category=MemoryCategory.USER_PROFILE,
            content="User prefers concise answers with code snippets.",
            importance=2.0,
            tags=["preference", "style"]
        )
    )
    assert created.id is not None
    assert created.category == MemoryCategory.USER_PROFILE
    assert "code snippets" in created.content

    # 2. Read
    fetched = temp_memory_db.get_memory(created.id)
    assert fetched is not None
    assert fetched.content == created.content

    # 3. Update
    updated = temp_memory_db.update_memory(
        memory_id=created.id,
        update_data=MemoryUpdate(
            content="User prefers ultra-concise answers with TypeScript snippets.",
            tags=["preference", "typescript"]
        )
    )
    assert updated is not None
    assert "TypeScript" in updated.content
    assert "typescript" in updated.tags

    # 4. List
    all_mems = temp_memory_db.list_memories()
    # At least 1 memory (the one created plus seeds if any)
    assert len(all_mems) >= 1

    # 5. Delete
    deleted = temp_memory_db.delete_memory(created.id)
    assert deleted is True
    assert temp_memory_db.get_memory(created.id) is None

def test_project_crud_and_isolation(temp_memory_db):
    """Test project memory creation, decisions, and strict isolation."""
    pm = ProjectMemoryManager(db=temp_memory_db)

    # Create Project Alpha
    proj_alpha = pm.create_project(
        ProjectCreate(
            id="alpha",
            name="Project Alpha",
            description="A stealth robotics system",
            tech_stack=["ROS2", "Python", "C++"],
            status="active"
        )
    )
    assert proj_alpha.id == "alpha"
    assert "ROS2" in proj_alpha.tech_stack

    # Create Project Beta
    proj_beta = pm.create_project(
        ProjectCreate(
            id="beta",
            name="Project Beta",
            description="Cloud e-commerce backend",
            tech_stack=["FastAPI", "PostgreSQL"],
            status="planning"
        )
    )
    assert proj_beta.id == "beta"

    # Add memories specifically tagged to Alpha
    temp_memory_db.create_memory(
        MemoryCreate(
            category=MemoryCategory.PROJECT_MEMORY,
            content="Alpha uses lidar sensor model Velodyne VLP-16.",
            project_id="alpha"
        )
    )

    # Add memories specifically tagged to Beta
    temp_memory_db.create_memory(
        MemoryCreate(
            category=MemoryCategory.PROJECT_MEMORY,
            content="Beta relies on Stripe for payment processing.",
            project_id="beta"
        )
    )

    # Verify project isolation
    alpha_mems = temp_memory_db.list_memories(project_id="alpha")
    beta_mems = temp_memory_db.list_memories(project_id="beta")

    assert len(alpha_mems) == 1
    assert "Velodyne" in alpha_mems[0].content
    assert "Stripe" not in alpha_mems[0].content

    assert len(beta_mems) == 1
    assert "Stripe" in beta_mems[0].content
    assert "Velodyne" not in beta_mems[0].content

    # Check project context string generation
    context_str = pm.get_project_context_string("alpha")
    assert "project alpha" in context_str.lower()
    assert "ros2" in context_str.lower()
    assert "stripe" not in context_str.lower()

def test_sensitive_info_filtering():
    """Verify that sensitive information (API keys, passwords) is strictly redacted."""
    extractor = MemoryExtractor()

    # Leaked OpenAI key
    dangerous_text = "Here is my secret OpenAI API key: sk-proj-1234567890abcdef1234567890abcdef12345678"
    extracted = extractor.extract_from_text(dangerous_text)
    for item in extracted:
        assert "sk-proj" not in item.content
        assert "[REDACTED_API_KEY]" in item.content or "API key" not in item.content

    # Leaked GitHub token
    dangerous_gh = "Save my token ghp_1234567890abcdefghijklmnopqrstuvwxyz12"
    extracted_gh = extractor.extract_from_text(dangerous_gh)
    for item in extracted_gh:
        assert "ghp_" not in item.content

def test_explicit_memory_directives():
    """Test explicit commands like 'Remember that...', 'Forget...'."""
    extractor = MemoryExtractor()

    # Explicit remember
    res1 = extractor.extract_from_text("Remember that my favorite programming language is Rust.")
    assert len(res1) >= 1
    assert any("Rust" in m.content for m in res1)

    # Explicit directive parsing
    parsed = extractor.parse_explicit_directive("Forget the HireLens database config")
    assert parsed is not None
    assert parsed["action"] == "forget"
    assert "HireLens" in parsed["target"]

def test_semantic_search_and_fallback():
    """Verify semantic retrieval and keyword/TF-IDF fallback."""
    search_engine = SemanticSearchEngine()

    corpus = [
        "NOVA uses FastAPI for high performance asynchronous REST endpoints.",
        "The desktop application is built with Tauri and React TypeScript.",
        "Vosk provides offline speech recognition without requiring internet access.",
        "Piper neural text to speech produces ultra natural voice responses."
    ]

    # Query matching semantic meaning
    results = search_engine.search(
        query="What framework powers the desktop UI?",
        candidate_texts=corpus,
        top_k=2
    )

    assert len(results) > 0
    top_result_idx, top_score = results[0]
    # The Tauri / React entry should rank first
    assert "Tauri" in corpus[top_result_idx]
    assert top_score > 0.1

@pytest.mark.asyncio
async def test_conversation_summarizer():
    """Test conversation summarization logic."""
    summarizer = ConversationSummarizer()

    turns = [
        {"role": "user", "content": "How do we implement offline vector search in NOVA?"},
        {"role": "assistant", "content": "We should use FastEmbed with BGE-small-en-v1.5 running on ONNX Runtime."},
        {"role": "user", "content": "That sounds great because it avoids the 2GB PyTorch download on Intel i3."}
    ]

    summary_text = await summarizer.summarize_session(turns, session_id="test-sess")
    assert summary_text is not None
    assert len(summary_text) > 0
    assert "test-sess" in summary_text or "vector" in summary_text.lower() or "nova" in summary_text.lower()

def test_memory_manager_context_injection(temp_memory_db):
    """Test MemoryManager end-to-end context injection."""
    mm = MemoryManager(db=temp_memory_db)

    # Store a memory
    temp_memory_db.create_memory(
        MemoryCreate(
            category=MemoryCategory.PROJECT_MEMORY,
            content="NOVA persistent memory uses SQLite with FastEmbed ONNX.",
            project_id="nova"
        )
    )

    # Request augmented context block
    context, proj_id = mm.build_augmented_context("Tell me about NOVA memory architecture", session_id="test")
    assert "FastEmbed" in context or "NOVA" in context
    assert proj_id == "nova"
