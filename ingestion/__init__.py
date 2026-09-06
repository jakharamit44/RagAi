"""Ingestion Pipeline Package"""
from .folder_watcher import FolderWatcher
from .manifest import ManifestManager
from .path_tagger import PathTagger
from .format_detector import FormatDetector
from .chunker import SemanticChunker, chunker
from .dedup import ContentDeduplicator
from .extractors import DocumentExtractorRouter, PDFExtractor, DOCXExtractor, TextExtractor
from .pipeline import IngestionPipeline

__all__ = [
    "FolderWatcher",
    "ManifestManager",
    "PathTagger",
    "FormatDetector",
    "SemanticChunker",
    "chunker",
    "ContentDeduplicator",
    "DocumentExtractorRouter",
    "PDFExtractor",
    "DOCXExtractor",
    "TextExtractor",
    "IngestionPipeline",
]
