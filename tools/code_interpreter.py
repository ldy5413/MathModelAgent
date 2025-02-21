from .jupyter_backend import JupyterKernel

functions = [
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "This function allows you to execute Python code and retrieve the terminal output. If the code "
            "generates image output, the function will return the text '[image]'. The code is sent to a "
            "Jupyter kernel for execution. The kernel will remain active after execution, retaining all "
            "variables in memory.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The code text"}
                },
                "required": ["code"],
                "additionalProperties": False,
            },
        },
    },
]


class CodeInterpreter:
    def __init__(self, work_dir: str):
        super().__init__()
        self.jupyter_work_dir = work_dir
        self.jupyter_kernel = JupyterKernel(work_dir=self.jupyter_work_dir)
