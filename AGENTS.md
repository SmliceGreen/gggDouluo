# 小说写作入口

后续章节直接编辑仓库根目录的 `ggg斗罗同人文.tex`。这是唯一主稿，不要手动编辑 Markdown 副本。

新章节写在末尾 `\backmatter` 与 `\end{document}` 之前，沿用 `\chapter{第一百四十二章：标题}` 等格式。保留已有公式、染色、字体和独立居中的数学显示方式。

编译：`latexmk -xelatex ggg斗罗同人文.tex`，或用 `xelatex` 多遍编译直到目录收敛。CJK 字体由 ctex 自动检测系统字体。

Markdown 副本：`python tex2md.py ggg斗罗同人文.tex ggg斗罗同人文.md` 从主稿逆生成，供 pandoc 管线和阅读使用。

发布：通过 GitHub Actions（`.github/workflows/build-release.yml`）自动构建。不要提交 `build`、`LatexBuild`、日志或辅助文件。历史版本通过 Git 历史查询。
