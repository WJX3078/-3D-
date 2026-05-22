from __future__ import annotations

import argparse
import html
import shutil
from pathlib import Path

import open3d as o3d


HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CT 3D 分割与重建展示</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; background: #101418; color: #eef3f8; }}
    header {{ height: 56px; display: flex; align-items: center; justify-content: space-between; padding: 0 18px; border-bottom: 1px solid #27313a; background: #151b21; }}
    h1 {{ font-size: 18px; margin: 0; font-weight: 650; }}
    main {{ display: grid; grid-template-columns: 300px 1fr; min-height: calc(100vh - 56px); }}
    aside {{ padding: 16px; border-right: 1px solid #27313a; background: #151b21; overflow: auto; }}
    #viewer {{ width: 100%; height: calc(100vh - 56px); }}
    .item {{ width: 100%; display: flex; justify-content: space-between; gap: 8px; align-items: center; padding: 10px; margin-bottom: 8px; border: 1px solid #34414c; background: #1b232b; color: #eef3f8; cursor: pointer; text-align: left; }}
    .item.active {{ border-color: #4da3ff; background: #203348; }}
    .meta {{ margin-top: 16px; font-size: 13px; color: #aeb8c2; line-height: 1.55; }}
    .hint {{ font-size: 13px; color: #aeb8c2; }}
    @media (max-width: 780px) {{
      main {{ grid-template-columns: 1fr; }}
      aside {{ border-right: 0; border-bottom: 1px solid #27313a; }}
      #viewer {{ height: 68vh; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>CT 3D 分割与重建展示</h1>
    <div class="hint">鼠标拖拽旋转，滚轮缩放</div>
  </header>
  <main>
    <aside>
      <div id="items"></div>
      <div class="meta">
        <div>流程：CT 图像 -> 点云 -> Open3D 手动分割 -> FUNSR 重建 -> Web 展示</div>
        <div id="status">正在初始化...</div>
      </div>
    </aside>
    <div id="viewer"></div>
  </main>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/PLYLoader.min.js"></script>
  <script>
    const models = {models_json};
    const viewer = document.getElementById('viewer');
    const statusEl = document.getElementById('status');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x101418);
    const camera = new THREE.PerspectiveCamera(55, viewer.clientWidth / viewer.clientHeight, 0.01, 100000);
    camera.position.set(0, -260, 220);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(viewer.clientWidth, viewer.clientHeight);
    viewer.appendChild(renderer.domElement);
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const light = new THREE.DirectionalLight(0xffffff, 0.8);
    light.position.set(1, 2, 3);
    scene.add(light);
    const axes = new THREE.AxesHelper(80);
    scene.add(axes);
    const loader = new THREE.PLYLoader();
    let current = null;

    function setActive(index) {{
      document.querySelectorAll('.item').forEach((button, i) => button.classList.toggle('active', i === index));
    }}

    function loadModel(index) {{
      const model = models[index];
      setActive(index);
      statusEl.textContent = '加载：' + model.name;
      loader.load(model.path, geometry => {{
        if (current) scene.remove(current);
        geometry.computeVertexNormals();
        geometry.computeBoundingBox();
        const hasColor = Boolean(geometry.attributes.color);
        const material = new THREE.PointsMaterial({{ size: model.size || 1.4, vertexColors: hasColor, color: model.color || 0x4da3ff }});
        current = new THREE.Points(geometry, material);
        const center = new THREE.Vector3();
        geometry.boundingBox.getCenter(center);
        current.geometry.translate(-center.x, -center.y, -center.z);
        scene.add(current);
        statusEl.textContent = model.name + ' 已加载';
      }}, undefined, error => {{
        statusEl.textContent = '加载失败：' + model.name;
        console.error(error);
      }});
    }}

    const itemsEl = document.getElementById('items');
    models.forEach((model, index) => {{
      const button = document.createElement('button');
      button.className = 'item';
      button.innerHTML = '<span>' + model.name + '</span><span>PLY</span>';
      button.onclick = () => loadModel(index);
      itemsEl.appendChild(button);
    }});
    if (models.length) loadModel(0);

    function animate() {{
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }}
    animate();

    window.addEventListener('resize', () => {{
      camera.aspect = viewer.clientWidth / viewer.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(viewer.clientWidth, viewer.clientHeight);
    }});
  </script>
</body>
</html>
"""


def ensure_ply(source: Path, assets_dir: Path) -> Path:
    target = assets_dir / (source.stem + ".ply")
    if source.suffix.lower() == ".ply":
        shutil.copy2(source, target)
        return target

    pcd = o3d.io.read_point_cloud(str(source))
    if pcd.is_empty():
        raise ValueError(f"Cannot convert empty point cloud: {source}")
    o3d.io.write_point_cloud(str(target), pcd)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a static Three.js viewer for point clouds/meshes.")
    parser.add_argument("--inputs", nargs="+", required=True, type=Path, help="Point clouds to show (.ply or .pcd).")
    parser.add_argument("--names", nargs="*", default=None, help="Display names matching --inputs.")
    parser.add_argument("--output-dir", default=Path("outputs/web"), type=Path)
    args = parser.parse_args(argv)

    assets_dir = args.output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    models = []
    for index, source in enumerate(args.inputs):
        target = ensure_ply(source, assets_dir)
        name = args.names[index] if args.names and index < len(args.names) else source.stem
        models.append(
            {
                "name": html.escape(name),
                "path": "assets/" + target.name,
                "size": 1.4,
            }
        )

    models_json = str(models).replace("'", '"')
    output_html = args.output_dir / "index.html"
    output_html.write_text(HTML_TEMPLATE.format(models_json=models_json), encoding="utf-8")
    print(f"Wrote web viewer: {output_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

