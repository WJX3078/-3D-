# 数据放置说明

本项目不建议把医疗原始数据提交到 GitHub。请在本地按下面结构放置数据：

```text
data/
  raw/
    dicom/
  ct_slices/
  pointclouds/
outputs/
  pointclouds/
  segmentation/
  web/
```

当前脚本也兼容旧目录，例如：

```text
CT图像/
ZHANG JING RTKA/
```

## 输入类型

- PNG/JPG/TIF 切片：可直接用于 `ct-to-pointcloud`。
- DICOM：需要安装 `pydicom`。
- PLY/PCD 点云：可直接用于 `segment` 或 `web`。

## 不要提交到 GitHub 的内容

- DICOM、CT 原始图像、患者数据。
- `.venv`、`.venv-1` 等虚拟环境。
- `outputs/` 下的结果。
- 论文 PDF、大视频、演示素材。
- 外部下载的完整研究仓库。

