# 已有图片转换适配器

模板仅保留原创适配器；上游核心和依赖在本机准备：

```text
python -B dev_tools/prepare_workspace.py --tools pixel --fetch
```

PowerShell 中继续运行 `dev_tools/setup_python.ps1 -WithPixelTools`。上游源码位于 `dev_tools/external/PixelArtConverter/`，固定提交及 MIT 许可见 `dev_tools/manifests/resources.json`；适配器加载前核对固定文件哈希。

在工具环境中导入本目录的 `convert.py`，调用 `convert(source, destination, palette, crop=None, size=(16,16))`；`palette` 提供颜色列表，`crop` 使用归一化裁剪框。尺寸参数是调用默认值，可按任务调整。

仅对已有且可使用的素材执行明确的裁剪、尺寸和调色板转换，不生成新成品美术，不包含组件专属素材。实际清晰度、透明边和风格仍需审阅，转换通过不等于游戏内资产验收。
