"""
repo_loader.py - Pipeline Stage 1
Clones any GitHub repository and prepares it for analysis.
"""

import os
import shutil
import subprocess
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RepoMetadata:
      url: str
      name: str
      local_path: str
      languages: List[str] = field(default_factory=list)
      file_count: int = 0
      total_lines: int = 0
      branch: str = "main"


class RepoLoader:
      """
          Stage 1: Clone and inventory a GitHub repository.
              Supports public and authenticated (token) repositories.
                  """

    def __init__(self, workspace: str = "./workspace", github_token: Optional[str] = None):
              self.workspace = Path(workspace)
              self.workspace.mkdir(parents=True, exist_ok=True)
              self.github_token = github_token or os.getenv("GITHUB_TOKEN")

    def load(self, repo_url: str, branch: str = "main") -> RepoMetadata:
              """Clone the repository and return metadata."""
              repo_name = self._extract_name(repo_url)
              local_path = self.workspace / repo_name

        if local_path.exists():
                      logger.info(f"Removing existing clone at {local_path}")
                      shutil.rmtree(local_path)

        authenticated_url = self._build_auth_url(repo_url)
        self._clone(authenticated_url, local_path, branch)

        metadata = RepoMetadata(
                      url=repo_url,
                      name=repo_name,
                      local_path=str(local_path),
                      branch=branch,
        )
        self._inventory(metadata, local_path)
        logger.info(f"Loaded {repo_name}: {metadata.file_count} files, {metadata.total_lines} lines")
        return metadata

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_name(self, url: str) -> str:
              return url.rstrip("/").split("/")[-1].replace(".git", "")

    def _build_auth_url(self, url: str) -> str:
              if self.github_token and url.startswith("https://github.com/"):
                            return url.replace("https://", f"https://{self.github_token}@")
                        return url

    def _clone(self, url: str, dest: Path, branch: str) -> None:
              cmd = ["git", "clone", "--depth", "1", "--branch", branch, url, str(dest)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
                      # Retry without branch flag (default branch)
                      cmd_default = ["git", "clone", "--depth", "1", url, str(dest)]
                      result2 = subprocess.run(cmd_default, capture_output=True, text=True)
                      if result2.returncode != 0:
                                        raise RuntimeError(f"Clone failed: {result2.stderr}")

              def _inventory(self, meta: RepoMetadata, path: Path) -> None:
                        lang_map = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                                                        ".java": "Java", ".go": "Go", ".rb": "Ruby", ".cpp": "C++",
                                                        ".c": "C", ".rs": "Rust", ".cs": "C#", ".php": "PHP"}
                        langs = set()
                        file_count = 0
                        total_lines = 0

        for f in path.rglob("*"):
                      if f.is_file() and not any(p.startswith(".") for p in f.parts):
                                        ext = f.suffix.lower()
                                        if ext in lang_map:
                                                              langs.add(lang_map[ext])
                                                              try:
                                                                                        lines = f.read_text(encoding="utf-8", errors="ignore").count("\n")
                                                                                        total_lines += lines
except Exception:
                        pass
                file_count += 1

        meta.languages = sorted(langs)
        meta.file_count = file_count
        meta.total_lines = total_lines


if __name__ == "__main__":
      import json
    loader = RepoLoader()
    meta = loader.load("https://github.com/Theesthan/GiFrac")
    print(json.dumps(meta.__dict__, indent=2))
