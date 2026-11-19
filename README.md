# Project Presentation and Defense

用于 Codex 的蓝白风格学术 PPT 技能，参考两份真实报告的配色、版式，以及流程图和分点表达方式，适合科研项目、开题答辩、文献汇报、组会和学术会议。

输入是一篇论文或项目材料，生成效果如这份完整的 [12 页英文示例 PPT](examples/smart-contract-fuzzers-12-en-final.pptx) 所示。示例论文为 Wu et al. 的 [Are We There Yet? Unraveling the State-of-the-Art Smart Contract Fuzzers](https://arxiv.org/abs/2402.02973)（ICSE 2024）。

## 安装方式

### 方式一：下载 ZIP，让 Codex 安装

[下载本仓库 ZIP](https://github.com/longze611/academic-blue-defense/archive/refs/heads/main.zip)，将文件提供给 Codex，并发送：

```text
请将这个 ZIP 中的 academic-blue-defense 技能安装到我的 Codex 技能目录。
```

### 方式二：复制 Git 链接，让 Codex 安装

将下面的内容发送给 Codex：

```text
请从这个 Git 仓库安装 academic-blue-defense 技能：
https://github.com/longze611/academic-blue-defense.git
```

安装后重新打开 Codex 会话，或按当前客户端方式刷新技能列表。

## 使用方式

向 Codex 提供论文 PDF 或项目材料，并发送：

```text
请使用 $academic-blue-defense，根据这份材料制作 12 页中文学术汇报 PPT。
先给我逐页结构和文案，确认后再制作。
```

技能会先确认页数与文案语言，并测试生图能力。文案确认后，按内置参考生成整页图片，再重建可编辑 PPT。项目报告包含封面、目录和结尾，均计入总页数。

生图不可用时，可选择在本机窗口配置 API，或跳过生图直接制作可编辑 PPT；跳过后，视觉效果和参考风格还原度可能下降。也支持只生成图片，或重建已有定稿图片。

## 运行条件

- Codex 能读取输入材料和本技能的参考素材。
- 生图阶段需要可用的 `imagegen` 技能及支持参考图输入的工具；可编辑制作需要 `Presentations` 技能，以及 PPTX 导出和逐页渲染工具。
- API 路径需要可访问的图像生成服务，可能产生费用。密钥通过本机隐藏输入窗口配置，不在聊天中填写；配置脚本支持 macOS Keychain 和具备 Secret Service 的 Linux 桌面。
- PDF 阅读与图表裁切需要可用的 PDF 工具；辅助脚本使用 Python 3，图像 API 路径还需 `openai` 和 Pillow。

本仓库提供技能指令、参考素材与辅助脚本，实际生图、PPT 制作和渲染由所在 Codex 环境的工具完成。

## 交付内容

所选流程对应的图片套件、可编辑 PPTX、渲染预览和制作源文件。文字、表格和流程结构按对象重建；照片、真实截图和部分科研图像可保留为图片，并说明可编辑范围。

## 致谢与来源

风格参考及来源记录见 [参考报告研究](references/source-study.md)和[素材来源](assets/source-provenance.json)。相关报告与论文素材的权利归各自权利人所有。本技能借鉴其视觉与表达方法，不代表原作者或机构的认可。
