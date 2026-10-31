#!/usr/bin/env python3
"""Compile the Chinese-named master and publish this novel to its Git repository."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

BOOK = "ggg斗罗同人文"
PROJECT = Path(__file__).absolute().parent  # Keep Chinese junction paths for compilation.
EXPECTED_REMOTE = "github.com/smlicegreen/gggdouluo"
MANAGED = {
    "README.md", "AGENTS.md", ".gitignore", "publish.py", "一键发布.cmd",
    ".vscode/settings.json", ".vscode/extensions.json", ".vscode/tasks.json",
    f"{BOOK}.tex", f"{BOOK}.pdf", f"{BOOK}.code-workspace",
}
LEGACY_PATHS = {
    "ggg斗罗同人文.md", "latex/.gitignore", "latex/AGENTS.md", "latex/README.md",
    "latex/publish.py", "latex/一键发布.cmd", "latex/.vscode/settings.json",
    "latex/.vscode/extensions.json", "latex/.vscode/tasks.json",
    f"latex/{BOOK}.tex", f"latex/{BOOK}.pdf", f"latex/{BOOK}.code-workspace",
}


class PublishError(Exception):
    pass


def say(message: str) -> None:
    print(message, flush=True)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_copy(source: Path, target: Path) -> None:
    if target.is_file() and digest(source) == digest(target):
        return
    descriptor, temporary = tempfile.mkstemp(prefix=".pdf-", suffix=".tmp", dir=target.parent)
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        shutil.copyfile(source, temporary_path)
        temporary_path.replace(target)
    finally:
        temporary_path.unlink(missing_ok=True)


@contextlib.contextmanager
def project_lock(build: Path):
    build.mkdir(exist_ok=True)
    with (build / "automation.lock").open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        started = time.monotonic()
        announced = False
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if not announced:
                    say("正在等待已有的编译或发布任务完成……")
                    announced = True
                if time.monotonic() - started > 300:
                    raise PublishError("等待超时，请等当前任务结束后再运行。")
                time.sleep(0.25)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def auxiliary_state(build: Path) -> tuple:
    return tuple(
        digest(path) if path.is_file() else None
        for path in (build / f"{BOOK}{suffix}" for suffix in (".aux", ".toc", ".out"))
    )


def compile_book(project: Path, force: bool = False) -> dict:
    source = project / f"{BOOK}.tex"
    if not source.is_file():
        raise PublishError(f"找不到主稿：{source}")
    build = project / "build"
    build.mkdir(exist_ok=True)
    source_hash = digest(source)
    fingerprint = hashlib.sha256((source_hash + digest(Path(__file__))).encode()).hexdigest()
    published = project / f"{BOOK}.pdf"
    receipt = build / "编译记录.json"
    if not force and receipt.is_file() and published.is_file():
        try:
            previous = json.loads(receipt.read_text(encoding="utf-8"))
            if previous.get("fingerprint") == fingerprint and previous.get("pdf_sha256") == digest(published):
                say(f"源码未变，使用已验证的 PDF（{previous['pages']} 页）。")
                return previous
        except (ValueError, KeyError):
            pass
    engine = shutil.which("xelatex")
    if not engine:
        raise PublishError("找不到 XeLaTeX，请确认已安装 TeX Live，并重新打开 VS Code。")
    output = build / "编译输出.txt"
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = str(int(source.stat().st_mtime))
    environment["FORCE_SOURCE_DATE"] = "1"
    command = [engine, "-no-shell-escape", "-synctex=1", "-interaction=nonstopmode",
               "-halt-on-error", "-file-line-error", f"-output-directory={build}", str(source)]
    stable = False
    with output.open("w", encoding="utf-8") as console:
        for turn in range(1, 7):
            before = auxiliary_state(build)
            say(f"正在编译第 {turn} 遍，更新目录和书签……")
            result = subprocess.run(command, cwd=project, env=environment, stdout=console,
                                    stderr=subprocess.STDOUT, timeout=300)
            console.flush()
            if result.returncode:
                tail = "\n".join(output.read_text(encoding="utf-8", errors="replace").splitlines()[-35:])
                raise PublishError(f"编译失败，已保留上次成功的 PDF。\n{tail}\n完整日志：{output}")
            if digest(source) != source_hash:
                raise PublishError("编译期间主稿发生了变化，请保存后重新运行；本次不会发布。")
            if before == auxiliary_state(build):
                stable = True
                break
    if not stable:
        raise PublishError("目录或交叉引用仍在变化，本次未发布。请检查编译日志。")
    log = (build / f"{BOOK}.log").read_text(encoding="utf-8", errors="replace")
    if "Missing character:" in log or re.search(r"Overfull \\[hv]box", log):
        raise PublishError(f"发现缺字或超宽内容，本次未发布。请检查：{build / (BOOK + '.log')}")
    pages = re.findall(r"Output written on .*?\((\d+)\s+pages?[,)]", log, re.S)
    generated = build / f"{BOOK}.pdf"
    if not pages or not generated.is_file():
        raise PublishError("编译没有生成可确认页数的 PDF，本次未发布。")
    with generated.open("rb") as stream:
        header = stream.read(8)
        stream.seek(max(0, generated.stat().st_size - 2048))
        ending = stream.read()
    if not header.startswith(b"%PDF-") or b"%%EOF" not in ending:
        raise PublishError("生成的 PDF 不完整，本次未发布。")
    atomic_copy(generated, published)
    data = {"fingerprint": fingerprint, "source_sha256": source_hash,
            "pdf_sha256": digest(published), "pages": int(pages[-1]),
            "compiled_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    receipt.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    say(f"编译完成：{data['pages']} 页，{published.stat().st_size / 1024**2:.2f} MiB。")
    return data


def git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(["git", "-C", str(repository), *arguments], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, encoding="utf-8", errors="replace",
                            env=environment, timeout=180)
    if check and result.returncode:
        raise PublishError(f"Git 操作失败：{result.stdout.strip()}\n已有文件与本地提交均已保留。")
    return result



def managed_paths(repository: Path) -> set[str]:
    tracked = set(git(repository, "ls-files", "-z").stdout.strip("\0").split("\0"))
    removed_legacy = {name for name in LEGACY_PATHS if name in tracked and not (repository / name).exists()}
    return MANAGED | removed_legacy


def find_repository(project: Path) -> Path:
    location = project.resolve()
    repository = Path(git(location, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if location != repository:
        raise PublishError("请从本仓库根目录的写作工程运行发布工具。")
    branch = git(repository, "branch", "--show-current").stdout.strip()
    if branch != "main":
        raise PublishError("当前不是 main 分支；请切回主分支后再发布。")
    remote = git(repository, "remote", "get-url", "origin").stdout.strip().lower().rstrip("/")
    normalized = remote.removesuffix(".git").replace("git@github.com:", "github.com/")
    normalized = normalized.removeprefix("https://").removeprefix("http://")
    if normalized != EXPECTED_REMOTE:
        raise PublishError("origin 并非本小说的 GitHub 仓库，本次不会上传。")
    staged = set(git(repository, "diff", "--cached", "--name-only", "-z").stdout.strip("\0").split("\0")) - {""}
    if staged - managed_paths(repository):
        raise PublishError("暂存区中还有其他文件，请先处理那些文件，再发布小说；本次未提交。")
    say("正在检查 GitHub 仓库状态……")
    git(repository, "fetch", "origin")
    behind = int(git(repository, "rev-list", "--count", "HEAD..origin/main").stdout.strip())
    if behind:
        raise PublishError("GitHub 上有尚未同步的新提交，请先合并后再发布；不会强行覆盖远端。")
    return repository


def publish_book(project: Path, compilation: dict, message: str | None) -> None:
    repository = find_repository(project)
    if digest(project / f"{BOOK}.tex") != compilation["source_sha256"]:
        raise PublishError("主稿在编译后发生变化，请保存后重新发布。")
    tracked = set(git(repository, "ls-files", "-z").stdout.strip("\0").split("\0"))
    allowed = managed_paths(repository)
    candidates = sorted(name for name in allowed if (repository / name).exists() or name in tracked)
    git(repository, "add", "--all", "--", *candidates)
    staged = set(git(repository, "diff", "--cached", "--name-only", "-z").stdout.strip("\0").split("\0")) - {""}
    if staged - allowed:
        raise PublishError("暂存区在发布过程中出现了其他文件，本次未提交。")
    changed = git(repository, "diff", "--cached", "--quiet", check=False)
    if changed.returncode == 1:
        git(repository, "diff", "--cached", "--check")
        title = message or f"更新《{BOOK}》源码及 PDF（{time.strftime('%Y-%m-%d %H:%M')}）"
        result = git(repository, "commit", "-m", title)
        say(result.stdout.strip())
    elif changed.returncode:
        raise PublishError(changed.stdout)
    else:
        say("文件没有变化，无需新增提交。")
    local = git(repository, "rev-parse", "HEAD").stdout.strip()
    upstream = git(repository, "rev-parse", "origin/main").stdout.strip()
    if local != upstream:
        say("正在上传到 GitHub……")
        result = git(repository, "push", "origin", "main", check=False)
        if result.returncode:
            raise PublishError(f"上传未完成，本地提交已保留；恢复网络或登录后，重新运行即可继续上传。\n{result.stdout}")
    remote_line = git(repository, "ls-remote", "origin", "refs/heads/main").stdout.split()
    if not remote_line or remote_line[0] != local:
        raise PublishError("远端提交校验未通过，请检查网络后重试。")
    say(f"发布完成：https://github.com/SmliceGreen/gggDouluo/commit/{local}")


def main() -> int:
    parser = argparse.ArgumentParser(description="编译《ggg斗罗同人文》并提交 GitHub。")
    parser.add_argument("--build-only", action="store_true", help="只编译，不提交或上传")
    parser.add_argument("--force", action="store_true", help="即使源码未变也重新编译")
    parser.add_argument("--message", help="本次提交说明")
    options = parser.parse_args()
    try:
        with project_lock(PROJECT / "build"):
            compilation = compile_book(PROJECT, options.force)
            if not options.build_only:
                publish_book(PROJECT, compilation, options.message)
        return 0
    except (PublishError, OSError, subprocess.TimeoutExpired) as error:
        say(f"\n未完成：{error}")
        return 1
    except KeyboardInterrupt:
        say("\n操作已取消。")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
