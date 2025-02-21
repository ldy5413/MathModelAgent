from core.Agents import CoderAgent
from core.WorkFlow import SolutionWorkFlow, WriteWorkFlow
from core.LLM import DeepSeekModel
from cli import UserInput
from utils.logger import log
from utils.io import input_content, output_content


def init_task():
    # === 初始化 ===
    # 设置控制台日志级别为 DEBUG
    log.set_console_level("WARNING")
    # 初始化日志系统，设置日志目录
    log.init(input_content.work_dirs["log"])


def start():
    init_task()
    # 加载配置文件
    deepseek_model = DeepSeekModel(**input_content.get_config())

    # 直接设置questions示例
    test_questions = {
        "title": "农作物种植优化问题",
        "background": """ 母亲是婴儿生命中最重要的人之一，她不仅为婴儿提供营养物质和身体保护，
 还为婴儿提供情感支持和安全感。母亲心理健康状态的不良状况，如抑郁、焦虑、
 压力等，可能会对婴儿的认知、情感、社会行为等方面产生负面影响。压力过大的
 母亲的可能会对婴儿的生理和心理发展产生负面影响，例如影响其睡眠等方面。
 附件给出了包括 390名 3 至 12 个月婴儿以及其母亲的相关数据。这些数
 据涵盖各种主题，母亲的身体指标包括年龄、婚姻状况、教育程度、妊娠时间、
 分娩方式，以及产妇心理指标CBTS（分娩相关创伤后应激障碍问卷）、EPDS
 （爱丁堡产后抑郁量表）、HADS（医院焦虑抑郁量表）和婴儿睡眠质量指标包
 括整晚睡眠时间、睡醒次数和入睡方式。
 请查阅相关文献，了解专业背景，根据题目数据建立数学模型，回答下列问
 题。""",
        "ques_count": 2,
        "ques1": """ 1. 许多研究表明，母亲的身体指标和心理指标对婴儿的行为特征和睡眠质
 量有影响，请问是否存在这样的规律，根据附件中的数据对此进行研究。""",
        "ques2": """ 2. 婴儿行为问卷是一个用于评估婴儿行为特征的量表，其中包含了一些关
 于婴儿情绪和反应的问题。我们将婴儿的行为特征分为三种类型：安静型、中等
 型、矛盾型。请你建立婴儿的行为特征与母亲的身体指标与心理指标的关系模型。
 数据表中最后有20组（编号391-410号）婴儿的行为特征信息被删除，请你判断
 他们是属于什么类型。""",
    }

    user_input = UserInput(
        data_folder_path="E:/Code/Set/Open/MathModelAgent/project/sample_data",
        bg_ques_all="原始问题文本...",
        model=deepseek_model,
        init_with_llm=False,  # 不使用LLM初始化
    )

    # 直接设置预定义的questions
    user_input.set_questions_directly(test_questions)
    input_content.set_user_input(user_input)

    coder_agent = CoderAgent(
        deepseek_model, work_dir=input_content.work_dirs["jupyter"]
    )

    solution_workflow = SolutionWorkFlow(coder_agent)
    solution_workflow.execute()

    write_workflow = WriteWorkFlow(model=deepseek_model)
    write_workflow.execute()

    output_content.data_recorder.print_summary()
    output_content.save_result()


if __name__ == "__main__":
    start()
