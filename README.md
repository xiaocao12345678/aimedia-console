# AI 多模态控制台

Windows 桌面客户端，一套界面调用 6 家国内大模型平台的 **图像理解 / 图像生成 / 视频生成**。
Win11 磨砂玻璃外观（系统级亚克力），六家平台 API Key 集中在一个界面里管理。

- 平台：火山方舟、阿里百炼、腾讯混元（TokenHub）、智谱 GLM、百度千帆、MiniMax
- 界面：PyQt6，无系统标题栏，自绘标题栏 + 玻璃按钮；模型下拉可编辑（新模型直接填 ID）

## 打包成 EXE（免安装）

    dist\AI多模态控制台\           ← 整个文件夹可直接拷到任意 Windows 电脑
      AI多模态控制台.exe          3.0 MB
      _internal\                  61 MB（Qt 运行库，必须与 exe 同目录）
      config.json                 六家平台 Key 与模型记忆（便携模式）
      使用说明.txt
      output\  logs\             首次启动自动创建

打包命令（PyInstaller 6.22，**onedir 而非 onefile**）：

    pyinstaller --noconfirm --clean --onedir --windowed ^
      --name "AI多模态控制台" --icon "assets/app.ico" ^
      --add-data "assets;assets" --hidden-import PyQt6.QtNetwork ^
      --exclude-module PyQt6.QtWebEngineCore --exclude-module PyQt6.QtQuick ^
      app.py

为什么不用 onefile：单文件 exe 每次启动都要把 64MB 依赖解压到临时目录，冷启动 3–10 秒；
onedir 实测 **0.70 秒**窗口就出来了。代价是必须连 `_internal` 一起复制。

配置的两种模式：
- EXE 同级有 `config.json` → 便携模式，配置跟着文件夹走（打包时已放入）
- 没有 → 回落到 `%APPDATA%\AI多模态控制台\config.json`

启动自检：每次启动都会往 `logs/startup.log` 写一行（frozen、exe 目录、实际用的配置文件、
已配置平台），"配置没读到"这类问题看这个文件最快定位。

一键重打包：双击项目根目录的 `build_exe.cmd`（会自动建图标、清 build/dist、带上 config 与使用说明）。

> 坑：`rm -rf dist` 报 `Device or resource busy` 时，不是杀软，而是**某个进程的 cwd 停在这个目录里**
> （Hermes 的 Python kernel、或在此目录启动过后台任务的 shell 都会这样）。查是谁占用：
> `handle64.exe "D:\...\dist"`（Sysinternals），把那个进程结束或让它 cd 出去，就能删了。


## 运行

双击 `run.cmd`，或：

    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" app.py

依赖：PyQt6、requests、Pillow（`pip install -r requirements.txt`）

## 参考图工作流（第一个标签页）

一条流水线把「参考图 + 需求」直接变成视频：

    ① 参考图与需求    上传一张或多张参考图，写清要什么镜头 / 要改什么
    ② 每一步的模型    理解 / 生图 / 视频 三步各自选平台 + 模型（可以来自不同平台，右侧显示「有 Key / 无 Key」）
    ③ 分析并生成素材  一次点击依次完成：理解参考图 → 出分析 → 出视频提示词 → 出首帧参考图
    ④ 视频提示词      自动填入，可手动改；改完点「按此提示词重出参考图」
    ⑤ 视频参考图      生成的首帧图；点图选中（蓝框），支持「基于选中图修改」做图生图迭代
    ⑥ 生成视频        用选中的参考图当首帧 + 当前提示词出视频

