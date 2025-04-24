<h1 align="center">🤖 MathModelAgent 📐</h1>
<p align="center">
    <img src="./docs/icon.png" height="250px">
</p>
<h4 align="center">
    专为数学建模设计的 Agent<br>
    自动完成数学建模，生成一份完整的可以直接提交的论文。
</h4>

<h5 align="center">简体中文 | <a href="README_EN.md">English</a></h5>

## 🌟 愿景：

3 天的比赛时间变为 1 小时 <br> 
自动完整一份可以获奖级别的建模论文

<p align="center">
    <img src="./docs/webui.png">
</p>

## ✨ 功能特性

- 🔍 自动分析问题，数学建模，编写代码，纠正错误，撰写论文
- 💻 本地代码解释器
- 📝 生成一份编排好格式的论文
- 🤝 muti-agents: ~~建模手~~，代码手(反思模块，本地代码解释器)，论文手
- 🔄 muti-llms: 每个agent设置不同的模型
- 💰 成本低 agentless

## 🚀 后期计划

- [x] 添加并完成 webui、cli
- [ ] 完善的教程、文档
- [ ] 提供 web 服务
- [ ] 英文支持（美赛）
- [ ] 集成 latex 模板
- [ ] 接入视觉模型
- [ ] 添加正确文献引用
- [ ] 更多测试案例
- [ ] docker 部署
- [ ] 引入用户的交互（选择模型，重写等等）
- [ ] codeinterpreter 接入云端 如 e2b 等供应商..

clone 项目后，下载**Todo Tree**插件，可以查看代码中所有具体位置的 todo

## 视频demo

<video src="https://github.com/user-attachments/assets/10b3145a-feb7-4894-aaca-30d44bb35b9e"></video>

## 📖 使用教程

1. 安装依赖

```bash
git clone https://github.com/jihe520/MathModelAgent.git # 克隆项目
pip install uv # 推荐使用 uv 管理 python 项目
uv venv # 创建虚拟环境
uv sync # 安装依赖
```

2. 配置模型

复制`/config/config.toml.example`到`/config/config.toml`, 填写配置模型

推荐模型能力较强的、参数量大的模型。

3. 运行测试 和 启动项目

```bash
uv run example.py # 简单测试能否正确运行
uv run webui.py # 推荐: 启动 webui
uv run terminal.py # 启动终端项目
```

运行的结果在`/project/work_dir/`目录下

## 🤝 贡献

- 项目处于**开发阶段**（我有时间就会更新），变更较多，还存在许多 Bug，我正着手修复。
- 欢迎提交 issues 和 PRs
- 需求参考 后期计划

## 📄 版权License

请勿商业用途，商业用途联系我（作者）

## 🙏 Reference

Thanks to the following projects:
- [OpenCodeInterpreter](https://github.com/OpenCodeInterpreter/OpenCodeInterpreter/tree/main)
- [TaskWeaver](https://github.com/microsoft/TaskWeaver)
- [Code-Interpreter](https://github.com/MrGreyfun/Local-Code-Interpreter/tree/main)
- [Latex](https://github.com/Veni222987/MathModelingLatexTemplate/tree/main)


## 联系

有问题可以进群问

<img src="./docs/qq.jpg" height="400px">