from src.domain.entities.evaluation import EvalCase

DEFAULT_EVAL_CASES: list[EvalCase] = [
    EvalCase(
        question="Кто написал трактат «В защиту прав женщин» и в каком году он вышел?",
        gold_sources=["06_ru_Уолстонкрафт_Мэри.txt"],
        evidence="1792",
    ),
    EvalCase(
        question=(
            "Какая английская писательница XVIII века требовала для женщин "
            "такого же образования, как у мужчин?"
        ),
        gold_sources=["06_ru_Уолстонкрафт_Мэри.txt"],
        evidence="Уолстонкрафт",
    ),
    EvalCase(
        question="Чем цели первой волны феминизма отличались от целей второй волны?",
        gold_sources=[
            "01_ru_Феминизм.txt",
            "02_ru_Первая_волна_феминизма.txt",
            "03_ru_Вторая_волна_феминизма.txt",
            "26_ru_волны_феминизма.md",
        ],
        evidence="волн",
    ),
    EvalCase(
        question="Кто стал первой в истории женщиной-министром?",
        gold_sources=["08_ru_Коллонтай_Александра_Михайловна.txt"],
        evidence="министром",
    ),
    EvalCase(
        question="Что такое интерсекциональность и кто ввёл этот термин?",
        gold_sources=["12_ru_Интерсекциональность.txt"],
        evidence="Креншоу",
    ),
    EvalCase(
        question="В каком году женщины получили право голоса в Новой Зеландии?",
        gold_sources=[
            "05_ru_Суфражистки.txt",
            "13_ru_Женское_избирательное_право.txt",
            "02_ru_Первая_волна_феминизма.txt",
        ],
        evidence="1893",
    ),
    EvalCase(
        question="When was the Seneca Falls Convention held?",
        gold_sources=[
            "18_en_Seneca_Falls_Convention.txt",
            "20_en_Elizabeth_Cady_Stanton.txt",
        ],
        evidence="1848",
    ),
    EvalCase(
        question="Из каких частей состоит CEDAW и какие статьи в них входят?",
        gold_sources=[
            "25_ru_Статистика_и_CEDAW.docx",
            "16_ru_Конвенция_о_ликвидации_всех_форм_дискриминации_женщин.txt",
        ],
        evidence="Часть",
    ),
    EvalCase(
        question="В каком году женщины Албании впервые получили избирательное право?",
        gold_sources=[
            "25_ru_Статистика_и_CEDAW.docx",
            "28_ru_волны_и_суфражизм_layout.pdf",
        ],
        evidence="Albania",
    ),
    EvalCase(
        question="В каком году открылись Бестужевские курсы?",
        gold_sources=["14_ru_Бестужевские_курсы.txt"],
        evidence="1878",
    ),
    EvalCase(
        question="Какую книгу написала Бетти Фридан и чем она известна?",
        gold_sources=["10_ru_Фридан_Бетти.txt", "21_en_Betty_Friedan.txt"],
        evidence="женственности",
    ),
    EvalCase(
        question="Что такое гендерный разрыв в оплате труда?",
        gold_sources=["25_ru_Статистика_и_CEDAW.docx"],
        evidence="pay gap",
    ),
    EvalCase(
        question="Сколько женщин входит в состав Государственной думы в 2024 году?",
        has_answer=False,
    ),
    EvalCase(
        question=(
            "Какой гендерный разрыв в оплате труда в России "
            "по данным Росстата за 2023 год?"
        ),
        has_answer=False,
    ),
    EvalCase(
        question="Как подать иск о дискриминации по полу в российский суд?",
        has_answer=False,
    ),
    EvalCase(
        question="Кто получил Нобелевскую премию мира 2023 года за защиту прав женщин?",
        has_answer=False,
    ),
    EvalCase(
        question="Какие квоты для женщин в советах директоров действуют в Норвегии сейчас?",
        has_answer=False,
    ),
]
