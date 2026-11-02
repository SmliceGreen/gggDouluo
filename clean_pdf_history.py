#!/usr/bin/env python3
"""Keep source history and only the current PDF on the published main branch."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

PDF = "ggg斗罗同人文.pdf"
REPO = Path(__file__).resolve().parent


class CleanupError(Exception):
    pass


def run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, encoding="utf-8", errors="replace",
                            env=env, timeout=300)
    if check and result.returncode:
        raise CleanupError(f"Git {' '.join(args[:2])} 失败：\n{result.stdout}")
    return result


def preflight(repo: Path) -> dict[str, str]:
    refs = run(repo, "ls-remote", "--heads", "--tags", "origin").stdout.splitlines()
    if len(refs) != 1 or not refs[0].endswith("\trefs/heads/main"):
        raise CleanupError("远端存在多个分支或标签，请先单独处理，避免遗漏历史。")
    local_refs = run(repo, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/tags").stdout.splitlines()
    if local_refs != ["refs/heads/main"]:
        raise CleanupError("本地存在其他分支或标签，请先检查。")
    env = os.environ.copy()
    dependency = repo / "build" / "filter-repo-dependency"
    if dependency.is_dir():
        env["PYTHONPATH"] = str(dependency) + os.pathsep + env.get("PYTHONPATH", "")
    probe = subprocess.run([sys.executable, "-c", "import git_filter_repo"], capture_output=True, env=env)
    if probe.returncode:
        raise CleanupError("缺少 git-filter-repo，请运行 python -m pip install --target build/filter-repo-dependency git-filter-repo。")
    return env


def clean(repo: Path = REPO) -> None:
    repo = repo.resolve()
    if run(repo, "rev-parse", "--show-toplevel").stdout.strip().replace("/", "\\").lower() != str(repo).lower():
        raise CleanupError("请从仓库根目录运行。")
    if run(repo, "branch", "--show-current").stdout.strip() != "main":
        raise CleanupError("当前分支不是 main。")
    remote_url = run(repo, "remote", "get-url", "origin").stdout.strip()
    if repo == REPO and remote_url.rstrip("/").lower().removesuffix(".git") != "https://github.com/smlicegreen/gggdouluo":
        raise CleanupError("origin 不是预期的小说仓库。")
    for args in [("diff", "--quiet"), ("diff", "--cached", "--quiet")]:
        if run(repo, *args, check=False).returncode:
            raise CleanupError("有未提交的已跟踪文件改动，先保存并提交，再运行。")
    refs = run(repo, "ls-remote", "--heads", "--tags", "origin").stdout.splitlines()
    if len(refs) != 1 or not refs[0].endswith("\trefs/heads/main"):
        raise CleanupError("远端存在多个分支或标签，请先单独处理，避免遗漏历史。")
    old = run(repo, "rev-parse", "HEAD").stdout.strip()
    remote = refs[0].split()[0]
    if old != remote:
        raise CleanupError("本地与远端 main 不一致，请先同步。")
    local_refs = run(repo, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/tags").stdout.splitlines()
    if local_refs != ["refs/heads/main"]:
        raise CleanupError("本地存在其他分支或标签，请先检查。")
    tree = run(repo, "rev-parse", "HEAD^{tree}").stdout.strip()
    names = run(repo, "-c", "core.quotepath=false", "ls-tree", "-r", "--name-only", "HEAD").stdout.splitlines()
    pdfs = [name for name in names if name.lower().endswith(".pdf")]
    if pdfs != [PDF]:
        raise CleanupError("当前提交中应当恰好有一份主目录 PDF。")
    if not (repo / PDF).is_file():
        raise CleanupError("找不到本地 PDF。")
    parent = run(repo, "rev-parse", "--verify", "HEAD^", check=False)
    if parent.returncode == 0:
        ancestors = run(repo, "-c", "core.quotepath=false", "rev-list", "--objects", "HEAD^").stdout.splitlines()
        if not any(line.partition(" ")[2].lower().endswith(".pdf") for line in ancestors):
            print("历史中没有旧 PDF，无需重写或强制推送。", flush=True)
            return
    filter_env = preflight(repo)

    backup_dir = repo.parent / "Douluo历史备份"
    backup_dir.mkdir(exist_ok=True)
    bundle = backup_dir / f"历史-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1000000000:09d}.bundle"
    print(f"正在备份历史到 {bundle}……", flush=True)
    run(repo, "bundle", "create", str(bundle), "--all")
    run(repo, "bundle", "verify", str(bundle))

    with tempfile.TemporaryDirectory(prefix="douluo-clean-") as temporary:
        stage = Path(temporary) / "repo"
        clone = subprocess.run(["git", "clone", "--no-local", "--single-branch", "--branch", "main",
                                str(repo), str(stage)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               encoding="utf-8", errors="replace", timeout=300)
        if clone.returncode:
            raise CleanupError(f"创建隔离副本失败：\n{clone.stdout}")
        name = run(repo, "config", "user.name").stdout.strip()
        email = run(repo, "config", "user.email").stdout.strip()
        if not name or not email:
            raise CleanupError("请先设置 Git user.name 和 user.email。")
        run(stage, "config", "user.name", name)
        run(stage, "config", "user.email", email)
        print("正在隔离副本中移除历史 PDF……", flush=True)
        filtered = subprocess.run([sys.executable, "-m", "git_filter_repo", "--force",
                                   "--path-glob", "*.pdf", "--invert-paths"], cwd=stage,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  encoding="utf-8", errors="replace", timeout=300, env=filter_env)
        if filtered.returncode:
            raise CleanupError(f"清理历史失败：\n{filtered.stdout}")
        # Recover exactly the PDF blob committed at the original HEAD, not an unsaved local file.
        blob = run(repo, "rev-parse", f"HEAD:{PDF}").stdout.strip()
        restored = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", blob],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if restored.returncode:
            raise CleanupError("读取已提交 PDF 失败。")
        (stage / PDF).write_bytes(restored.stdout)
        run(stage, "add", "-f", "--", PDF)
        run(stage, "commit", "-m", "更新最新版小说 PDF")
        new = run(stage, "rev-parse", "HEAD").stdout.strip()
        if run(stage, "rev-parse", "HEAD^{tree}").stdout.strip() != tree:
            raise CleanupError("清理后的文件与原始提交不一致，已停止。")
        history = run(stage, "-c", "core.quotepath=false", "rev-list", "--objects", "HEAD^").stdout.splitlines()
        if any(line.partition(" ")[2].lower().endswith(".pdf") for line in history):
            raise CleanupError("清理后历史仍包含 PDF，已停止。")
        if run(repo, "rev-parse", "HEAD").stdout.strip() != old:
            raise CleanupError("本地 HEAD 已变化，已停止。")
        latest_refs = run(repo, "ls-remote", "--heads", "--tags", "origin").stdout.splitlines()
        if latest_refs != [f"{remote}\trefs/heads/main"]:
            raise CleanupError("远端分支或标签在清理期间发生变化，已停止。")
        run(stage, "remote", "add", "publish-target", remote_url)
        print("准备替换远端 main：使用精确版本保护，若远端改变则停止。", flush=True)
        run(stage, "push", f"--force-with-lease=refs/heads/main:{remote}", "publish-target", "HEAD:refs/heads/main")
        result = run(repo, "fetch", "--no-tags", "origin", "main", check=False)
        if result.returncode:
            raise CleanupError("远端已更新，但本地拉取新历史失败；备份在 " + str(bundle))
        if run(repo, "rev-parse", "FETCH_HEAD").stdout.strip() != new:
            raise CleanupError("远端已更新，但读取到的提交发生变化；备份在 " + str(bundle))
        moved = run(repo, "update-ref", "refs/heads/main", new, old, check=False)
        if moved.returncode:
            raise CleanupError("远端已更新，本地分支发生变化；请保留工作区并检查备份 " + str(bundle))
        print(f"完成：main 保留源码历史与最新 PDF。旧历史备份：{bundle}", flush=True)


if __name__ == "__main__":
    try:
        clean()
    except (CleanupError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"\n清理未完成：{exc}", flush=True)
        sys.exit(1)
