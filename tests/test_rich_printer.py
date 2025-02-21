import pytest
from utils.RichPrinter import RichPrinter


def test_rich_printer_basic():
    """测试 RichPrinter 的基本功能"""

    # 测试工作流开始和结束
    RichPrinter.workflow_start()
    RichPrinter.workflow_end()

    # 测试不同类型的消息打印
    RichPrinter.success("这是一条成功消息")
    RichPrinter.error("这是一条错误消息")
    RichPrinter.warning("这是一条警告消息")

    # 测试带自定义参数的消息
    RichPrinter.success("自定义标题的成功消息", title="自定义标题")
    RichPrinter.error("自定义颜色的错误消息", color="bright_red")

    # 测试表格打印
    headers = ["编号", "姓名", "得分"]
    rows = [[1, "张三", 95], [2, "李四", 88], [3, "王五", 92]]
    RichPrinter.table(headers=headers, rows=rows, title="学生成绩表")

    # 测试 Agent 消息
    RichPrinter.print_agent_msg("正在生成代码...", "CoderAgent")
    RichPrinter.print_agent_msg("正在撰写论文...", "WriterAgent")


def test_rich_printer_error_cases():
    """测试错误情况"""

    # 测试未知 Agent 名称
    with pytest.raises(ValueError):
        RichPrinter.print_agent_msg("测试消息", "UnknownAgent")
