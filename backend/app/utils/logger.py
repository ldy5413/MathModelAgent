from loguru import logger
import sys
import os


class Logger:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, console_level: str = "INFO"):
        """
        初始化日志记录器
        Args:
            console_level: 控制台日志级别，默认为"INFO"
        """
        if not Logger._initialized:
            # 移除默认的控制台处理器
            logger.remove()
            # 添加控制台处理器，显示彩色日志
            logger.add(
                sys.stdout,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                level=console_level,
            )
            Logger._initialized = True
        self.logger = logger
        self._log_file_handler = None
        self._console_level = console_level

    def init(self, log_dir: str = None, file_level: str = "DEBUG"):
        """
        初始化日志系统，设置日志文件路径
        Args:
            log_dir: 日志保存目录
            file_level: 文件日志级别，默认为"DEBUG"
        """
        if log_dir is None:
            log_dir = os.getcwd()

        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)

        # 如果已经有文件处理器，先移除
        if self._log_file_handler is not None:
            self.logger.remove(self._log_file_handler)

        # 添加新的文件处理器
        self._log_file_handler = self.logger.add(
            os.path.join(log_dir, "log_{time:YYYY-MM-DD}.log"),
            encoding="utf-8",
            level=file_level,
        )

    def set_console_level(self, level: str):
        """
        动态设置控制台日志级别
        Args:
            level: 新的日志级别
        """
        # 移除现有的控制台处理器
        logger.remove()
        # 添加新的控制台处理器
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=level,
        )
        self._console_level = level

    def get_console_level(self) -> str:
        """获取当前控制台日志级别"""
        return self._console_level

    def __getattr__(self, name):
        # 将所有未定义的属性代理到 logger 实例
        return getattr(self.logger, name)


# 创建全局单例实例，设置控制台日志级别为 DEBUG
log = Logger(console_level="DEBUG")

# 导出 log 实例，这样其他模块可以直接使用
__all__ = ["log"]
