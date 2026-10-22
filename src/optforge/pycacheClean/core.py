"""
core.py — Core logic for pycacheClean CLI tool
"""
import os
import shutil


def find_pycache_dirs(
    base_dir: str,
    exclude_dirs: list[str] | None = None,
    max_depth: int | None = None,
) -> list[str]:
  """
    Walk through directory tree and find all __pycache__ folders.
    
    Args:
        base_dir: Root directory to scan
        exclude_dirs: Folders to skip (e.g., 'venv', '.git')
        max_depth: How many levels deep to go (None = unlimited)
    
    Returns:
        List of full paths to __pycache__ directories
    """
  pycache_dirs = []
  exclude_dirs = exclude_dirs or []
  for root, dirs, files in os.walk(base_dir):
    if max_depth is not None:
      current_depth = root.replace(base_dir, "").count(os.sep)
      if current_depth > max_depth:
        dirs.clear()
        # stop descending
        continue
    # Skip excluded directories
    rel_path = os.path.relpath(root, base_dir)
    parts = rel_path.split(os.sep)
    if any(excluded in parts for excluded in exclude_dirs):
      dirs.clear()
      continue
    # Collect __pycache__ folders
    for dir_name in dirs:
      if dir_name == "__pycache__":
        pycache_dirs.append(os.path.join(root, dir_name))
  return pycache_dirs


def remove_pycache_dirs(
    pycache_list: list[str],
    dry_run: bool = False,
) -> dict:
  """
    Remove __pycache__ directories.
    
    Args:
        pycache_list: List of paths to remove
        dry_run: If True, only report what would be deleted
    
    Returns:
        Dict with 'success', 'failed', and 'errors' counts
    """
  result = {"success": 0, "failed": 0, "errors": []}
  for cache_path in pycache_list:
    try:
      if dry_run:
        print(f"[DRY RUN] Would remove: {cache_path}")
        result["success"] += 1
      else:
        shutil.rmtree(cache_path)
        result["success"] += 1
    except Exception as e:
        return e
  return result
