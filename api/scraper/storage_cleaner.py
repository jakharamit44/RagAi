import os
import gc
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "downloads", "mdu_scraped"))
BASE_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
SAMPLE_COURSES_DIR = os.path.abspath(os.path.join(BASE_DATA_DIR, "sample_courses"))
UPLOADS_DIR = os.path.abspath(os.path.join(BASE_DATA_DIR, "uploads"))

class StorageCleaner:
    """
    Automated storage lifecycle manager.
    Safely prunes transient scraped downloads and temporary files
    while strictly protecting all course directory PDFs and knowledge assets.
    """

    @staticmethod
    def is_safe_scraper_temp_file(file_path: Optional[str]) -> bool:
        """
        Validates that file_path is strictly a temporary scraped file inside DOWNLOAD_DIR.
        GUARANTEES that no files in sample_courses, uploads, or other directories are ever deleted.
        """
        if not file_path or not isinstance(file_path, str):
            return False

        try:
            norm_target = os.path.abspath(os.path.normpath(file_path))
            norm_download_dir = os.path.abspath(os.path.normpath(DOWNLOAD_DIR))

            # 1. Target must reside strictly inside DOWNLOAD_DIR
            common = os.path.commonpath([norm_download_dir, norm_target])
            if common != norm_download_dir:
                logger.warning(f"Safety violation: {norm_target} is outside DOWNLOAD_DIR ({norm_download_dir}). Rejected.")
                return False

            # Cannot be the directory itself
            if norm_target == norm_download_dir:
                return False

            # 2. Strict blacklist against sample_courses and user directories
            protected_roots = [SAMPLE_COURSES_DIR, UPLOADS_DIR, os.path.abspath("data/sample_courses")]
            for p_root in protected_roots:
                if os.path.exists(p_root):
                    norm_p = os.path.abspath(os.path.normpath(p_root))
                    try:
                        if os.path.commonpath([norm_p, norm_target]) == norm_p:
                            logger.error(f"CRITICAL SAFETY ABORT: {norm_target} resides inside protected directory {norm_p}!")
                            return False
                    except ValueError:
                        pass

            return True
        except Exception as e:
            logger.error(f"Error validating file safety for {file_path}: {e}")
            return False

    @staticmethod
    def cleanup_file(file_path: Optional[str]) -> bool:
        """
        Safely removes a single temporary scraped file if and only if it passes the safety guard.
        """
        if not file_path:
            return False

        if not StorageCleaner.is_safe_scraper_temp_file(file_path):
            logger.warning(f"Blocked deletion of non-temp file: {file_path}")
            return False

        try:
            if os.path.exists(file_path):
                size_bytes = os.path.getsize(file_path)
                os.remove(file_path)
                logger.info(f"🧹 Cleaned up temporary scraped file: {os.path.basename(file_path)} ({size_bytes} bytes freed)")
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to remove scraped temp file {file_path}: {e}")
            return False

    @staticmethod
    def cleanup_scraped_downloads(purge_all_cached: bool = True) -> Dict[str, Any]:
        """
        Sweeps data/downloads/mdu_scraped/ for temporary .tmp files and ingested PDFs.
        Reports disk space reclaimed while ensuring zero directory course PDFs are touched.
        """
        bytes_freed = 0
        files_deleted = 0
        skipped_count = 0
        errors = []

        if not os.path.exists(DOWNLOAD_DIR):
            return {
                "status": "success",
                "bytes_freed": 0,
                "files_deleted": 0,
                "remaining_files": 0,
                "message": "Scraper download directory does not exist."
            }

        try:
            for entry in os.scandir(DOWNLOAD_DIR):
                if entry.is_file():
                    file_path = entry.path
                    if StorageCleaner.is_safe_scraper_temp_file(file_path):
                        # Always clean .tmp files
                        is_tmp = file_path.endswith(".tmp")
                        if is_tmp or purge_all_cached:
                            try:
                                f_size = entry.stat().st_size
                                os.remove(file_path)
                                bytes_freed += f_size
                                files_deleted += 1
                                logger.info(f"Purged scraped temp file: {entry.name} ({f_size} bytes)")
                            except Exception as del_err:
                                errors.append(f"Failed to remove {entry.name}: {del_err}")
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1
        except Exception as scan_err:
            logger.error(f"Error scanning download directory: {scan_err}")
            errors.append(str(scan_err))

        # Reclaim Python heap
        gc.collect()

        # Count remaining files in DOWNLOAD_DIR
        try:
            remaining = len([f for f in os.listdir(DOWNLOAD_DIR) if os.path.isfile(os.path.join(DOWNLOAD_DIR, f))])
        except Exception:
            remaining = 0

        mb_freed = round(bytes_freed / (1024 * 1024), 2)
        logger.info(f"Storage cleanup finished: {files_deleted} files deleted ({mb_freed} MB freed). {remaining} remaining.")

        return {
            "status": "success",
            "bytes_freed": bytes_freed,
            "mb_freed": mb_freed,
            "files_deleted": files_deleted,
            "remaining_files": remaining,
            "protected_dirs_intact": True,
            "errors": errors
        }
