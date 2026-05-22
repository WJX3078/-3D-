# CT 到分割再到 3D 重建流程

## 流程概览

```text
输入 CT 图像或 DICOM
  -> 阈值提取前景点
  -> 生成 Open3D 点云
  -> 人工选择视角并绘制 mask
  -> 2D mask 投影回 3D 点云
  -> 保存分割点云
  -> FUNSR 表面重建
  -> Three.js 网页展示
```

## 命令入口

统一入口：

```powershell
python .\run_full_pipeline.py --help
```

子命令：

- `ct-to-pointcloud`
- `segment`
- `funsr`
- `web`

## 1. CT 图像转点云

```powershell
python .\run_full_pipeline.py ct-to-pointcloud `
  --input ".\CT图像" `
  --output ".\outputs\pointclouds\ct_pointcloud.ply" `
  --percentile 75 `
  --pixel-step 2 `
  --slice-step 1 `
  --max-points 300000
```

关键参数：

- `--percentile`：自动阈值百分位。值越高，保留点越少。
- `--threshold`：手动阈值，指定后覆盖自动阈值。
- `--pixel-step`：像素下采样。
- `--slice-step`：切片下采样。
- `--xy-spacing`、`--z-spacing`：控制点云比例。

## 2. 手动 mask 分割

```powershell
python .\run_full_pipeline.py segment `
  --input ".\outputs\pointclouds\ct_pointcloud.ply" `
  --output-dir ".\outputs\segmentation" `
  --prefix "bone_001"
```

输出：

```text
outputs/segmentation/bone_001_view.png
outputs/segmentation/bone_001_camera.json
outputs/segmentation/bone_001_mask.png
outputs/segmentation/bone_001_segmented.ply
outputs/segmentation/bone_001_segmented.pcd
outputs/segmentation/bone_001_remaining.ply
```

## 3. FUNSR 重建

准备 FUNSR 输入：

```powershell
python .\run_full_pipeline.py funsr `
  --point-cloud ".\outputs\segmentation\bone_001_segmented.ply" `
  --dataname "bone_001" `
  --output-name "bone_001" `
  --refresh-cache
```

运行 FUNSR：

```powershell
python .\run_full_pipeline.py funsr `
  --point-cloud ".\outputs\segmentation\bone_001_segmented.ply" `
  --dataname "bone_001" `
  --output-name "bone_001" `
  --gpu 0 `
  --refresh-cache `
  --run
```

## 4. 网页展示

```powershell
python .\run_full_pipeline.py web `
  --inputs ".\outputs\pointclouds\ct_pointcloud.ply" ".\outputs\segmentation\bone_001_segmented.ply" `
  --names "CT点云" "手动分割结果" `
  --output-dir ".\outputs\web"
```

打开：

```text
outputs/web/index.html
```

