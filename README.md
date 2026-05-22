# 医疗数据 3D 分割与重建

这是一个面向 CT 图像的 3D 分割与重建原型工程，当前支持一条半自动流程：

```text
CT 图像 / DICOM
  -> 点云生成
  -> Open3D 交互式 3D 可视化
  -> 手动画 mask 分割点云
  -> 保存分割点云
  -> 准备 / 运行 FUNSR 重建
  -> 生成 Three.js 展示网页
```

## 项目状态

当前工程是研究与演示原型，不是临床系统。默认流程使用阈值和人工 mask 完成点云分割，适合课程设计、科研演示和后续算法迭代。

已整理好的核心代码：

- `run_full_pipeline.py`：统一命令入口。
- `src/medical3d_pipeline/ct_to_pointcloud.py`：CT 切片或 DICOM 转点云。
- `src/medical3d_pipeline/manual_mask_segment.py`：Open3D 可视化和手动 mask 分割。
- `src/medical3d_pipeline/funsr_reconstruct.py`：FUNSR 输入准备和训练命令包装。
- `src/medical3d_pipeline/make_web_viewer.py`：生成可展示的 Three.js 网页。

## 重要隐私说明

不要把真实 DICOM、CT 原始图像、患者数据、论文 PDF、大视频、虚拟环境或训练输出提交到 GitHub。仓库中的 `.gitignore` 已默认排除这些内容。

## 环境安装

建议使用 Python 3.10-3.12。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如果要直接读取 DICOM，请确保安装了 `pydicom`。如果只使用已导出的 PNG/JPG 切片，则不需要 DICOM 读取能力。

## 快速开始

### 1. CT 图像转点云

```powershell
python .\run_full_pipeline.py ct-to-pointcloud `
  --input ".\CT图像" `
  --output ".\outputs\pointclouds\ct_pointcloud.ply" `
  --percentile 75 `
  --pixel-step 2 `
  --slice-step 1 `
  --max-points 300000
```

### 2. Open3D 手动画 mask 分割

```powershell
python .\run_full_pipeline.py segment `
  --input ".\outputs\pointclouds\ct_pointcloud.ply" `
  --output-dir ".\outputs\segmentation" `
  --prefix "bone_001"
```

Open3D 窗口中调整视角后按 `C` 截图；在 OpenCV 窗口中左键点选多边形，按 `S` 保存并执行分割。

### 3. 准备 FUNSR 重建

```powershell
python .\run_full_pipeline.py funsr `
  --point-cloud ".\outputs\segmentation\bone_001_segmented.ply" `
  --dataname "bone_001" `
  --output-name "bone_001" `
  --refresh-cache
```

确认 CUDA/PyTorch/FUNSR 环境可用后，再添加 `--run` 启动训练重建。

### 4. 生成展示网页

```powershell
python .\run_full_pipeline.py web `
  --inputs ".\outputs\pointclouds\ct_pointcloud.ply" ".\outputs\segmentation\bone_001_segmented.ply" `
  --names "CT点云" "手动分割结果" `
  --output-dir ".\outputs\web"
```

然后打开：

```text
outputs/web/index.html
```

## 文档

- [完整流程说明](docs/pipeline.md)
- [数据放置说明](docs/data.md)
- [GitHub 上传说明](docs/github.md)
- [项目现状盘点](docs/project_status.md)

## 外部依赖项目

FUNSR、MedCLIP、BiomedCLIP 和 semantic-segmentation-editor 属于外部研究/工具项目。为了保持 GitHub 仓库干净，本仓库默认不提交这些外部下载目录。需要 FUNSR 重建时，请按 `docs/github.md` 中的说明准备 `FUNSR/FUNSR` 目录。

