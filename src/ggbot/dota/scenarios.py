from typing import Mapping

from ggbot.memory import Memory
from ggbot.btree import *
from ggbot.actions import *
from ggbot.conversation import *
from ggbot.context import *
from ggbot.btdata import *
from ggbot.bttypes import *
from ggbot.opendota import OpenDotaApi
from ggbot.dota.component import *
from ggbot.dota.medals import *

__all__ = [
    'create_dota_scenario_handlers'
]


def _medals_message() -> str:
    msg = 'Медали:\n'
    for medal in PLAYER_MEDALS:
        msg += f'{medal.icon} {medal.name}\n'
    return msg


def create_dota_scenario_handlers(
        memory: Memory,
        dota: Dota,
        api: OpenDotaApi
) -> Mapping[str, ScenarioHandler]:
    steam_id = Variable('steam_id', NUMBER)
    last_match_id = Variable('last_match_id', NUMBER)
    last_match = Variable('last_match', DOTA_MATCH)
    match_player = Variable('match_player', DOTA_MATCH_PLAYER)
    medal_ids = Variable('medal_ids', ARRAY(STRING))
    phrase = Variable('phrase', STRING)
    steam_id_user_var = 'steam_id'

    request_dotabuff_from_user = selector(
        memory.check_user_var_exists(steam_id_user_var),
        sequence(
            reply_to_message(
                "Хз какой у тебя айди, "
                "скинь ссылку на свой профиль в Dotabuff или Opendota, я запомню"
            ),
            retry_until_success(
                2,
                selector(
                    sequence(
                        wait_for_message_from_user(60),
                        parse_steam_id_from_message(steam_id),
                        memory.set_user_var(steam_id_user_var, '{{ steam_id }}')
                    ),
                    always_fail(reply_to_message('Кинь ссылку либо айди'))
                )
            ),
            reply_to_message("Ок, спасибо!")
        )
    )

    require_dotabuff = sequence(
        request_dotabuff_from_user,
        memory.check_user_var_exists(steam_id_user_var),
        memory.copy_user_var_to_local(steam_id_user_var, 'steam_id'),
    )

    intent_my_dotabuff = sequence(
        require_dotabuff,
        reply_to_message("https://www.dotabuff.com/players/{{ steam_id }}")
    )

    intent_my_mmr = sequence(
        require_dotabuff,
        RequestOpenDotaAction(
            api_key=dota.api_key,
            #query="players/{{ steam_id }}"
            query=Formatted("players/{steam_id}", steam_id=steam_id)
        ),
        reply_to_message("Твой ммр по версии opendota: {{ result.mmr_estimate.estimate }}")
    )

    intent_my_best_heroes = sequence(
        require_dotabuff,
        RequestOpenDotaAction(
            api_key=dota.api_key,
            query=Formatted("players/{steam_id}/rankings", steam_id=steam_id)
        ),
        reply_to_message("""Топ герои:
        {% for hero in (result|sort(attribute='score', reverse=False))[:5] %}
        * {{ hero.hero_id|dota_hero_id_to_localized_name }}{% endfor %}""")
    )

    intent_my_last_match = sequence(
        require_dotabuff,
        FetchLastMatchId(api=api, steam_id=steam_id, result=last_match_id),
        RequestMatch(api=api, match_id=last_match_id, result=last_match),
        set_var_from(var=match_player, value=MatchPlayer(match=last_match, steam_id=steam_id)),
        GeneratePhraseForPlayer(
            phrase_generator=dota.phrase_generator,
            match_player=match_player,
            result=phrase,
            dota=dota
        ),
        SendEmbed(
            title=phrase,
            description=Formatted(
                "{result} на {hero} ({duration})"
                "\nПосмотреть на [Dotabuff](https://www.dotabuff.com/matches/{match_id}), "
                "[OpenDota](https://www.opendota.com/matches/{match_id})",
                result=MatchPlayerResultString(match_player),
                hero=HeroName(PlayerHeroId(match_player), dota),
                duration=Formatted(
                    "{minutes} минут",
                    minutes=MatchDurationMinutes(last_match)
                ),
                match_id=last_match_id,
                medals=FormattedMedals(medal_ids)
            ),
            thumbnail=PlayerHeroIconUrl(match_player, dota),
            fields=StringDictionary({
                "KDA": Formatted(
                    "{kills}/{deaths}/{assists}",
                    kills=Attr(match_player, 'kills'),
                    deaths=Attr(match_player, 'deaths'),
                    assists=Attr(match_player, 'assists'),
                ),
                ":gold: Золото/Опыт": Formatted(
                    "{gpm} / {xpm}",
                    gpm=Attr(match_player, 'gold_per_min'),
                    xpm=Attr(match_player, 'xp_per_min'),
                ),
                ":crossed_swords: Урона по героям": Formatted(
                    "{value} k",
                    value=Rounded(
                        Divided(
                            Attr(match_player, 'hero_damage'),
                            Const(NUMBER, 1000)
                        )
                    )
                ),
                ":homes: Урона по домикам": Formatted(
                    "{value} k",
                    value=Rounded(
                        Divided(
                            Attr(match_player, 'tower_damage'),
                            Const(NUMBER, 1000)
                        )
                    )
                ),
                ":heal: Лечения": Formatted(
                    "{value} k",
                    value=Rounded(
                        Divided(
                            Attr(match_player, 'hero_healing'),
                            Const(NUMBER, 1000)
                        )
                    )
                ),
                ":creep: Добито крипов": AsString(Attr(match_player, 'last_hits'))
            })
        )
    )

    intent_dota_pick_against = sequence(
        RequestOpenDotaAction(
            api_key=dota.api_key,
            query=Formatted(
                "players/{hero_id}/matchups",
                hero_id=SlotValue('hero_id')
            )
        ),
        CountMatchupsAction(),
        reply_to_message("""Против {{ match.slots.hero_id|dota_hero_id_to_localized_name }} неплохо заходят:
        {% for hero in result[:5] %}{{ hero.hero_id|dota_hero_id_to_localized_name }} ({{ '{0:0.1f}'.format(hero.winrate * 100) }}%)
        {% endfor %}""")
    )

    intent_list_medals = reply_to_message(_medals_message())

    intent_last_match_medals = sequence(
        require_dotabuff,
        FetchLastMatchId(api=api, steam_id=steam_id, result=last_match_id),
        selector(
            CheckSecondsSinceRecentMatchGreaterThan(api, steam_id, seconds=Const(NUMBER, 2 * 60)),
            sequence(
                log("Просим подождать, время с конца катки не прошло"),
                send_message_to_channel(
                    "Похоже что матч завершился совсем недавно, ждем повтор"
                ),
                wait_time(2 * 60)
            )
        ),
        selector(
            sequence(
                log_value(Formatted("Запрашиваем матч {m}", m=last_match_id)),
                RequestMatch(
                    api=api,
                    match_id=last_match_id,
                    result=last_match
                ),
                CheckMatchIsParsed(last_match),
                log("Матч распаршен, все ок"),
            ),
            sequence(
                log_value(Formatted("Запрашиваем повтор {m}", m=last_match_id)),
                send_message_to_channel('Минутку, запрашивую у опендоты разбор матча...'),
                RequestParseMatch(api=api, match_id=last_match_id),
                retry_until_success(
                    times=7,
                    child=sequence(
                        wait_time(60),  # Должно быть больше кеша
                        RequestMatch(
                            api=api,
                            match_id=last_match_id,
                            result=last_match,
                            use_cached_if_younger_than=20
                        ),
                        CheckMatchIsParsed(last_match),
                    )
                ),
                log("Делаем повторный запрос (должно загрузиться из кеша)"),
                RequestMatch(
                    api=api,
                    match_id=last_match_id,
                    result=last_match
                ),
            ),
            always_fail(
                send_message_to_channel(
                    "Что-то разбор матча у опендоты занял больше обычного, что-то пошло не так"
                )
            )
        ),
        RequestMatch(api=api, match_id=last_match_id, result=last_match),
        set_var_from(var=match_player, value=MatchPlayer(match=last_match, steam_id=steam_id)),
        CalculateMedals(match=last_match, steam_id=steam_id, result=medal_ids),
        GeneratePhraseForPlayer(
            phrase_generator=dota.phrase_generator,
            match_player=match_player,
            result=phrase,
            dota=dota
        ),
        SendEmbed(
            title=phrase,
            description=Formatted(
                "{result} на {hero} ({duration})"
                "\nПосмотреть на [Dotabuff](https://www.dotabuff.com/matches/{match_id}), "
                "[OpenDota](https://www.opendota.com/matches/{match_id}) "
                "\n\n{medals}",
                result=MatchPlayerResultString(match_player),
                hero=HeroName(PlayerHeroId(match_player), dota),
                duration=Formatted(
                    "{duration} минут",
                    duration=MatchDurationMinutes(last_match)
                ),
                match_id=last_match_id,
                medals=FormattedMedals(medal_ids)
            ),
            thumbnail=PlayerHeroIconUrl(match_player, dota),
        )
    )

    return {
        'intent-dotabuff': ScenarioHandler(intent_my_dotabuff),
        'intent-my-mmr': ScenarioHandler(intent_my_mmr),
        'intent-my-best-heroes': ScenarioHandler(intent_my_best_heroes),
        'intent-my-last-match': ScenarioHandler(intent_my_last_match),
        'intent-dota-pick-against': ScenarioHandler(intent_dota_pick_against),
        'intent-list-medals': ScenarioHandler(intent_list_medals),
        'intent-last-match-medals': ScenarioHandler(intent_last_match_medals)
    }
