# ggg斗罗同人文 LaTeX 排版版

- [带书签的 PDF](gggDouluo.pdf)：A4，微软雅黑 12pt，共 1472 页、142 个书签，约 4.93 MiB。
- [完整 LaTeX 源码](gggDouluo.tex)。

本目录包含完整小说与独立的 VS Code 工程。作品采用仓库根目录的 [CC BY-NC-SA 4.0 许可证](../LICENSE)。

## 编译

需要 TeX Live（含 XeLaTeX、latexmk）和 VS Code 的 [LaTeX Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop) 扩展。请确保 `latexmk` 和 `xelatex` 可在终端中运行。源码使用微软雅黑、Consolas、TeX Gyre Termes、Latin Modern Math 和 DejaVu Sans 字体；其他系统需提供对应字体或修改字体设置。

双击 `gggDouluo.code-workspace` 打开完整工程，再打开 `gggDouluo.tex`。

- `Ctrl+Alt+B` 编译；保存源码也会自动编译。
- `Ctrl+Alt+V` 预览。
- 生成的 PDF 位于 `build/gggDouluo.pdf`。

也可在本目录运行：

```sh
latexmk -xelatex -synctex=1 -interaction=nonstopmode -file-line-error -outdir=build gggDouluo.tex
```

latexmk 会自动重复编译以更新目录和书签。本地 `.latexmkrc` 使默认 latexmk 命令也使用 XeLaTeX，避免误用 pdfLaTeX 导致字体命令报错；单独打开源码时，编辑器的默认输出可能位于源码旁边。

工程设置关闭了额外 `LaTeX` 扩展的 chktex 检查，避免长篇公式文档触发该扩展的 `ENOBUFS` 提示，编译由 LaTeX Workshop 完成。

编译辅助文件与 `build/` 已加入忽略规则。更新仓库中的 PDF 时，请将 `build/gggDouluo.pdf` 复制为本目录的 `gggDouluo.pdf` 后再提交。

源码是 Markdown 原稿的独立排版副本；修改源码不会自动同步根目录 Markdown，也不会自动上传 GitHub。
