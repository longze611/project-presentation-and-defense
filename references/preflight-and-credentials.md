# 启动测试、密钥窗口与全局配置

## 适用范围与顺序

只在实际需要新生图的制作任务启动时执行；修改本技能、纯文案、排版修复或只重建现有图片不触发弹窗、API调用或配置。先确认总页数和文案语言（可与能力测试并行），解析实际工具，再确定生图路径，随后编写逐页文案并取得确认。正式页面仍须等待文案确认。用户在当前任务已明确的页数、语言、API授权和跳过选择应延续，不重复询问。

启动测试只做一张不含论文内容的诊断图，不占用最终页数，保存在项目 `.build/preflight/`，不要混入正式 `images/Sxx.png`。有实际可解码的新图片、实际图像参考输入和本次时间戳，才记为通过；仅存在Key、能聊天、HTTP 200、模型列表、旧成功日志及 `--dry-run` 均不是通过。

## 1. 先测试当前可用路径

1. 发现并读取当前 `imagegen` 技能及工具。内置工具优先，内置模式无需API Key。选取本技能 `assets/references/b-method.png`，通过当前工具支持的图像输入机制提交；提示只生成“白底、两个蓝色矩形、一条箭头，无文字和标识”的低成本诊断图。工具需要上下文图时先打开原图，不能只传文件路径字符串冒充附件。
2. 实际检查返回图可显示/解码。返回成功但无法输入参考，只能说明文生图可用，参考迁移条件仍未满足。内置工具无模型参数时写 `model=unexposed`；测试证明该工具的图像能力，不证明后端恰为 `gpt-image-2`。用户要求严格可核实的模型时，说明限制，提供显式API路径。
3. 内置工具不可用或失败时，若同机全局配置已存在、记录了用户授权API路径且当前任务没有禁用API，使用下述 `probe` 读取共享配置并真实测试，无须再次让用户录Key。旧的 `validated_at` 仅是历史记录。
4. 没有可用路径则展示两个选择。可用文本：

   - **配置API，继续Image 2**：在本机窗口输入API Key；若使用中转站，同时填写该站base URL。将向所选服务提交密钥及测试参考图，可能产生API费用；测试成功后供本机后续对话复用。
   - **跳过Image 2，直接生成可编辑PPT**：明确提醒“跳过生图后，PPT的视觉效果和对参考风格的还原度可能下降”。用户选择后记为 `mode=direct-editable`。

用当前可用的问题工具收集选择，不能把沉默或超时视为选择API或跳过。没有内置工具时记录 `unavailable`，不是虚构一次失败调用。不自动换成其他生图模型。用户选择配置API就是对该路径的授权，不再为同一配置和诊断图反复请求确认。

## 2. 本机隐藏输入与实际验证

助手定位本技能目录后，使用装有 `openai`、`Pillow` 的Python，执行：

```bash
python /absolute/skill/scripts/image_access.py configure --output-dir /absolute/project/.build/preflight
```

`/absolute/skill` 指当前安装目录，不照抄旧机器路径。系统沙箱、网络或凭据库需要执行批准时，按环境规则申请该命令的访问，不让用户在聊天中重复提供密钥。

脚本行为：

- macOS使用原生系统窗口，Key输入隐藏；下一窗口明确要求中转站填写base URL。Linux有桌面、tkinter及Secret Service时使用本机窗口。官方默认 `https://api.openai.com/v1`；中转站填写其完整API根地址，通常以 `/v1` 结尾，不填网页首页或 `/images/edits` 端点。
- 用户输入的Key只保留在脚本内存、系统凭据库和生图子进程环境中。不得放到聊天、命令参数、代码、提示词、项目JSON、日志或截图中；不要用普通问题输入框代替隐藏输入框。
- 按窗口选定地址，通过原版 `imagegen/scripts/image_gen.py edit --model gpt-image-2` 提交真实参考图并实际生成、解码诊断图。脚本不实现自定义SDK请求，也不修改原版CLI。这里只验证参考输入接口可用，正式页面的风格质量仍须逐页检查。
- 成功后先写入系统凭据库、回读验证，再原子发布全局非敏感配置。取消、无效URL、401、权限/额度问题或未返回可解码图片都不能标为成功；旧配置保持不变。显示经过脱敏的错误类别，不转发可能含Key的原始响应。
- 保存成功后当前任务直接使用配置，无需等待用户再回复“已更新”；失败则让用户选择修正后重试或跳过，等待其选择，不无限重试。用户已经取消或拒绝配置时不反复弹窗。

