import json
from pathlib import Path


class ProjectService:

    def __init__(self, load_config=True):
        self.project_root = None
        if not load_config:
            return

        config_path = Path(__file__).resolve().parents[2] / "project.json"

        try:
            configured_path = json.loads(config_path.read_text(encoding="utf-8"))["path"]
            if Path(configured_path).expanduser().is_dir():
                self.project_root = Path(configured_path).expanduser().resolve()
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            pass

    def set_project(self, path: str):
        project_root = Path(path).expanduser().resolve()

        if not project_root.is_dir():
            return {
                "success": False,
                "error": "Project path does not exist"
            }

        self.project_root = project_root

        return {
            "success": True,
            "path": str(project_root)
        }

    def get_project(self):
        return {
            "success": True,
            "path": str(self.project_root) if self.project_root else None
        }

    def get_tree(self):
        if self.project_root is None:
            return {
                "success": False,
                "error": "No project selected",
                "files": []
            }

        return {
            "success": True,
            "files": self._tree(self.project_root)
        }

    def read_file(self, path: str):
        if self._is_placeholder_path(path):
            return None
        file_path = self._project_path(path)

        if file_path is None or not file_path.is_file():
            return None

        try:
            return file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def write_file(self, path: str, content: str):
        if self._is_placeholder_path(path):
            return {
                "success": False,
                "error": "Use a real project-relative path, not a placeholder path"
            }
        file_path = self._project_path(path)

        if file_path is None:
            return {
                "success": False,
                "error": "Path is outside the selected project"
            }

        created = not file_path.exists()
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        except OSError as error:
            return {
                "success": False,
                "error": str(error)
            }

        return {
            "success": True,
            "path": str(file_path.relative_to(self.project_root)),
            "created": created
        }

    def delete_file(self, path: str):
        if self._is_placeholder_path(path):
            return {
                "success": False,
                "error": "Use a real project-relative path, not a placeholder path"
            }
        file_path = self._project_path(path)

        if file_path is None:
            return {
                "success": False,
                "error": "Path is outside the selected project"
            }

        if not file_path.is_file():
            return {
                "success": False,
                "error": "File does not exist"
            }

        try:
            file_path.unlink()
        except OSError as error:
            return {
                "success": False,
                "error": str(error)
            }

        return {
            "success": True,
            "path": str(file_path.relative_to(self.project_root))
        }

    def search(self, query: str):
        if self.project_root is None:
            return []

        results = []
        for file_path in self.project_root.rglob("*"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            for line_number, line in enumerate(content.splitlines(), start=1):
                if query.lower() in line.lower():
                    results.append({
                        "path": str(file_path.relative_to(self.project_root)),
                        "line": line_number,
                        "content": line
                    })

        return results

    def _project_path(self, path: str):
        if self.project_root is None:
            return None

        candidate = (self.project_root / path).resolve()
        if candidate != self.project_root and self.project_root not in candidate.parents:
            return None

        return candidate

    def _is_placeholder_path(self, path: str):
        if not isinstance(path, str):
            return True

        normalized = path.replace("\\", "/").strip().lower()
        return (
            not normalized
            or normalized.startswith("path/to/")
            or "<" in normalized
            or ">" in normalized
            or normalized.startswith("your/")
        )

    def _tree(self, directory: Path):
        return [
            {
                "name": path.name,
                "path": str(path.relative_to(self.project_root)),
                "type": "directory" if path.is_dir() else "file",
                **({"children": self._tree(path)} if path.is_dir() else {})
            }
            for path in sorted(directory.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        ]