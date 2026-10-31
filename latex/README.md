# ggg斗罗同人文

- [最新 PDF（含章节书签）](ggg斗罗同人文.pdf)
- [小说主稿：ggg斗罗同人文.tex](ggg斗罗同人文.tex)

后续章节直接写进这份 `.tex`，放在文件末尾 `\backmatter` 与 `\end{document}` 之前，沿用已有的 `\chapter{章节标题}` 格式。

## 写作与编译

本机桌面 `ggg斗罗同人文_LaTeX` 直接指向仓库中的这个目录，两处访问的是同一份主稿。双击桌面“ggg斗罗同人文（写作）”或本目录的 `ggg斗罗同人文.code-workspace`，打开源码后编辑。

需要 Python 3、TeX Live（XeLaTeX）、Git，以及 VS Code 的 [LaTeX Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)。字体包括微软雅黑、Consolas、TeX Gyre Termes、Latin Modern Math、DejaVu Sans；其他系统需提供对应字体或调整字体设置。

- `Ctrl+Alt+B` 编译，保存源码也会编译。
- `Ctrl+Alt+V` 预览 `build/ggg斗罗同人文.pdf`。
- 编译成功后，同目录的 `ggg斗罗同人文.pdf` 会自动更新，含目录与章节书签。

编译入口直接调用 XeLaTeX，支持中文目录与文件名，并自动重复编译直到目录、引用稳定。无需 latexmk；单独打开 `.tex` 可能无法加载工程配置，请使用工作区文件。

```sh
python -X utf8 publish.py --build-only
```

## 一键发布

先保存源码，再双击桌面“一键发布ggg斗罗同人文”，或本目录的 `一键发布.cmd`。也可以运行：

```sh
python -X utf8 publish.py
```

工具会自动编译，更新本目录和仓库根目录的同名 PDF，只提交小说及其编译发布配置，然后推送到 GitHub 的 `main` 分支。可通过 `--message "本次更新说明"` 指定提交说明；`--force --build-only` 可强制重新编译。

首次使用需要 Git 已登录且有仓库写入权限。本工具不保存账号密码。编译失败时保留上次成功的 PDF，源码未变化时复用已验证 PDF，不会反复制造重复提交；上传失败会保留本地提交，下次运行会继续上传。

`build` 和辅助文件已经排除。根目录 Markdown 保留为迁移前存档，后续以 `.tex` 为主稿。

作品采用根目录的 [CC BY-NC-SA 4.0 许可证](https://github.com/SmliceGreen/gggDouluo/blob/main/LICENSE)。
