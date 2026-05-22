# GitHub 上传说明

## 1. 本地初始化 Git

当前环境没有检测到 `git` 命令。请先安装 Git for Windows，然后在项目根目录执行：

```powershell
git init
git add README.md requirements.txt requirements-funsr.txt run_full_pipeline.py src docs .gitignore
git commit -m "Initial GitHub-ready CT 3D segmentation pipeline"
```

如果要包含旧的本地脚本，可以额外添加：

```powershell
git add PROJECT_STATUS.md PIPELINE_README.md
```

## 2. 创建 GitHub 仓库

在 GitHub 网页上新建一个空仓库，例如：

```text
medical-ct-3d-segmentation-reconstruction
```

不要勾选自动生成 README，因为本项目已经有 `README.md`。

## 3. 关联远程仓库并推送

替换下面的地址为你的仓库地址：

```powershell
git remote add origin https://github.com/<your-user>/medical-ct-3d-segmentation-reconstruction.git
git branch -M main
git push -u origin main
```

## 4. 推送前检查

先看一下即将提交的文件：

```powershell
git status --short
```

确认不要出现这些内容：

```text
.venv/
.venv-1/
ZHANG JING RTKA/
CT图像/
predictions/
outputs/
论文/
PPT备选图片/
*.dcm
*.pdf
*.mp4
```

## 5. FUNSR 目录说明

本仓库的 `funsr` 子命令默认寻找：

```text
FUNSR/FUNSR/
```

但 `.gitignore` 默认排除了 `FUNSR/`，因为它是外部项目并含有数据/历史仓库。上传 GitHub 时建议只在 README 中说明如何准备 FUNSR，而不是把整个外部目录提交进去。

