class AppError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """
    Ресурс не найден (404)
    """
    pass


class ConflictError(AppError):
    """
    Конфликт данных, например дубликат (409)
    """
    pass


class LLMServiceError(AppError):
    """
    Ошибка при обращении к LLM API (503)
    """
    pass


class DatabaseError(AppError):
    """
    Ошибка на уровне базы данных (500)
    """
    pass
