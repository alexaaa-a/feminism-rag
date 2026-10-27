ROUTE_IN_DOMAIN = "in_domain"
ROUTE_NEEDS_TABLE = "needs_table"
ROUTE_LANG = "lang_preference"
ROUTE_INTENT = "intent"

ANSWERABLE = "answerable"
GROUNDED = "grounded"

RERANK_PREFIX = "candidate_"


def route_questions() -> dict[str, dict]:
    return {
        ROUTE_IN_DOMAIN: {
            "type": "noul",
            "instructions": (
                "Относится ли вопрос пользователя к феминизму, истории женского движения, "
                "правам женщин, гендерному равенству или связанным с ними документам и персоналиям?"
            ),
            "criteria": {
                "true": "Вопрос про феминизм, его историю, деятельниц, документы, права женщин.",
                "false": "Вопрос про что-то другое: погода, спорт, программирование, общая болтовня.",
            },
        },
        ROUTE_NEEDS_TABLE: {
            "type": "noul",
            "instructions": (
                "Нужны ли для ответа табличные данные: конкретный год, число, "
                "значение по стране или строка статистики?"
            ),
            "criteria": {
                "true": "Спрашивают точную цифру, год, значение по конкретной стране или позиции.",
                "false": "Спрашивают объяснение, причины, сравнение идей или биографию.",
            },
        },
        ROUTE_LANG: {
            "type": "choice",
            "instructions": "На каком языке источники подойдут для ответа на этот вопрос?",
            "criteria": {
                "ru": "Вопрос про русскоязычный или российский контекст, либо задан по-русски без привязки к зарубежным источникам.",
                "en": "Вопрос про англоязычный контекст: события, персоналии или документы англоязычных стран.",
                "any": "Язык источника не важен.",
            },
        },
        ROUTE_INTENT: {
            "type": "choice",
            "instructions": "Что именно нужно пользователю?",
            "criteria": {
                "factual": "Конкретный факт: дата, имя, число, событие.",
                "overview": "Обзор темы, объяснение или сравнение.",
                "corpus": "Вопрос про сам корпус: какие документы есть, что ассистент умеет.",
                "chitchat": "Приветствие или разговор не по делу.",
            },
        },
    }


def rerank_questions(candidates_count: int) -> dict[str, dict]:
    return {
        f"{RERANK_PREFIX}{index}": {
            "type": "noul",
            "instructions": (
                f"Содержит ли фрагмент {index} информацию, которая прямо отвечает "
                f"на вопрос пользователя или является его частью?"
            ),
            "criteria": {
                "true": "Во фрагменте есть факт, запрошенный в вопросе.",
                "false": "Фрагмент про другое или только упоминает тему без нужного факта.",
            },
        }
        for index in range(1, candidates_count + 1)
    }


def answerability_questions() -> dict[str, dict]:
    return {
        ANSWERABLE: {
            "type": "noul",
            "instructions": (
                "Достаточно ли выданных фрагментов, чтобы ответить на вопрос пользователя "
                "без догадок и без внешних знаний?"
            ),
            "criteria": {
                "true": "Фрагменты содержат запрошенный факт целиком.",
                "false": "Фрагменты про тему вообще, но нужного факта в них нет.",
            },
        }
    }


def groundedness_questions() -> dict[str, dict]:
    return {
        GROUNDED: {
            "type": "noul",
            "instructions": (
                "Каждое утверждение ответа подтверждается выданными фрагментами? "
                "Отвечай false, если в ответе есть факт, которого нет во фрагментах."
            ),
            "criteria": {
                "true": "Все факты ответа есть во фрагментах.",
                "false": "В ответе есть хотя бы один факт, которого во фрагментах нет.",
            },
        }
    }


def rerank_state(question: str, candidates: list[str]) -> str:
    numbered = "\n\n".join(
        f"Фрагмент {index}:\n{text}" for index, text in enumerate(candidates, start=1)
    )
    return f"Вопрос пользователя:\n{question}\n\nКандидаты:\n{numbered}"


def answerability_state(question: str, context: str) -> str:
    return f"Вопрос пользователя:\n{question}\n\nВыданные фрагменты:\n{context}"


def groundedness_state(question: str, context: str, answer: str) -> str:
    return (
        f"Вопрос пользователя:\n{question}\n\n"
        f"Выданные фрагменты:\n{context}\n\n"
        f"Ответ ассистента:\n{answer}"
    )
