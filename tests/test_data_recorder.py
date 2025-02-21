import pytest
from utils.data_recorder import DataRecorder
from core.LLM import DeepSeekModel
from utils.common_utils import load_toml
import os
import json


def test_real_chat_completion_recording(tmp_path):
    """使用实际API测试聊天完成记录的序列化功能"""
    # 创建临时目录作为日志目录
    log_dir = tmp_path / "test_logs"
    os.makedirs(log_dir, exist_ok=True)

    # 初始化 DataRecorder
    recorder = DataRecorder(str(log_dir))

    # 加载配置并初始化模型
    config = load_toml("config/config.toml")
    model = DeepSeekModel(**config)

    # 构造一个简单的对话
    history = [
        {"role": "system", "content": "你是一个助手。"},
        {"role": "user", "content": "你好，请帮我计算 1+1 等于多少？"},
    ]

    # 实际调用API获取响应
    completion = model.chat(history=history, agent_name="CoderAgent")

    # 测试记录 ChatCompletion
    agent_name = "CoderAgent"
    recorder.append_chat_completion(completion, agent_name)

    # 验证 JSON 文件是否被创建
    json_path = os.path.join(str(log_dir), "chat_completion.json")
    assert os.path.exists(json_path)

    # 读取并验证 JSON 内容
    with open(json_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    # 验证基本结构
    assert agent_name in saved_data
    assert len(saved_data[agent_name]) == 1

    completion_data = saved_data[agent_name][0]
    assert "id" in completion_data
    assert "model" in completion_data
    assert completion_data["model"] == config["model"]

    # 验证 choices
    assert "choices" in completion_data
    choice = completion_data["choices"][0]
    assert "index" in choice
    assert "message" in choice
    assert "role" in choice["message"]
    assert "content" in choice["message"]
    assert choice["message"]["role"] == "assistant"

    # 验证 usage
    assert "usage" in completion_data
    assert "completion_tokens" in completion_data["usage"]
    assert "prompt_tokens" in completion_data["usage"]
    assert "total_tokens" in completion_data["usage"]

    # 验证 system_fingerprint
    assert "system_fingerprint" in completion_data


def test_real_chat_completion_with_tools(tmp_path):
    """测试带有工具调用的实际API响应记录"""
    log_dir = tmp_path / "test_logs"
    os.makedirs(log_dir, exist_ok=True)
    recorder = DataRecorder(str(log_dir))

    config = load_toml("config/config.toml")
    model = DeepSeekModel(**config)

    # 构造一个需要工具调用的对话
    history = [
        {"role": "system", "content": "你是一个助手。"},
        {"role": "user", "content": "请帮我写一段Python代码来计算1到100的和。"},
    ]

    # 定义工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "execute_code",
                "description": "Execute Python code",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The Python code to execute",
                        }
                    },
                    "required": ["code"],
                },
            },
        }
    ]

    # 实际调用API获取响应
    completion = model.chat(
        history=history, tools=tools, tool_choice="auto", agent_name="CoderAgent"
    )

    # 记录响应
    agent_name = "CoderAgent"
    recorder.append_chat_completion(completion, agent_name)

    # 验证JSON文件
    json_path = os.path.join(str(log_dir), "chat_completion.json")
    with open(json_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    completion_data = saved_data[agent_name][0]

    # 验证工具调用
    choice = completion_data["choices"][0]
    assert "tool_calls" in choice["message"]
    if choice["message"]["tool_calls"]:
        tool_call = choice["message"]["tool_calls"][0]
        assert "id" in tool_call
        assert "type" in tool_call
        assert "function" in tool_call
        assert "name" in tool_call["function"]
        assert "arguments" in tool_call["function"]
        assert tool_call["function"]["name"] == "execute_code"


def test_token_usage_tracking(tmp_path):
    """测试 token 使用统计功能"""
    log_dir = tmp_path / "test_logs"
    os.makedirs(log_dir, exist_ok=True)
    recorder = DataRecorder(str(log_dir))

    config = load_toml("config/config.toml")
    model = DeepSeekModel(**config)

    # 构造两个简单的对话
    histories = [
        [
            {"role": "system", "content": "你是一个助手。"},
            {"role": "user", "content": "1+1等于多少？"},
        ],
        [
            {"role": "system", "content": "你是一个助手。"},
            {"role": "user", "content": "2+2等于多少？"},
        ],
    ]

    agent_name = "CoderAgent"

    # 发送两次请求
    for history in histories:
        completion = model.chat(history=history, agent_name=agent_name)
        recorder.append_chat_completion(completion, agent_name)

    # 验证 token_usage.json 文件
    json_path = os.path.join(str(log_dir), "token_usage.json")
    assert os.path.exists(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        usage_data = json.load(f)

    # 验证数据结构
    assert agent_name in usage_data
    agent_usage = usage_data[agent_name]

    # 验证字段
    assert "completion_tokens" in agent_usage
    assert "prompt_tokens" in agent_usage
    assert "total_tokens" in agent_usage
    assert "chat_count" in agent_usage

    # 验证计数
    assert agent_usage["chat_count"] == 2
    assert agent_usage["total_tokens"] > 0
    assert agent_usage["completion_tokens"] > 0
    assert agent_usage["prompt_tokens"] > 0

    # 验证总数关系
    assert agent_usage["total_tokens"] == (
        agent_usage["completion_tokens"] + agent_usage["prompt_tokens"]
    )

    # 测试打印摘要
    recorder.print_summary()


def test_cost_calculation(tmp_path):
    """测试费用计算功能"""
    log_dir = tmp_path / "test_logs"
    os.makedirs(log_dir, exist_ok=True)
    recorder = DataRecorder(str(log_dir))

    # 测试不同模型的费用计算
    test_cases = [
        {
            "model": "gpt-4",
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "expected_cost": 0.06,  # (1000 * 0.03 + 500 * 0.06) / 1000
        },
        {
            "model": "gpt-3.5-turbo",
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "expected_cost": 0.00125,  # (1000 * 0.0005 + 500 * 0.0015) / 1000
        },
        {
            "model": "unknown-model",
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "expected_cost": 0.00015,  # 使用默认价格
        },
    ]

    for case in test_cases:
        cost = recorder.calculate_cost(
            case["model"], case["prompt_tokens"], case["completion_tokens"]
        )
        assert abs(cost - case["expected_cost"]) < 0.00001, (
            f"Cost calculation failed for {case['model']}"
        )


def test_token_usage_and_cost_tracking(tmp_path):
    """测试 token 使用统计和费用追踪功能"""
    log_dir = tmp_path / "test_logs"
    os.makedirs(log_dir, exist_ok=True)
    recorder = DataRecorder(str(log_dir))

    config = load_toml("config/config.toml")
    model = DeepSeekModel(**config)

    # 构造两个简单的对话
    histories = [
        [
            {"role": "system", "content": "你是一个助手。"},
            {"role": "user", "content": "1+1等于多少？"},
        ],
        [
            {"role": "system", "content": "你是一个助手。"},
            {"role": "user", "content": "2+2等于多少？"},
        ],
    ]

    agent_name = "CoderAgent"
    initial_total_cost = recorder.total_cost

    # 发送两次请求
    for history in histories:
        completion = model.chat(history=history, agent_name=agent_name)
        recorder.append_chat_completion(completion, agent_name)

    # 验证 token_usage.json 文件
    json_path = os.path.join(str(log_dir), "token_usage.json")
    assert os.path.exists(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        usage_data = json.load(f)

    # 验证数据结构和基本字段
    assert agent_name in usage_data
    agent_usage = usage_data[agent_name]
    required_fields = [
        "completion_tokens",
        "prompt_tokens",
        "total_tokens",
        "chat_count",
        "cost",
    ]
    for field in required_fields:
        assert field in agent_usage

    # 验证计数和费用
    assert agent_usage["chat_count"] == 2
    assert agent_usage["total_tokens"] > 0
    assert agent_usage["cost"] > 0
    assert recorder.total_cost > initial_total_cost

    # 验证总数关系
    assert agent_usage["total_tokens"] == (
        agent_usage["completion_tokens"] + agent_usage["prompt_tokens"]
    )

    # 测试打印摘要
    recorder.print_summary()
