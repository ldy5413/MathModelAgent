# websocket-redis-manager

## 项目简介
`websocket-redis-manager` 是一个基于 FastAPI 的项目，旨在提供一个高效的 WebSocket 和 Redis 管理解决方案。该项目封装了 WebSocket 和 Redis 的操作，使得在应用程序中使用它们变得更加简单和高效。

## 目录结构
```
websocket-redis-manager
├── src
│   ├── core
│   ├── models
│   ├── handlers
│   ├── config
│   ├── utils
│   └── main.py
├── tests
├── requirements.txt
└── pyproject.toml
```

## 安装依赖
在项目根目录下运行以下命令以安装所需的依赖：
```
pip install -r requirements.txt
```

## 使用说明
1. **启动应用程序**
   在项目根目录下，运行以下命令启动 FastAPI 应用：
   ```
   uvicorn src.main:app --reload
   ```

2. **WebSocket 连接**
   通过 WebSocket 客户端连接到 `ws://localhost:8000/task/{task_id}`，其中 `{task_id}` 是您要连接的任务 ID。

3. **Redis 消息发布**
   使用 `RedisManager` 类发布消息到特定的 Redis 频道。

## 贡献
欢迎任何形式的贡献！请提交问题或拉取请求。

## 许可证
本项目采用 MIT 许可证。