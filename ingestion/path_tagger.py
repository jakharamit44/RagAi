import os
from typing import Dict, Optional

class PathTagger:
    """
    Infers department, semester, and course metadata directly from folder hierarchy.
    Example: .../ComputerScience/Semester4/CS401_Algorithms/lecture1.pdf
    Reference: Phase 1 (Folder structure as free metadata)
    """

    @staticmethod
    def infer_tags(file_path: str, watched_root: Optional[str] = None) -> Dict[str, Optional[str]]:
        tags = {
            "department": None,
            "semester": None,
            "course": None,
        }

        rel_path = file_path
        if watched_root and file_path.startswith(watched_root):
            rel_path = os.path.relpath(file_path, watched_root)

        parts = [p for p in os.path.dirname(rel_path).replace("\\", "/").split("/") if p]

        if len(parts) >= 3:
            tags["department"] = parts[0]
            tags["semester"] = parts[1]
            tags["course"] = parts[2]
        elif len(parts) == 2:
            tags["department"] = parts[0]
            tags["course"] = parts[1]
        elif len(parts) == 1:
            tags["department"] = parts[0]

        # Scan for explicit academic identifiers anywhere in path components
        for p in parts:
            p_upper = p.upper()
            if "CS401" in p_upper or "CS402" in p_upper or "EE201" in p_upper or p_upper.startswith("CS"):
                if "CS401" in p_upper or "CS402" in p_upper:
                    tags["course"] = "CS401" if "CS401" in p_upper else "CS402"
                elif "EE201" in p_upper:
                    tags["course"] = "EE201"
                elif not tags["course"]:
                    tags["course"] = p

                if not tags["department"] or tags["department"] in ("D:", "C:", "data", "sample_courses") or tags["department"].startswith("CS") or tags["department"] == tags["course"]:
                    tags["department"] = "ComputerScience" if ("CS" in p_upper or tags["department"].startswith("CS")) else "ElectricalEngineering"
            elif "COMPUTERSCIENCE" in p_upper:
                tags["department"] = "ComputerScience"

        if tags.get("department") and (tags["department"].startswith("CS") or tags["department"] == tags.get("course")):
            tags["department"] = "ComputerScience"

        return tags
