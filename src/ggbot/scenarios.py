from ggbot.btree import *
from .actions import *
from .conversation import ScenarioHandler


__all__ = [
    "MISMATCH_SCENARIO",
    "HELLO_SCENARIO",
    "DIALOG_TEST_SCENARIO",
    "DOTA_GATHER_SCENARIO",
    "WHAT_DO_YOU_THINK",
    "HANDLERS",
]


MISMATCH_SCENARIO = sequence(
    # add_reaction_to_request_message('❓')
)


WHAT_DO_YOU_THINK = random_one_of(
    reply_to_message("конечно"),
    reply_to_message("а ты как думал"),
    reply_to_message("определенно"),
    reply_to_message("разумеется"),
    reply_to_message("а как же"),
    reply_to_message("естественно"),
    reply_to_message("само собой"),
    reply_to_message("ну да"),
    reply_to_message("возможно"),
    reply_to_message("теоретически"),
    reply_to_message("предположительно"),
    reply_to_message("шансы есть"),
    reply_to_message("проверять бы не стал"),
    reply_to_message("сомневаюсь"),
    reply_to_message("да нет"),
    reply_to_message("хз"),
    reply_to_message("тут я не до конца уверен"),
    reply_to_message("я бы не был так в это уверен"),
    reply_to_message("ну нет"),
    reply_to_message("точно нет"),
    reply_to_message("ты что, шутишь?"),
    reply_to_message("конечно же нет"),
    reply_to_message("это невозможно"),
    reply_to_message("что за вопрос"),
    reply_to_message("на это я отвечать не стану"),
)


HELLO_SCENARIO = random_one_of(
    reply_to_message("дороу"),
    reply_to_message("даров"),
    reply_to_message("привет"),
    reply_to_message("приветствую"),
    selector(
        sequence(
            check_condition("{{ 6 < now().hour <= 12 }}"),
            reply_to_message("Доброе утро @{{user.name}}"),
        ),
        sequence(
            check_condition("{{ 12 < now().hour <= 18 }}"),
            reply_to_message("Добрый день"),
        ),
        sequence(
            check_condition("{{ 18 < now().hour <= 22 }}"),
            reply_to_message("Добрый вечер"),
        ),
        sequence(
            check_condition("{{ (22 < now().hour <= 24) or (now().hour <= 6) }}"),
            reply_to_message("Доброй ночи <@{{ user.member.id }}>"),
        ),
        reply_to_message("Доброго времени суток"),
    ),
)


HELLO_1_SCENARIO = sequence(
    random_one_of(
        reply_to_message("дороу, как дела?"),
        reply_to_message("привет, как оно? "),
        reply_to_message("приветствую, как бодрость духа?"),
        reply_to_message("Доброго времени суток, как поживаете?"),
    ),
    selector(
        sequence(
            wait_for_message_from_user(10),
            random_one_of(
                reply_to_message("бывает"),
                reply_to_message("штош"),
                reply_to_message("здорово"),
                reply_to_message("но это же замечательно"),
                reply_to_message("сочуствую"),
                reply_to_message("везет тебе"),
                reply_to_message("прикольно"),
                reply_to_message("ок"),
                reply_to_message("такое"),
                add_reaction_to_request_message("👍"),
            ),
        ),
        random_one_of(
            reply_to_message("не хочешь говорить - ну и хер с тобой"),
            reply_to_message("казалось бы, простой был вопрос"),
            reply_to_message("хорошо, можешь не отвечать, я это запомнил"),
            reply_to_message("неужели так сложно ответ написать?"),
        ),
    ),
)


DOTA_GATHER_SCENARIO = sequence(
    send_message_to_channel("(это тест) Кто пойдет в доту? (20 секунд жду)"),
    repeat_until_timer_expires(
        25,
        selector(
            sequence(
                wait_for_message_from_channel(10),
                # add_reaction_to_request_message('✔️'),
                set_var(
                    "gathered",
                    "{% if gathered is defined %}{{ gathered + [message.author.name] }}{% else %}{{ [message.author.name] }}{% endif %}",
                ),
                edit_last_answer(
                    "(это тест) Кто пойдет в доту? (20 секунд жду) `{{ gathered }}`"
                ),
            ),
            send_message_to_channel("Anyone?"),
        ),
    ),
    send_message_to_channel("Голосование окончено"),
)


DIALOG_TEST_SCENARIO = sequence(
    reply_to_message("Просто скажи, да или нет?"),
    retry_until_success(
        2,
        sequence(
            sequence(
                wait_for_message_from_user_with_intents(["yes", "no"], seconds=5),
                selector(
                    sequence(message_intent_is("yes"), reply_to_message("Ок")),
                    sequence(message_intent_is("no"), reply_to_message("Нет так нет")),
                    always_fail(
                        random_one_of(
                            reply_to_message("И что ты этим хотел сказать?"),
                            reply_to_message('"Да" или "нет", так сложно что ли?'),
                        )
                    ),
                ),
            )
        ),
    ),
)

HANDLERS = {
    "mismatch": ScenarioHandler(MISMATCH_SCENARIO),
    "intent-hello": ScenarioHandler(HELLO_SCENARIO),
    "intent-what-do-you-think": ScenarioHandler(WHAT_DO_YOU_THINK),
    "intent-dialog-test": ScenarioHandler(DIALOG_TEST_SCENARIO),
    "intent-gather-test": ScenarioHandler(DOTA_GATHER_SCENARIO),
}
