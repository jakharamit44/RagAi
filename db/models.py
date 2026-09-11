import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class GUID(TypeDecorator):
    """
    Platform-independent GUID/UUID type.
    Uses PostgreSQL's native UUID type in production, CHAR(36) in SQLite development.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value


class WatchedFolder(Base):
    """
    Registered folders watched by ingestion pipeline.
    Reference: Appendix A (Table 12) & Phase 1, 10
    """
    __tablename__ = "watched_folders"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    path = Column(Text, unique=True, nullable=False)
    department = Column(Text, nullable=True)
    semester = Column(Text, nullable=True)
    course = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ManifestEntry(Base):
    """
    Change detection and reconciliation tracking for folder watcher.
    Reference: Appendix A (Table 13) & Phase 1
    """
    __tablename__ = "manifest_entries"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    path = Column(Text, unique=True, nullable=False)
    content_hash = Column(Text, nullable=False, index=True)  # SHA-256
    mtime = Column(Float, nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending / processing / done / failed
    error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_manifest_status_updated", "status", "updated_at"),
    )


class Document(Base):
    """
    Successfully ingested university document metadata.
    Reference: Appendix A (Table 14) & Phase 1, 2
    """
    __tablename__ = "documents"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    source_path = Column(Text, nullable=False)
    title = Column(Text, nullable=False, index=True)
    department = Column(Text, nullable=True, index=True)
    semester = Column(Text, nullable=True, index=True)
    course = Column(Text, nullable=True, index=True)
    doc_type = Column(String(50), nullable=False, index=True)  # born_digital / scanned / handwritten
    ocr_confidence = Column(Float, nullable=True)   # 0.0 - 1.0 (null for born-digital)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_dept_course", "department", "course"),
        Index("ix_documents_created_at", "created_at"),
    )


class Chunk(Base):
    """
    The retrievable passage unit with vector pointers and source locations.
    Reference: Appendix A (Table 15) & Phase 2, 3, 4
    """
    __tablename__ = "chunks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID(), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=True)
    section = Column(Text, nullable=True)
    text = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False, index=True)  # SHA-256 for dedup
    embedding_ref = Column(String(255), nullable=True)      # Vector DB ID

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_doc_page", "document_id", "page_number"),
    )


class User(Base):
    """
    Local mirror of university SSO identity with RBAC roles.
    Reference: Appendix A (Table 16) & Phase 11
    """
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    external_id = Column(Text, unique=True, nullable=False)  # SSO subject ID
    role = Column(String(50), nullable=False)                # student / faculty / admin
    department = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class QueryAuditLog(Base):
    """
    Content-free query audit trail for security, latency & abuse monitoring.
    Reference: Appendix A (Table 17) & Phase 19
    """
    __tablename__ = "query_audit_log"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    question_hash = Column(String(64), nullable=False)       # SHA-256 of question (privacy-safe)
    served_by = Column(String(50), nullable=False)           # local / hosted / fallback / cache
    latency_ms = Column(Float, nullable=False)
    tokens_used = Column(Integer, default=0, nullable=False)
    crag_decision = Column(String(30), nullable=True)
    confidence = Column(Float, nullable=True)


class ApiKey(Base):
    """
    Multi-tenant API keys with role delegation, department scoping, and SHA-256 hashed storage.
    Supports enable/disable toggle, revocation, and per-key rate limits.
    """
    __tablename__ = "api_keys"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    key_prefix = Column(String(20), nullable=False, index=True)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    role = Column(String(50), default="student", nullable=False)
    department = Column(Text, nullable=True)
    rate_limit = Column(Integer, default=60, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class UrlGovernanceRule(Base):
    """
    External source and web URL governance for academic RAG ingestion.
    Supports allowlist and disallowlist rules with wildcard / prefix matching.
    """
    __tablename__ = "url_governance_rules"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    url_pattern = Column(Text, nullable=False)
    action = Column(String(20), default="allow", nullable=False)  # allow / disallow
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SystemSetting(Base):
    """
    Dynamic system configuration managed from Admin Portal.
    Stored in database so admin configuration never modifies or pollutes .env.
    """
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SecurityIncident(Base):
    """
    Audit log for security incidents, unauthorized access, rate limiting violations,
    and adversarial prompt injection attempts.
    """
    __tablename__ = "security_incidents"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    event_type = Column(String(50), nullable=False)  # AUTH_FAILURE, RATE_LIMIT_EXCEEDED, FORBIDDEN_ACCESS, PROMPT_INJECTION, POLICY_VIOLATION
    severity = Column(String(20), default="MEDIUM", nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    client_ip = Column(String(100), nullable=True)
    user_identifier = Column(String(100), nullable=True)  # apikey:name, user_id, or anonymous
    endpoint = Column(String(255), nullable=True)
    detail = Column(Text, nullable=True)
    action_taken = Column(String(50), default="BLOCKED", nullable=False)  # BLOCKED, RATE_LIMITED, FLAGGED, LOGGED


class PromptOptimizationRun(Base):
    """
    Tracks autonomous self-improvement optimization runs (Karpathy loop).
    Records baseline scores, mutations applied, validation outcomes, and rollback states.
    """
    __tablename__ = "prompt_optimization_runs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    baseline_score = Column(Float, nullable=False)
    new_score = Column(Float, nullable=False)
    mutation_strategy = Column(String(50), nullable=False)  # add_constraint, add_example, refine_rule
    mutation_applied = Column(Text, nullable=False)
    status = Column(String(30), nullable=False)            # ACCEPTED / ROLLED_BACK
    diagnostics = Column(Text, nullable=True)


class WebScrapeJob(Base):
    """
    Configuration and tracking for automated web scraping and delta ingestion jobs.
    """
    __tablename__ = "web_scrape_jobs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False, default="MDU Main Scraper")
    base_url = Column(Text, nullable=False, default="https://mdu.ac.in")
    seed_urls = Column(Text, nullable=False, default='["https://mdu.ac.in/default.aspx"]')  # JSON list
    allowed_domains = Column(Text, nullable=False, default="mdu.ac.in")
    url_patterns = Column(Text, nullable=True)  # Comma-separated or regex
    max_depth = Column(Integer, default=3, nullable=False)
    max_pages = Column(Integer, default=500, nullable=False)
    crawl_interval_minutes = Column(Integer, default=360, nullable=False)  # Every 6 hours
    auto_ingest = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default="idle", nullable=False)  # idle / running / paused / completed / failed
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    stats = Column(Text, nullable=True)  # JSON summary of last crawl
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    manifest_entries = relationship("WebScrapeManifest", back_populates="job", cascade="all, delete-orphan")


class WebScrapeManifest(Base):
    """
    Tracks all crawled URLs, documents, headers (ETag, Last-Modified), SHA-256 hashes,
    and ingestion statuses for continuous delta change detection.
    """
    __tablename__ = "web_scrape_manifest"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID(), ForeignKey("web_scrape_jobs.id", ondelete="CASCADE"), nullable=True)
    url = Column(Text, nullable=False, index=True)
    url_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 of normalized URL
    content_type = Column(String(100), default="text/html", nullable=False)
    etag = Column(String(255), nullable=True)
    last_modified_header = Column(String(255), nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)  # SHA-256 of content
    http_status = Column(Integer, nullable=True)
    title = Column(Text, nullable=True)
    local_file_path = Column(Text, nullable=True)
    document_id = Column(GUID(), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="discovered", nullable=False, index=True)  # discovered, downloaded, ingested, skipped_unchanged, failed
    error_message = Column(Text, nullable=True)
    last_checked_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("WebScrapeJob", back_populates="manifest_entries")
    document = relationship("Document")

    __table_args__ = (
        Index("ix_manifest_job_status", "job_id", "status"),
        Index("ix_manifest_url_hash", "url_hash"),
    )


class ContextTier(Base):
    """
    OpenViking-inspired Hierarchical Virtual Context Filesystem and Tiered Storage.
    Maintains progressive context tiers:
      - L0: Dense 1-sentence abstract (~50-100 tokens)
      - L1: Structured curricular/document synopsis (~500-1500 tokens)
      - L2: Metadata pointer to raw text chunks in the database and Qdrant.
    Addresses resources uniformly using the `ragai://` URI protocol.
    """
    __tablename__ = "context_tiers"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    uri = Column(String(255), unique=True, nullable=False, index=True)
    tier_type = Column(String(50), nullable=False, index=True)  # root, department, course, document, concept
    department = Column(String(100), nullable=True, index=True)
    course = Column(String(100), nullable=True, index=True)
    title = Column(Text, nullable=False)
    document_id = Column(GUID(), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)

    # Tiered Content
    l0_abstract = Column(Text, nullable=False)
    l1_overview = Column(Text, nullable=False)
    l2_chunk_count = Column(Integer, default=0, nullable=False)
    token_count_l0 = Column(Integer, default=0, nullable=False)
    token_count_l1 = Column(Integer, default=0, nullable=False)

    # Metadata for navigation
    metadata_json = Column(Text, nullable=True)  # e.g. parent_uri, keywords, topics
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    document = relationship("Document")

    __table_args__ = (
        Index("ix_context_dept_course", "department", "course"),
        Index("ix_context_tier_type", "tier_type"),
    )
