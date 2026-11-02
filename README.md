# ggg斗罗同人文

- [最新 PDF（含章节书签）](ggg斗罗同人文.pdf)
- [小说 LaTeX 主稿](ggg斗罗同人文.tex)

仓库根目录只维护一份小说主稿和一份阅读用 PDF。

## 写作与编译

双击 `ggg斗罗同人文.code-workspace` 打开工程，再编辑同目录的 `.tex`。后续章节放在文件末尾 `\backmatter` 与 `\end{document}` 之前，沿用 `\chapter{章节标题}`。

本机桌面“ggg斗罗同人文（写作）”和 `ggg斗罗同人文_LaTeX` 文件夹直接指向本仓库根目录，访问的是同一份主稿。

需要 Python 3、TeX Live（XeLaTeX）、Git，以及 VS Code 的 [LaTeX Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)。字体包括微软雅黑、Consolas、TeX Gyre Termes、Latin Modern Math、DejaVu Sans；其他系统需提供对应字体或修改字体设置。

- `Ctrl+Alt+B` 编译，保存源码也会编译。
- `Ctrl+Alt+V` 预览。
- 编译成功后，根目录的 `ggg斗罗同人文.pdf` 自动更新，包含目录和章节书签。

```sh
python -X utf8 publish.py --build-only
```

编译入口直接调用 XeLaTeX，支持中文目录与文件名，并重复编译直到目录和引用稳定。请使用工作区文件，以加载本工程配置。

## 一键发布

写完并保存后，双击桌面“一键发布ggg斗罗同人文”，或本目录的 `一键发布.cmd`。也可运行：

```sh
python -X utf8 publish.py
```

工具会编译并更新根目录的同名 PDF，提交小说和相关配置，推送到 GitHub 的 `main` 分支，然后清除该分支历史中的旧 PDF，仅保留最新 PDF。可用 `--message "本次更新说明"` 指定提交说明；`--force --build-only` 可强制重新编译。

历史清理需要 `git-filter-repo`：`python -m pip install --target build/filter-repo-dependency git-filter-repo`。清理会修改历史提交编号并使用带精确版本保护的强制推送；其他克隆需要重新同步。清理前会在桌面 `Douluo历史备份` 文件夹创建 Git bundle。GitHub 的旧 PR、其他引用及后台缓存可能仍保留旧对象，空间占用不保证立即下降。

如果发布已完成但清理失败，解决提示的问题后可单独运行 `python -X utf8 clean_pdf_history.py` 重试。清理只在远端只有 main 且没有标签、本地没有其他分支或标签、已跟踪文件没有未提交改动时执行。

Git 需要已登录且有仓库写入权限，工具不保存账号密码。编译失败会保留上次成功的 PDF；源码未变化时复用已验证 PDF，避免重复提交；上传失败会保留本地提交，下次运行继续上传。

`build` 只存本地编译辅助文件，已排除在提交之外。旧 Markdown 和重复 PDF 已从当前目录结构中移除；源码历史保留，旧 PDF 存在本地历史备份中。

## 许可

© 2026 Smlice Green

本作品采用 **CC BY-NC-SA 4.0（署名—非商业性使用—相同方式共享 4.0 国际）** 许可证。

允许免费阅读、复制、分享和非商业性改编。

使用或转载本作品时必须署名作者 **Smlice Green**。

对本作品进行改编并公开发布时，必须采用相同许可条件。

**禁止将本作品用于商业目的，包括商业性出售、付费传播或其他以商业利益或金钱报酬为主要目的的使用。**

许可证：
https://creativecommons.org/licenses/by-nc-sa/4.0/
