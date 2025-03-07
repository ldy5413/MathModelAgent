import gradio as gr


def update_markdown(text):
    # 返回更新后的 Markdown 内容
    return f"""
# 更新的 Markdown 内容

当前输入内容：**{text}**

- 长度：{len(text)} 字符
"""


with gr.Blocks() as demo:
    gr.Markdown("# Markdown 实时更新演示")

    with gr.Row():
        # 输入组件
        input_text = gr.Textbox(
            label="输入内容", placeholder="在这里输入内容...", show_label=False
        )

        # 输出 Markdown 组件
        md_output = gr.Markdown(
            "## 初始内容\n在此输入内容以更新此处显示", label="动态 Markdown"
        )

    # 绑定输入事件（每次输入时实时更新）
    input_text.input(fn=update_markdown, inputs=input_text, outputs=md_output)

    # 可选：添加清除按钮
    clear_btn = gr.Button("清空")

    def clear():
        return "", "## 内容已清空\n请输入新内容"

    clear_btn.click(fn=clear, outputs=[input_text, md_output])

if __name__ == "__main__":
    demo.launch()
