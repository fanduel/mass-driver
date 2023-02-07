"""Githubas Forge. Using the github lib if available"""

from github import Github

from mass_driver.forge import BranchName, Forge


class GithubForge(Forge):
    """Github API wrapper, capable of creating/getting PRs"""

    def create_pr(
        self,
        forge_repo_url: str,
        base_branch: BranchName,
        head_branch: BranchName,
        pr_title: str,
        pr_body: str,
        draft: bool,
    ):
        """Send a PR, with msg body, to forge_repo for given branch of repo_path"""
        repo_name = self.detect_github_repo(forge_repo_url)
        api = Github(self.auth_token)
        repo = api.get_repo(repo_name)
        breakpoint()
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=head_branch,
            base=base_branch,
            draft=draft,
        )
        return pr.html_url

    def get_pr(self, forge_repo: str, pr_id: str):
        """Send a PR with msg on upstream of repo at repo_path, for given branch"""
        api = Github(self.auth_token)
        repo = api.get_repo(forge_repo)
        return repo.get_pull(int(pr_id))

    def detect_repo_name(self, remote_url: str) -> str:
        """Detect that one repo ID"""
        return _detect_github_repo(remote_url)

    def detect_pr_identifier(self, pr_html_url: str) -> str:
        """Detect that one PR number"""
        return _detect_pr_number(pr_html_url)


def _detect_github_repo(remote_url: str):
    """Find the github remote from a URL, cloneable or generic

    >>> _detect_github_repo("git@github.com:OverkillGuy/sphinx-needs-test.git")
    'OverkillGuy/sphinx-needs-test'
    >>> _detect_github_repo("https://github.com/OverkillGuy/sphinx-needs-test")
    'OverkillGuy/sphinx-needs-test'
    >>> _detect_github_repo("https://github.com/OverkillGuy/sphinx-needs-test/pull/123")
    'OverkillGuy/sphinx-needs-test'
    """
    if remote_url.startswith("https://"):
        no_prefix = remote_url.removeprefix("https://github.com/")
        if "/pull/" in no_prefix:
            pull_index = no_prefix.index("/pull/")
            return no_prefix[:pull_index]
        return no_prefix
    if ":" not in remote_url:
        raise ValueError(
            f"Given remote URL is not a valid Github clone URL: '{remote_url}'"
        )
    _junk, gh_name = remote_url.split(":")
    return gh_name.removesuffix(".git")


def _detect_pr_number(pr_html_url: str) -> str:
    """Find the github PR number given a PR's HTML URL

    >>> _detect_pr_number("https://github.com/OverkillGuy/sphinx-needs-test/pull/123")
    '123'
    """
    if "/pull/" not in pr_html_url:
        raise ValueError(f"Given URL isn't a PR html URL: '{pr_html_url}'")
    url_parts = pr_html_url.split("/")
    return url_parts[-1]
