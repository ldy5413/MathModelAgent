from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import get_writer_prompt
from app.schemas.enums import CompTemplate, FormatOutPut
from app.tools.openalex_scholar import OpenAlexScholar
from app.utils.log_util import logger
from app.services.redis_manager import redis_manager
from app.schemas.response import SystemMessage, WriterMessage
import json
from app.core.functions import writer_tools
from icecream import ic
from app.schemas.A2A import WriterResponse
from app.services.task_control import TaskControl


# 长文本
# TODO: 并行 parallel
# TODO: 获取当前文件下的文件
# TODO: 引用cites tool
class WriterAgent(Agent):  # 同样继承自Agent类
    def __init__(
        self,
        task_id: str,
        model: LLM,
        max_chat_turns: int = 10,  # 添加最大对话轮次限制
        comp_template: CompTemplate = CompTemplate,
        format_output: FormatOutPut = FormatOutPut.Markdown,
        scholar: OpenAlexScholar = None,
        max_memory: int = 25,  # 添加最大记忆轮次
    ) -> None:
        super().__init__(task_id, model, max_chat_turns, max_memory)
        self.format_out_put = format_output
        self.comp_template = comp_template
        self.scholar = scholar
        self.is_first_run = True
        self.system_prompt = get_writer_prompt(format_output)
        self.available_images: list[str] = []

    async def run(
        self,
        prompt: str,
        available_images: list[str] = None,
        sub_title: str = None,
    ) -> WriterResponse:
        """
        执行写作任务
        Args:
            prompt: 写作提示
            available_images: 可用的图片相对路径列表（如 20250420-173744-9f87792c/编号_分布.png）
            sub_title: 子任务标题
        """
        logger.info(f"subtitle是:{sub_title}")

        if self.is_first_run:
            self.is_first_run = False
            await self.append_chat_history(
                {"role": "system", "content": self.system_prompt}
            )

        if available_images:
            self.available_images = available_images
            # 拼接成完整URL
            image_list = ",".join(available_images)
            image_prompt = f"\n可用的图片链接列表：\n{image_list}\n请在写作时适当引用这些图片链接。采用markdown语法插入图片，例如： ![描述性文字](图片链接) 。\n"
            logger.info(f"image_prompt是:{image_prompt}")
            prompt = prompt + image_prompt

        logger.info(f"{self.__class__.__name__}:开始:执行对话")
        self.current_chat_turns += 1  # 重置对话轮次计数器

        await self.append_chat_history({"role": "user", "content": prompt})

        # 工具循环：允许多次搜索，直到模型输出正文
        max_tool_rounds = 3
        footnotes = []

        def _looks_like_query_json(text: str) -> str | None:
            """如果文本是 {"query": "..."} 结构，返回 query 文本，否则返回 None"""
            try:
                data = json.loads(text)
                if isinstance(data, dict) and isinstance(data.get("query"), str):
                    return data["query"].strip()
            except Exception:
                return None
            return None

        rounds = 0
        while True:
            await TaskControl.wait_if_paused(self.task_id)
            # 获取历史消息用于本次对话
            response = await self.model.chat(
                history=self.chat_history,
                tools=writer_tools,
                tool_choice="auto",
                agent_name=self.__class__.__name__,
                sub_title=sub_title,
            )

            msg = response.choices[0].message

            # 1) 如果模型通过 function calling 触发搜索
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                logger.info("检测到工具调用")
                tool_call = msg.tool_calls[0]
                tool_id = tool_call.id
                if tool_call.function.name == "search_papers":
                    logger.info("调用工具: search_papers")
                    await redis_manager.publish_message(
                        self.task_id,
                        SystemMessage(content=f"写作手调用{tool_call.function.name}工具"),
                    )

                    query = json.loads(tool_call.function.arguments)["query"]

                    await redis_manager.publish_message(
                        self.task_id,
                        WriterMessage(
                            input={"query": query},
                        ),
                    )

                    # 更新对话历史 - 添加助手的响应
                    await self.append_chat_history(msg.model_dump())
                    ic(msg.model_dump())

                    try:
                        papers = await self.scholar.search_papers(query)
                    except Exception as e:
                        error_msg = f"搜索文献失败: {str(e)}"
                        logger.error(error_msg)
                        return WriterResponse(
                            response_content=error_msg, footnotes=footnotes
                        )

                    papers_str = self.scholar.papers_to_str(papers)
                    logger.info(f"搜索文献结果\n{papers_str}")
                    await self.append_chat_history(
                        {
                            "role": "tool",
                            "content": papers_str,
                            "tool_call_id": tool_id,
                            "name": "search_papers",
                        }
                    )

                    # 给出明确指令：使用上述结果写作，不要再输出查询 JSON
                    follow_up = (
                        "请基于上述文献结果撰写目标小节，输出纯 Markdown 文本；"
                        "如果没有检索到合适文献，也请继续完成写作并保留占位说明。"
                        "不要再输出 {\"query\": ...} 之类的 JSON；如需再次检索，请直接调用 search_papers 工具。"
                    )
                    await self.append_chat_history({"role": "user", "content": follow_up})

                    rounds += 1
                    if rounds >= max_tool_rounds:
                        logger.info("达到最大工具交互轮次，停止继续检索")
                        break
                    # 继续下一轮
                    continue

            # 2) 未触发函数调用，可能直接输出正文，或输出 {"query": ...}
            response_content = msg.content or ""
            inferred_query = _looks_like_query_json(response_content)
            if inferred_query and rounds < max_tool_rounds:
                # 将其视为再次检索的意图
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(
                        content="检测到写作手输出检索意图 JSON，自动触发 search_papers 并继续写作"
                    ),
                )

                # 把“JSON检索意图”作为助手消息加入历史，随后以工具响应的方式补充
                await self.append_chat_history({
                    "role": "assistant",
                    "content": response_content,
                })

                try:
                    papers = await self.scholar.search_papers(inferred_query)
                except Exception as e:
                    error_msg = f"搜索文献失败: {str(e)}"
                    logger.error(error_msg)
                    return WriterResponse(
                        response_content=error_msg, footnotes=footnotes
                    )

                papers_str = self.scholar.papers_to_str(papers)
                await self.append_chat_history(
                    {
                        "role": "tool",
                        "content": papers_str,
                        "tool_call_id": "inferred_query",
                        "name": "search_papers",
                    }
                )

                follow_up = (
                    "请基于上述文献结果撰写目标小节，输出纯 Markdown 文本；"
                    "不要再输出 JSON；如需再次检索，请直接调用 search_papers 工具。"
                )
                await self.append_chat_history({"role": "user", "content": follow_up})

                rounds += 1
                continue

            # 3) 模型已输出正文
            self.chat_history.append({"role": "assistant", "content": response_content})
            logger.info(f"{self.__class__.__name__}:完成:执行对话")
            return WriterResponse(response_content=response_content, footnotes=footnotes)
        self.chat_history.append({"role": "assistant", "content": response_content})
        logger.info(f"{self.__class__.__name__}:完成:执行对话")
        return WriterResponse(response_content=response_content, footnotes=footnotes)

    async def summarize(self) -> str:
        """
        总结对话内容
        """
        try:
            await self.append_chat_history(
                {"role": "user", "content": "请简单总结以上完成什么任务取得什么结果:"}
            )
            # 获取历史消息用于本次对话
            response = await self.model.chat(
                history=self.chat_history, agent_name=self.__class__.__name__
            )
            await self.append_chat_history(
                {"role": "assistant", "content": response.choices[0].message.content}
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"总结生成失败: {str(e)}")
            # 返回一个基础总结，避免完全失败
            return "由于网络原因无法生成详细总结，但已完成主要任务处理。"
