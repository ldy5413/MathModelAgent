from .jupyter_backend import JupyterKernel


class CodeInterpreter:
    def __init__(
        self, work_dir: str, notebook_serializer
    ):  # project / work_dir / task_id / jupyter
        self.jupyter_kernel = JupyterKernel(
            work_dir=work_dir, notebook_serializer=notebook_serializer
        )
