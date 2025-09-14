from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import get_modeler_prompt
from app.schemas.A2A import CoordinatorToModeler, ModelerToCoder
from app.utils.log_util import logger
from app.config.setting import settings
import json
from icecream import ic
from app.services.task_control import TaskControl

# TODO: 提问工具tool


class ModelerAgent(Agent):  # 继承自Agent类
    def __init__(
        self,
        task_id: str,
        model: LLM,
        max_chat_turns: int = 30,  # 添加最大对话轮次限制
        language: str | None = None,
    ) -> None:
        super().__init__(task_id, model, max_chat_turns)
        self.system_prompt = get_modeler_prompt(language)

    async def run(self, coordinator_to_modeler: CoordinatorToModeler) -> ModelerToCoder:
        """根据 Coordinator 输出生成建模方案（带自动重试与字段校验）"""
        await self.append_chat_history({"role": "system", "content": self.system_prompt})
        await self.append_chat_history(
            {"role": "user", "content": json.dumps(coordinator_to_modeler.questions)}
        )

        # 期望键：EDA + 每个 quesN + sensitivity_analysis
        ques_keys = [k for k in coordinator_to_modeler.questions.keys() if k.startswith("ques") and k != "ques_count"]
        required_keys = set(["eda", "sensitivity_analysis", *ques_keys])

        last_error = ""
        for attempt in range(1, settings.MAX_RETRIES + 1):
            await TaskControl.wait_if_paused(self.task_id)
            response = await self.model.chat(
                history=self.chat_history,
                agent_name=self.__class__.__name__,
            )

            raw = response.choices[0].message.content or ""
            json_str = raw.replace("```json", "").replace("```", "").strip()
            if not json_str:
                last_error = "空输出"
            else:
                try:
                    data = json.loads(json_str)
                except Exception as e:
                    last_error = f"JSON 解析失败: {e}"
                else:
                    # 单层 JSON + 必要字段校验
                    if not isinstance(data, dict):
                        last_error = "输出不是 JSON 对象"
                    else:
                        missing = [k for k in required_keys if k not in data]
                        # 值必须是字符串
                        value_type_issue = [k for k, v in data.items() if not isinstance(v, str)]
                        if not missing and not value_type_issue:
                            ic(data)
                            return ModelerToCoder(questions_solution=data)
                        else:
                            parts = []
                            if missing:
                                parts.append("缺少字段: " + ", ".join(missing))
                            if value_type_issue:
                                parts.append("值需为字符串的键: " + ", ".join(value_type_issue))
                            last_error = "; ".join(parts)

            # 失败反馈，要求严格纠正
            fix_prompt = (
                "上一次的输出无效，原因："
                + last_error
                + "。请仅输出严格单层 JSON，不要包含解释或代码块围栏。键必须包含："
                + ", ".join(sorted(required_keys))
                + "；每个键的值为字符串。"
            )
            await self.append_chat_history({"role": "user", "content": fix_prompt})

        raise ValueError(f"ModelerAgent 多次尝试仍失败: {last_error}")
