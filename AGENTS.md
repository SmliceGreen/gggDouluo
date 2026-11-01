# 小说写作入口

后续章节直接编辑仓库根目录的 `ggg斗罗同人文.tex`。这是唯一主稿，不要重建旧 Markdown 或恢复重复正文副本。

新章节写在末尾 `\backmatter` 与 `\end{document}` 之前，沿用 `\chapter{第一百四十二章：标题}` 等格式。保留已有公式、染色、字体和独立居中的数学显示方式。

本机桌面 `ggg斗罗同人文_LaTeX` 是仓库根目录的目录联接；桌面入口与仓库访问的是同一份文件。

编译：`python -X utf8 publish.py --build-only`。Python 直接调用 XeLaTeX，支持中文路径，并自动更新目录、引用和章节书签。成功后更新根目录同名 PDF；`build` 只存本地编译辅助文件。

发布：`python -X utf8 publish.py`，或双击 `一键发布.cmd`，会提交本小说及相关工具并推送 GitHub。仅在用户要求发布或已有明确授权时运行发布命令；日常检查用 `--build-only`。

编译失败不得发布，不要提交 `build`、日志或辅助文件，不要重新生成 `latex` 目录中的重复 PDF。历史版本通过 Git 历史查询。
