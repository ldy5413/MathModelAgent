import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.tools.code_interpreter import E2BCodeInterpreter


def test_e2b():
    interpreter = E2BCodeInterpreter("./test_workspace")
    text_to_gpt, content_to_display, error_occurred, error_message = (
        interpreter.execute_code(
            """
print('hello world')
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)
plt.plot(x, y)
plt.show()
"""
        )
    )

    print("text_to_gpt", text_to_gpt)
    print("content_to_display", content_to_display)
    print("error_occurred", error_occurred)
    print("error_message", error_message)


if __name__ == "__main__":
    test_e2b()
