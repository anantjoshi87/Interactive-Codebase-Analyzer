# Git cloning and temporary folder manager

from contextlib import contextmanager
import tempfile
import shutil

from git import Repo


class RepoFetcher:
    @staticmethod
    @contextmanager
    def clone_to_temp(repo_url: str):
        """
        Clone a Git repository into a temporary directory.

        The directory is automatically deleted when the
        context exits.
        """

        temp_dir = tempfile.mkdtemp(prefix="repo_parse_")

        try:
            print(f"Cloning {repo_url}")
            Repo.clone_from(repo_url, temp_dir, depth=1)

            yield temp_dir

        finally:
            print(f"Cleaning up {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)
