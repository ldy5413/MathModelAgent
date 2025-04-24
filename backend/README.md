ENV=DEV uvicorn app.main:app --reload
ENV=DEV uvicorn app.main:app --host 0.0.0.0 --port 8000 --ws-ping-interval 60 --ws-ping-timeout 120

wscat -c ws://127.0.0.1:8000/task/20250424-195735-a710fb83
- 绘图
napki
输出 draw.io 格式