没有桌面、GUI被阻止或凭据库不可用时，明确说明无法弹窗的原因，并给出在用户本机桌面终端运行同一 `configure` 命令的方式。脚本当前支持macOS Keychain及Linux Secret Service；其他系统须使用其可用的本机安全输入与系统凭据库方案，不能宣称脚本已经支持。不要退回让用户发送明文Key。

## 3. 全局作用域与跨对话复用

共享配置位于 `${CODEX_HOME:-~/.codex}/image-api/config.json`，与项目目录、当前shell和单个聊天无关。配置只含 `base_url`、`model`、用户API授权标记、验证时间及凭据库服务/账户引用，不含Key。macOS密钥存在Keychain，Linux存在Secret Service；全局目录权限700、配置权限600。

任何新旧对话调用本技能时，都从这个固定位置读取；不依赖 `export`、当前聊天注入的环境变量或重启应用。调用时读取系统凭据库，仅给原版CLI子进程设置匹配的 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。共享生图配置优先于无关的shell Key，避免把某站点Key配到另一站点。

```bash
# 仅检查配置存在，不读出密钥，也不代表生图通过
python /absolute/skill/scripts/image_access.py status

# 在新的制作任务中，实际测试已保存的API配置
python /absolute/skill/scripts/image_access.py probe --output-dir /absolute/project/.build/preflight

# 文案确认后：从全局凭据库加载，直接调用原版CLI生成正式页面
python /absolute/skill/scripts/image_access.py run -- edit \
  --image /absolute/skill/assets/references/b-method.png \
  --prompt-file /absolute/project/prompts/S06-v01.txt \
  --size 2048x1152 --quality high --no-augment \
  --out /absolute/project/images/S06.png
```

`run` 固定请求 `gpt-image-2`，不再传 `--model`；用重复的 `--image` 提交当前页真实参考与证据。它仅为凭据注入和CLI启动器，仍遵循 `imagegen` 当前CLI文档及API授权要求。逐页生成以保留真实图像输入，不用不透明的批任务覆盖模型。不要将Key拼到命令行或打印子进程环境。

“全局”指同一用户、同一机器、同一 `CODEX_HOME`，且调用本技能或显式读取这个共享配置的流程；不修改Codex聊天模型/登录配置，不自动给其他工具、设备或云端授权。Codex聊天可用不等于独立图像API可用。中转站收到 `model=gpt-image-2` 并返回图片也不能独立证明其后台模型身份，应记录请求模型和未验证的后端状态。

本任务只修改技能时，不为验证编辑而打开真实密钥窗口或发起付费生图。测试辅助脚本可使用隔离目录、模拟CLI及临时测试凭据，不接触用户真实Key。

## 4. 记录与跳过后的衔接

项目记录 `language`（`zh-CN` / `en` 或用户指定值）、`language_confirmed`、`generation_preflight`、`image_stage_decision`（`builtin` / `api` / `skip` / `not-required`）、`global_image_profile`。不要保存窗口输入或Key；诊断图报告不含密钥。

跳过后继续：语言与页数确认 → 逐页文案 → 用户审定 → 真实参考风格锁 → 原生对象布局 → Presentations制作 → 重叠/连线/事实检查。保留封面、目录、结尾等原有规则。没有生成图片时，不生成虚假的拆图来源；最终PPT预览明确标为渲染预览。若原本只要图片，先明确用户是否愿意改要可编辑PPT，不能擅自转交付类型。

官方说明参考：[图像生成](https://developers.openai.com/api/docs/guides/image-generation)、[API入门与Key环境变量](https://developers.openai.com/api/docs/quickstart)。这里的共享文件和凭据启动器是本技能提供的本机复用机制，不是Codex自带的全局模型开关；用户指定的 `gpt-image-2` 不因文档推荐其他模型而被替换。
