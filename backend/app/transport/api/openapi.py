from .schemas import ErrorOut, RequestValidationErrorOut

TAGS_METADATA = [
    {
        "name": "system",
        "description": "Состояние сервиса и публичная конфигурация приложения.",
    },
    {
        "name": "auth",
        "description": "Вход через MAX или общий профиль демонстрационного режима.",
    },
    {
        "name": "profile",
        "description": "Текущий пользователь и его предпочтения.",
    },
    {
        "name": "events",
        "description": "Рекомендации, каталог, избранное и реакции на события.",
    },
    {
        "name": "evenings",
        "description": "Генерация и сохранение готовых планов вечера.",
    },
    {
        "name": "admin",
        "description": "Административные операции с отдельным токеном доступа.",
    },
]

ERROR_DESCRIPTIONS = {
    401: "Требуется действительный Bearer-токен.",
    403: "Недостаточно прав для выполнения операции.",
    404: "Запрошенный ресурс не найден.",
    409: "Операция недоступна до завершения анкеты.",
    422: "Запрос не прошёл проверку формата или бизнес-правил.",
    502: "Внешний поставщик событий временно недоступен.",
}


def error_responses(*status_codes: int):
    return {
        status_code: {
            "model": ErrorOut | RequestValidationErrorOut
            if status_code == 422
            else ErrorOut,
            "description": ERROR_DESCRIPTIONS[status_code],
        }
        for status_code in status_codes
    }
