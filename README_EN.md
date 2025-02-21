<h1 align="center">🤖 MathModelAgent 📐</h1>
<p align="center">
    <img src="./docs/icon.png" height="250px">
</p>

<h4 align="center">
    An agent designed for mathematical modeling<br>
    Automatically complete mathematical modeling and generate a ready-to-submit paper.
</h4>

<br>

<h6><a href="README.md">简体中文</a> | English</h5>


## Vision:

Automatically generate an award-worthy mathematical modeling paper

## ✨ Features

- 🔍 Automatic problem analysis, mathematical modeling, code writing, error correction, and paper writing
- 💻 Local code interpreter
- 📝 Generate a well-formatted paper
- 🤝 Multi-agents: ~~modeling expert~~, coding expert (reflection module, local code interpreter), paper expert
- 🔄 Multi-llms: Different models for each agent

## 🚀 Future Plans

- [ ] Comprehensive tutorials and documentation
- [ ] Web service
- [ ] English support (MCM/ICM)
- [ ] LaTeX template integration
- [ ] Vision model integration
- [ ] Proper citation implementation
- [ ] More test cases
- [ ] Docker deployment
- [ ] User interaction (model selection, rewriting, etc.)
- [ ] Cloud integration for code interpreter (e.g., e2b providers)

After cloning the project, install the **Todo Tree** plugin to view all specific todo locations in the code

## Video Demo


## 📖 Usage Guide

1. Install Dependencies
```bash
git clone
pip install uv
uv sync # install dependencies
```
2. Configure Model
Copy `/config/config.toml.example` to `/config/config.toml` and fill in the model configuration

Recommend using models with strong capabilities and large parameter counts.

3. Run Tests and Start Project
```bash
uv run example.py # simple test to verify correct operation
uv run main.py # complete project
```

Results will be in the `/project/work_dir/` directory

## 🤝 Contribution

- Project is in **development stage** (I update when time permits), with frequent changes and some bugs that I'm working to fix.
- Issues and PRs are welcome
- For requirements, refer to Future Plans

## 📄 License

Not for commercial use. Contact me (author) for commercial purposes.

## 🙏 Reference
Thanks to the following projects:
- [OpenCodeInterpreter](https://github.com/OpenCodeInterpreter/OpenCodeInterpreter/tree/main)
- [TaskWeaver](https://github.com/microsoft/TaskWeaver)
- [Code-Interpreter](https://github.com/MrGreyfun/Local-Code-Interpreter/tree/main)
- [Latex](https://github.com/Veni222987/MathModelingLatexTemplate/tree/main)
