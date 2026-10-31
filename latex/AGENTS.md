# 小说写作入口

后续章节直接编辑本目录的 `ggg斗罗同人文.tex`。这是一份完整主稿，不要再从旧 Markdown 重新生成或覆盖它。

新章节写在末尾 `\backmatter` 与 `\end{document}` 之前，用 `\chapter{第一百四十二章：标题}` 等现有格式。保留已有公式、颜色、字体与独立居中的数学显示方式。

本机桌面 `ggg斗罗同人文_LaTeX` 是本目录的目录联接，两个路径指向同一批文件。

编译：`python -X utf8 publish.py --build-only`。编译和自动更新目录书签由 Python 直接调用 XeLaTeX 完成，避免 latexmk 的中文路径问题。

发布：`python -X utf8 publish.py`，或双击 `一键发布.cmd`；会编译、更新本目录及仓库根目录的同名 PDF、提交并推送 GitHub。只有用户要求发布或已有明确授权时才运行发布命令；日常检查使用 `--build-only`。

编译失败不得发布；不要提交 `build`、日志或辅助文件。根目录 Markdown 是迁移前的存档，后续正文以本 `.tex` 为准。
