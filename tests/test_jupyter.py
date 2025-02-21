import pytest
from tools.jupyter_backend import JupyterKernel


def test_jupyter_notebook():
    jupyter_kernel = JupyterKernel("work_dir")
    code = """
import matplotlib.pyplot as plt
plt.plot([1,2,3], [4,5,6])
plt.savefig('aa.png')  # 必须保存文件而非直接show()
print(2 + 3 * 4)
"""
    text_to_gpt, content_to_display, error_occurred, error_message = (
        jupyter_kernel.execute_code(code)
    )
    print(text_to_gpt)
    print(content_to_display)
    print(error_occurred)
    print(error_message)
