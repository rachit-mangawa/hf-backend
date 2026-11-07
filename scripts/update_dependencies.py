"""Scans upstream git repositories in requirements.in for updates and recompiles requirements.txt."""

import argparse
import os
import re
import subprocess
import sys
from typing import NamedTuple


class GitDep(NamedTuple):
    raw_line: str
    owner: str
    repo: str
    url: str
    current_ref: str | None
    subdirectory: str | None


GIT_URL_PATTERN = re.compile(
    r"^git\+(https://github\.com/([^/]+)/([^/.]+)(?:\.git)?)(?:@([^#]+))?(?:#subdirectory=(.+))?$"
)


def parse_semver_key(tag: str):
    clean = tag.lstrip("vV")
    parts = []
    for piece in clean.split("."):
        nums = re.findall(r"\d+", piece)
        parts.append(int(nums[0]) if nums else 0)
    return parts


def get_remote_refs(git_url: str) -> dict[str, str]:
    """Returns mapping of ref name (e.g. 'refs/tags/v1.2' or 'refs/heads/main') to commit hash."""
    result = subprocess.run(
        ["git", "ls-remote", git_url],
        capture_output=True,
        text=True,
        check=True,
    )
    refs = {}
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            commit, ref_name = parts[0], parts[1]
            # Strip dereferenced tag suffix ^{}
            if ref_name.endswith("^{}"):
                ref_name = ref_name[:-3]
            refs[ref_name] = commit
    return refs


def find_latest_tag(refs: dict[str, str]) -> str | None:
    tags = []
    for ref in refs:
        if ref.startswith("refs/tags/"):
            tag_name = ref.replace("refs/tags/", "")
            tags.append(tag_name)
    if not tags:
        return None
    tags.sort(key=parse_semver_key)
    return tags[-1]


def find_latest_branch_commit(refs: dict[str, str], branch: str = "main") -> str | None:
    ref_target = f"refs/heads/{branch}"
    if ref_target in refs:
        return refs[ref_target]
    if "HEAD" in refs:
        return refs["HEAD"]
    return None


def main():
    parser = argparse.ArgumentParser(description="Update upstream git dependencies in requirements.in.")
    parser.add_argument(
        "--mode",
        choices=["auto", "tags", "commits"],
        default="auto",
        help="Update strategy: 'tags' (prefer newer semver tags), 'commits' (track latest main branch commit), or 'auto'.",
    )
    parser.add_argument(
        "--req-in",
        default="requirements.in",
        help="Path to requirements.in file.",
    )
    parser.add_argument(
        "--req-txt",
        default="requirements.txt",
        help="Path to requirements.txt file.",
    )
    parser.add_argument(
        "--compile",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Recompile requirements.txt using uv after updating.",
    )

    args = parser.parse_args()

    if not os.path.exists(args.req_in):
        print(f"Error: {args.req_in} not found.", file=sys.stderr)
        sys.exit(1)

    with open(args.req_in, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated_lines = []
    changes = []

    for line in lines:
        stripped = line.strip()
        match = GIT_URL_PATTERN.match(stripped)
        if not match:
            updated_lines.append(line)
            continue

        full_url, owner, repo, current_ref, subdir = match.groups()
        print(f"Checking upstream for {owner}/{repo} (current ref: {current_ref})...")

        try:
            refs = get_remote_refs(f"https://github.com/{owner}/{repo}.git")
        except Exception as e:
            print(f"Warning: Failed to query git ls-remote for {owner}/{repo}: {e}", file=sys.stderr)
            updated_lines.append(line)
            continue

        target_ref = current_ref

        if args.mode == "tags":
            latest_tag = find_latest_tag(refs)
            if latest_tag:
                target_ref = latest_tag
        elif args.mode == "commits":
            latest_commit = find_latest_branch_commit(refs, "main")
            if latest_commit:
                target_ref = latest_commit
        else:  # auto
            # If current ref is formatted like a version tag (v1.x or 1.x), look for newest tag
            if current_ref and re.match(r"^v?\d+(\.\d+)*", current_ref):
                latest_tag = find_latest_tag(refs)
                if latest_tag:
                    target_ref = latest_tag
            else:
                # Default to latest commit or latest tag
                latest_tag = find_latest_tag(refs)
                latest_commit = find_latest_branch_commit(refs, "main")
                target_ref = latest_tag if latest_tag else latest_commit

        if target_ref and target_ref != current_ref:
            changes.append(f"{repo}: {current_ref} -> {target_ref}")
            new_line = f"git+{full_url}@{target_ref}"
            if subdir:
                new_line += f"#subdirectory={subdir}"
            new_line += "\n"
            updated_lines.append(new_line)
        else:
            updated_lines.append(line)

    with open(args.req_in, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)

    if changes:
        print("Updated requirements.in:")
        for change in changes:
            print(f"  - {change}")
    else:
        print("requirements.in is already up to date with requested refs.")

    if args.compile:
        print(f"Compiling {args.req_txt} with uv...")
        cmd = [
            "uv",
            "pip",
            "compile",
            args.req_in,
            "-o",
            args.req_txt,
            "--python-version",
            "3.11",
            "--python-platform",
            "linux",
            "--extra-index-url",
            "https://download.pytorch.org/whl/cpu",
            "--emit-index-url",
            "--refresh",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error compiling requirements.txt:\n{result.stderr}", file=sys.stderr)
            sys.exit(result.returncode)
        print("Successfully recompiled requirements.txt.")

    # Check git diff status
    diff_check = subprocess.run(
        ["git", "status", "--porcelain", args.req_in, args.req_txt],
        capture_output=True,
        text=True,
    )
    has_changes = bool(diff_check.stdout.strip())
    print(f"HAS_CHANGES={'true' if has_changes else 'false'}")

    # Set GitHub Actions output if in CI
    gh_output = os.getenv("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"has_changes={'true' if has_changes else 'false'}\n")
            if changes:
                summary = ", ".join(changes)
                f.write(f"changes_summary={summary}\n")


if __name__ == "__main__":
    main()
