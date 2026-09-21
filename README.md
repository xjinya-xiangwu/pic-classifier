# PhotoCurator — 服装照片本地分组整理

把一批 500–1000 张拍摄照片按 **衣着 + 模特姿势 + 拍摄角度** 自动分组（背景/光线/表情不参与判断），逐组人工挑选 1 张保留，最后在源文件夹内统一重命名（组名_序号，保留张加 `_精选`），全程可撤销。

## 安装与运行（macOS）

**最简方式（推荐）**：打开「终端」（启动台搜索"终端"），粘贴这一行并回车：

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/xjinya-xiangwu/pic-classifier/main/install_mac.sh)
```

自动完成：下载代码到 `~/PhotoCurator` → 安装依赖 → 在**应用程序**里生成 PhotoCurator.app → 启动并打开浏览器。以后在**启动台双击 PhotoCurator** 即可，不再需要终端。

> 若 `raw.githubusercontent.com` 打不开（网络原因）：在浏览器打开仓库里的 `install_mac.sh` → 原始内容 → 另存为 `install_mac.sh`，然后终端执行 `bash ` 拖入该文件回车，效果相同。

**首次准备**：安装过程中若弹出「命令行开发者工具」安装窗口，点**安装**等 2-5 分钟，脚本会自动继续；装好后在 App「设置」里填 boyue 中转站的 API Key（sk- 开头，每台 Mac 填一次）。

<details>
<summary>老方法：手动下载 ZIP + 终端运行（备选）</summary>

1. 仓库页 → Code → Download ZIP → 解压。
2. 终端输入 `bash `（末尾有空格），把 `run.command` 拖进窗口，回车。
3. 双击运行需先修复执行权限：`chmod +x ` 拖入 `run.command` 回车。

</details>

**小技巧**：扫描时需要填照片文件夹路径——在 Finder 里选中该文件夹按 `Cmd+Option+C` 复制"路径名称"，再到 App 里粘贴。

关闭 App：点击 PhotoCurator 窗口/浏览器标签即可（后台服务随其退出；或在活动监视器结束 python）。升级版本：重新执行安装命令。

Windows 调试环境用 `run.bat`。

## macOS 常见拦截与解决

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| 「无法执行，因为没有正确的访问权限」 | 从 Windows/微信传来的文件丢失可执行位 | 用上面 `bash run.command` 方式运行；或 `chmod +x run.command` 后双击 |
| 「无法验证开发者 / 已损坏」 | macOS 隔离标记（网络下载） | 系统设置 → 隐私与安全性 → 点「仍要打开」；或终端执行 `xattr -dr com.apple.quarantine .`（在本目录下） |
| 首次扫描时询问「"python"想要访问文件夹」 | macOS 访问控制 | 点「允许」 |
| 报错含 `$'\r': command not found` | 文件被转成 Windows 换行符 | 重新 `git clone` 本仓库获取正确版本，不要用微信传文件 |

## 使用流程

1. **设置** → 填 API Key（默认智谱 GLM，OpenAI 兼容协议；可改 base_url + 模型名换任何兼容服务商）。可用 `python app.py check-api` 验证连通。
2. 首页输入照片文件夹路径 → **扫描**（支持 heic/heif/jpg/jpeg/png，可选含子文件夹）。
3. **开始识别**（并发调用视觉模型，逐张打标签；中断后再次点击只处理未完成部分，已识别的照片不会重复计费）。
4. 左侧组列表逐组查看，点击缩略图选该组保留的一张（推荐张有蓝框提示；键盘 `←→` 移动、`空格` 选中、`回车` 下一组）。
5. **完成验收 → 原地重命名**：源文件夹内文件改名为 `G01_白连衣裙_叉腰_正面全身_001.png`，每组保留张文件名带 `_精选`。生成清单 CSV 于 `~/.photocurator/`。
6. 后悔 → **撤销上次重命名** 或 `python app.py undo`，恢复全部原文件名。

## 设置项

| 项 | 说明 |
| --- | --- |
| 分组粒度 | 粗(衣着+朝向) / 中(默认, +姿势+景别) / 细(全维度)，切换即时生效、不重新调 API |
| 期望组数 | 填 10 则自动合并到 ≤10 组，0 = 不限 |
| 价格 | 元/百万 token，填了才显示成本（千张约 125 万输入 + 15 万输出 token） |

## 数据位置

索引、标签缓存、缩略图、撤销记录、清单：`~/.photocurator/`。源文件夹只发生**文件名变更**，不移动、不删除、不改内容。

## 测试

`python test_smoke.py` — 覆盖 扫描 → 模拟打标 → 分组/合并 → 互斥选择 → 重命名 → 撤销 全链路。