细节与约定：
- 理解模型被要求**只输出 JSON**（`analysis` / `video_prompt` / `image_prompt` 三个字段）。
  兼容 ```json 代码块、中文引号、尾逗号；真的解析不出来时把整段文本当视频提示词，流程不中断
- 三步模型的选择会记住（平台 + 模型分别存），下次打开沿用
- 生成的参考图全部落在 `output/`，每次修改生成新的一张并自动选中，旧图保留可回退
- 每一步用的是**该步所选平台**已保存的 Key；缺 Key 会直接提示去密钥界面
- 全部请求/响应照旧进「运行日志」窗口

## 视频编辑（第五个标签页）

输入一段**参考视频**（+ 可选参考图），按指令生成新视频：

    ① 参考视频    本地文件 或 公网 URL（二选一）
    ② 参考图      可选，最多 3 张（换装 / 换物用）
    ③ 指令        例如「把整个画面转换成黏土动画风格，保留人物动作与镜头运动」
    ④ 平台与模型  只有三家支持视频输入，其余平台不在此页出现
    ⑤ 结果        异步任务，进度进「运行日志」；完成后可打开视频

三家契约不同，程序自动处理：

| 平台 | 模型 | 视频输入方式 | 备注 |
|---|---|---|---|
| 阿里百炼 | wan2.7-videoedit / wan3.0-video | 本地 ≤10 MB 自动转 base64，更长的填公网 URL | media 里 video + reference_image，标准 video-synthesis 异步 |
| 火山方舟 | doubao-seedance-2-5 / 2-0 | 本地视频先传 Files API（≤512 MB）拿 file id 再引用；也支持公网 URL | 上传接口不需要开通视频模型，但**生成视频需要先在方舟控制台开通 Seedance** |
| MiniMax | MiniMax-H3 | 本地 ≤40 MB 自动转 base64 | content 里 video_url + role=reference_video |

**实测（2026-10-22）**：

- 百炼 `wan2.7-videoedit` 用官方示例视频 + 指令「转换为黏土风格」跑通，5.0s / 1280×720 /
  H.264 + 音轨，输出 2.09 MB；提交→34 次轮询→下载共 384 秒。抽帧确认画面真的变成黏土质感。
- 火山方舟的 **Files API 上传实测可用**（`POST /api/v3/files`，`purpose=user_data`，
  返回 `file-2026xxxx-xxxxx`，几秒内 status 从 processing 变 active，不需要开通视频模型）。
  但本机账号的 Seedance 2.5 / 2.0 / fast / mini **全部返回 `ModelNotOpen`**，
  1.0 系列返回 `InvalidEndpointOrModel.NotFound`，所以"file id 还是 asset:// 引用"这一层还无法验证——
  请求在模型开通检查那一步就被拦下了。代码已做成两种写法依次尝试，开通后第一次跑就能确定。

不可用的三家（别白试）：智谱 CogVideoX、腾讯 HY-Video、百度千帆都是图生视频，不吃视频输入。

## 模型开通（不是所有模型都能直接调）

拿到 Key 只解决"你是谁"，能不能调某个模型还取决于**该账号有没有开通这个模型**。
开通与没开通的表现各不相同：

| 平台 | 未开通时的报错 | 开通入口 |
|---|---|---|
| 火山方舟 | `404 ModelNotOpen ... has not activated the model doubao-seedance-2-5-260628` | 方舟「开通管理」页 `ark.volcengine.com/region:cn-beijing/openManagement`，找到模型点「开通服务」，勾「全选」+「自动开通新增模型」 |
| 阿里百炼 | 模型不存在 / 权限错误（如 `wan2.7-videoedit`） | 百炼「模型广场」北京地域 `bailian.console.aliyun.com/cn-beijing/model/market`，模型详情点「立即开通」 |
| 腾讯混元 | `402 No free trial quota is available ... postpaid billing is not enabled` | TokenHub 控制台 → 在线推理 → 视觉模型，操作列点「启用后付费」 |
| 智谱 GLM | 429 限流（免费档） | 无需开通，换付费档（glm-4.6v / cogview-3 / cogvideox-3） |
| 百度千帆 | 权限不足 / 模型不存在 | 平台默认开通；检查 Key 的资源范围是否含对应 appid |
| MiniMax | `402 insufficient balance` 或 `base_resp.status_code=1008` | 无需开通，充值即可 |

程序做了两件事省事：
1. 「平台密钥」每行的「获取教程」对话框里，除操作步骤、注意事项外，新增**模型开通**区块：
   什么情况会用到、去哪点哪个按钮、官方注意事项，底部一个直达按钮。
2. 任务失败时按错误码给建议（`core/error_hint.py`），弹窗和运行日志都会写：
   "这个模型没有在「火山方舟」账号里开通。开通入口：方舟「开通管理」页 → 找到该模型 → 点「开通服务」"，
   并附控制台链接。不再只丢一行 404。

**注意**：火山方舟的 Files API 上传**不需要**开通模型，只有真正生成才需要。
所以哪怕视频模型没开通，上传这一步也能成功——不要把"上传成功"当成"能生成"。

## 使用流程

1. 点标题栏右侧「平台密钥」→ 六家平台的 Key 在同一页填好，逐行「保存」或「全部保存」
   - 每行有「获取教程」：打开该平台的官方获取步骤（4–5 步操作 + 3 条注意事项 + 官方文档链接）
   - 每行有「打开控制台」：直达取 Key 的页面
2. 标题栏左侧下拉选择「当前调用哪一家」；`密钥 n/6` 表示已配置几家
3. 三个分页做任务（模型下拉列出该能力可用的**全部**模型，「ID · 说明」，可直接选也可手输）：
   - 图像理解：选图（可多张）+ 提问 → 结果可另存 txt
   - 图像生成：提示词 / 参考图（图生图）/ 尺寸 / 数量 / 种子 → 缩略图在页内
   - 视频生成：提示词 / 首帧图 / 时长 / 分辨率 / 轮询间隔与最长等待 → 完成后可打开视频
4. 运行日志在**独立窗口**：标题栏「运行日志」打开，可筛选级别、复制、另存、清空、打开日志目录；
   每次请求的方法、URL、脱敏后的请求体（图片 base64 会折叠成「<N 字符的图片数据已省略>」）、
   响应码、耗时、平台原始错误都在里面。关掉窗口只是隐藏，任务继续记录，再打开还能看历史
5. 主界面底部只留一行状态（当前状态 + 最后一条日志摘要），任务空间更大

## 各平台 Key 怎么拿（教程内置）

界面里点「获取教程」看详细步骤，摘要如下（步骤与注意事项均取自各平台官方文档，链接见每行的官方文档页）：

| 平台 | 入口 | 最容易踩的点 |
|---|---|---|
| 火山方舟 | 方舟控制台 → API Key 管理 | 2026-09-17 12:00 后新建的 Key 是新明文格式；地域固定 cn-beijing |
| 阿里百炼 | 百炼控制台 → API Key（右上角先选地域） | 每个地域的 Key 与域名独立，不能跨地域混用 |
| 腾讯混元 | TokenHub 控制台 → API Key 管理 | 走 TokenHub，老平台已停止新增模型；Key 长期有效，建议按用途分开建 |
| 智谱 GLM | BigModel → API Keys | 个人/团队/模型标准 API 的 Key 分开管理互不通用，这里要用「模型标准 API」 |
| 百度千帆 | 控制台 → 安全认证 → API Key | 创建时要选「千帆 ModelBuilder」并配置资源（appid）；Key 形如 bce-v3/... |
| MiniMax | 开放平台 → 接口密钥 | 按量付费用「接口密钥」，M Plan 的「订阅 Key」不通用 |

## 窗口操作

- 拖动标题栏移动窗口；双击标题栏最大化/还原
- 右下角三角抓手可调整窗口大小
- 最大化是「铺满工作区」实现，不会盖住任务栏；代价是不支持 Windows 贴边分屏（Snap）

## 外观实现

- 背景：Win11 22H2+ 用 DWM `SYSTEMBACKDROP_TYPE = Acrylic`（真透出桌面模糊）
  → 失败回退 Mica → 再失败回退 `SetWindowCompositionAttribute` → 最后回退实底
  实际生效方式写在启动日志第一屏（例：`玻璃背景：Win11 亚克力（DWM SystemBackdrop）`）
- **窗口不能开 `WA_TranslucentBackground`**：那会变成 layered window，而 Win11 的 DWM
  SystemBackdrop 只在非 layered 窗口上绘制 —— 开了就是"API 调用成功但看不到模糊"。
  背景透明靠 QSS 让 QWidget 不画底，由 DWM 在窗口后面画模糊，再叠一层白 tint 保证文字可读。
- 按钮：白渐变 + 白高光描边 + 底部暗边（模拟玻璃厚度）；主操作按钮是蓝色玻璃
- 面板/输入框：淡蓝灰细描边（纯白描边在浅色亚克力上会看不见，界面会糊成一片）

## 各平台的差异（程序已处理）

| 平台 | 图像理解 | 图像生成 | 视频生成 |
|---|---|---|---|
| 火山方舟 | 同步 | 同步 | 异步任务 `contents/generations/tasks`，10s 轮询 |
| 阿里百炼 | 同步 | 同步（`multimodal-generation`） | 异步 `video-synthesis`（必须带 `X-DashScope-Async: enable`），15s |
| 腾讯混元 | 同步 | 同步，两个端点（`hy-image-v3.5-preview` / `hy-image-v3`） | 异步 `wand/hunyuan-video`，3–5s |
| 智谱 GLM | 同步 | 同步 | 异步 `videos/generations` → `async-result/{id}`，5s |
| 百度千帆 | 同步 | 同步（`/v2/images/generations`） | 两套：蒸汽机 `musesteamer-*` 与自研 K 系列，按模型名自动选路 |
| MiniMax | 同步（OpenAI 兼容） | 同步，自有协议 `/v1/image_generation` | 异步 `/v2/video_generation` → `/v2/query/…`，10s |

坑位（都已在代码里处理）：
- MiniMax 鉴权失败也返回 HTTP 200，真实错误在 `base_resp.status_code`（1004 = login fail）
- 千帆视频两套 API 互不兼容，按模型名前缀选路
- 腾讯生图两个端点返回结构不同：`choices[0].delta.image.url` vs `data[].url`
- 百炼默认走 `dashscope.aliyuncs.com`；若账号被要求用业务空间域名，改 `core/adapters.py` 的 `BL_BASE`

## 模型清单

下拉框按平台 + 能力列出该平台当前可调的全部模型，每项带档位说明（旗舰/轻量/免费/三方/即将下线）。当前收录：

| 平台 | 图像理解 | 图像生成 | 视频生成 |
|---|---|---|---|
| 火山方舟 | 6（Seed 2.1 Pro/Lite/Turbo、Evolving、2.0 Pro、1.6 Vision） | 5（Seedream 5.0 Pro/Flash/标准/Lite、4.5） | 6（Seedance 2.5/2.0/Fast/Mini/1.0 Pro/1.0 Lite） |
| 阿里百炼 | 5（qwen3.8 Max/Flash、3.7 Plus、qwen3-vl Plus/Max） | 4（qwen-image 3.0 Pro/2.1 Pro、wan2.7 Pro/2.7） | 7（wan3.0 Video/Prime、wan2.7 t2v/i2v/r2v/videoedit、2.6 t2v） |
| 腾讯混元 | 4（HY Vision 2.0、1.5 Thinking、Vision Video、优图 VITA） | 8（Hy-Image 3.5/3.0 + Seedream/可灵/WAND/Vidu 三方） | 1（Hy-Video 1.5） |
| 智谱 GLM | 8（GLM-4.6V/Flash、5.3 Flash/FlashX、5V-Turbo、4.5V、4V-Flash、OCR） | 4（GLM-Image、CogView-4/4-250304/3-Flash） | 3（CogVideoX-3/2/Flash） |
| 百度千帆 | 4（文心 5.0、ERNIE 4.5 Turbo VL、Qwen3-VL-32B、DeepSeek-VL2） | 4（Qwen-Image、ERNIE Image Turbo、蒸汽机 Air Image、Qwen-Image-Edit） | 7（K3.0/K2.6/K2.5-Turbo、蒸汽机 2.1/2.0 Pro/Turbo+Audio/Lite） |
| MiniMax | 2（M3.1 Flash、M3） | 2（image-01、image-01-live） | 2（H3、H3-Max） |

只收录「程序已实现调用路径」的模型；平台上线新模型时，直接在下拉框里手输模型 ID 即可，不用改代码。

## 已验证 / 未验证

**已验证（真实执行）**
- 18 个端点全部用真实 HTTP 打通过：401 或 MiniMax 业务码 1004（说明 URL、鉴权头、请求结构正确）
- 后台线程链路：进度 → 请求日志 → 响应日志 → 失败原因（含平台原始错误体）
- 界面：启动、三页渲染、玻璃背景生效方式（dwm-acrylic）、伪最大化铺满工作区不遮任务栏、还原、
  密钥界面六行一屏完整显示
- 入口 `app.py` 真实启动后系统能识别到窗口，关闭走正常退出

**真实 Key 实测（2026-10-22，五家各三条能力）**

| 平台 | 图像理解 | 图像生成 | 视频生成 |
|---|---|---|---|
| 火山方舟 | OK（Seed 2.1 Pro / Lite） | OK（Seedream 5.0 Pro 44s、Flash 18s，2496×1664） | 未测（成本） |
| 阿里百炼 | OK（qwen3.8-flash 2.1s） | OK（wan2.7-image 18s、qwen-image-3.0-pro 54s） | 未测（成本） |
| 腾讯混元 | OK（hy-vision-2.0-instruct 4.4s） | ✗ 402 无免费额度且未开后付费 | 未测 |
| 智谱 GLM | OK（glm-4.6v 4.4s；免费 flash 常 429） | OK（cogview-3-flash 8.7s，免费） | OK（cogvideox-3 全链路：提交→29 次轮询→下载 2.2MB，238s） |
| MiniMax | ✗ 402 余额不足 | ✗ 402 余额不足 | 未测 |
| 百度千帆 | 未配置 Key | — | — |

实测中修掉的问题：
- 火山生图曾报 400：`sequential_image_generation is not supported`——原因是 n=1 也传了多图参数。已改为只在 n>1 时提示、不再传参（该系列一次只出 1 张）
- 模型清单移除了实测 404 的 `doubao-seedream-5-0-260128`、`doubao-seedream-4-5-251128`
- 智谱免费档（*-flash）在模型说明里标注了「实测常被限流」

**仍未验证**
- 火山 / 百炼 / 腾讯 / MiniMax 的视频生成（单条 5s 会产生可见费用，需要时单独跑 test_video_real.py）
- 各家对尺寸/时长参数的完整接受范围（代码做了就近映射，最终以平台返回为准）

## 自检脚本

    python probe_endpoints.py    # 18 个端点连通性（无效 Key，零成本）
    python test_task_flow.py     # 后台线程与错误展示链路
    python smoke_glass.py        # 玻璃界面：三页 + 最大化 + 密钥界面截图到 logs\

## 文件结构

    app.py                    入口（单实例、全局异常兜底、异常写 logs\）
    core/config.py            Key 与模型记忆（%APPDATA%\AI多模态控制台\config.json）
    core/net.py               请求封装：超时、重试、Key 脱敏、日志
    core/adapters.py          六家平台的 HTTP 实现（一家一个函数，docstring 标了官方文档）
    core/providers.py         平台注册表 + 统一入口 + 模型清单
    core/tasks.py             QThread 后台任务
    ui/main_window.py         主窗口（玻璃 + 三页 + 运行日志）
    ui/key_manager.py         六家 Key 集中管理界面
    ui/frameless.py           自绘标题栏、拖动、伪最大化
    ui/win_effects.py         DWM 亚克力 / 圆角（ctypes 声明齐全，见注释里的闪退原因）
    ui/style.py               磨砂玻璃主题样式表
    output\                   产物（图片 img_平台_时间戳.png、视频 vid_平台_时间戳.mp4）
    logs\                     运行日志、崩溃记录、自检截图
