from typing import Mapping, List

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

__all__ = ["create_dota_scenario_handlers"]


def load_or_create_medals(
    memory: Memory,
    user_medals: IVariable[Mapping[str, int]],
    user_parsed_matches: IVariable[List[int]],
) -> Action:
    return sequence(
        selector(
            sequence(
                log("Загружаем медальки из памяти"),
                memory.check_user_var_exists(user_medals.get_name()),
                memory.copy_user_var_to_local(user_medals.get_name(), user_medals),
            ),
            sequence(
                log("Создаем пустые медальки"),
                set_var_from(user_medals, Factory(MAP(STRING, NUMBER), dict)),
            ),
        ),
        selector(
            sequence(
                log("Загружаем матчи из памяти"),
                memory.check_user_var_exists(user_parsed_matches.get_name()),
                memory.copy_user_var_to_local(
                    user_parsed_matches.get_name(), user_parsed_matches
                ),
            ),
            sequence(
                log("Создаем пустые медальки"),
                set_var_from(user_parsed_matches, Factory(ARRAY(NUMBER), list)),
            ),
        ),
    )


def save_medals(
    memory: Memory,
    user_medals: IVariable[Mapping[str, int]],
    user_parsed_matches: IVariable[List[int]],
) -> Action:
    return sequence(
        log("Сохраняем медальки и распаршенные матчи"),
        memory.set_user_var_from(user_medals.get_name(), user_medals),
        memory.set_user_var_from(user_parsed_matches.get_name(), user_parsed_matches),
    )


def require_steam_id(memory: Memory, steam_id: IVariable[int]) -> Action:
    steam_id_user_var = "steam_id"

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
                        memory.set_user_var_from(steam_id_user_var, steam_id),
                    ),
                    always_fail(reply_to_message("Кинь ссылку либо айди")),
                ),
            ),
            reply_to_message("Ок, спасибо!"),
        ),
    )

    return sequence(
        request_dotabuff_from_user,
        memory.check_user_var_exists(steam_id_user_var),
        memory.copy_user_var_to_local(steam_id_user_var, steam_id),
    )


def create_dota_scenario_handlers(
    memory: Memory, dota: Dota, api: OpenDotaApi
) -> Mapping[str, ScenarioHandler]:
    # Variables
    steam_id = Variable("steam_id", NUMBER)
    last_match_id = Variable("last_match_id", NUMBER)
    last_match = Variable("last_match", DOTA_MATCH)
    match_player = Variable("match_player", DOTA_MATCH_PLAYER)
    match_medals = Variable("player_medals", ARRAY(DOTA_PLAYER_MEDAL))
    phrase = Variable("phrase", STRING)
    rankings = Variable("rankings", ARRAY(DOTA_PLAYER_RANKING))
    user_medals = Variable("user_medals", MAP(STRING, NUMBER))
    user_medals_matches = Variable("user_medals_matches", ARRAY(NUMBER))
    _medal_name = Variable("_medal_name", STRING)
    _medal_count = Variable("_medal_count", NUMBER)
    _medal_to_add = Variable("_medal_to_add", STRING)

    all_medals = Const(ARRAY(STRING), list(PLAYER_MEDALS_DICT.keys()))

    intent_my_dotabuff = sequence(
        require_steam_id(memory, steam_id),
        reply_to_message2(
            Formatted("https://www.dotabuff.com/players/{steam_id}", steam_id=steam_id)
        ),
    )

    intent_my_mmr = sequence(
        require_steam_id(memory, steam_id),
        RequestOpenDotaAction(
            api_key=dota.api_key,
            # query="players/{{ steam_id }}"
            query=Formatted("players/{steam_id}", steam_id=steam_id),
        ),
        reply_to_message(
            "Твой ммр по версии opendota: {{ result.mmr_estimate.estimate }}"
        ),
    )

    _ranking = Variable("_ranking", DOTA_PLAYER_RANKING)
    intent_my_best_heroes = sequence(
        require_steam_id(memory, steam_id),
        RequestPlayerRankings(api=api, steam_id=steam_id, result=rankings, limit=6),
        reply_to_message2(
            Formatted(
                "Твои топ герои: {heroes}",
                heroes=JoinedString(
                    " ",
                    SelectFromArray(
                        rankings,
                        _ranking,
                        Formatted(
                            "`{name}`",
                            name=HeroName(Attr(_ranking, "hero_id"), dota),
                            score=AsString(Rounded(Attr(_ranking, "score"))),
                        ),
                    ),
                ),
            )
        ),
    )

    intent_my_last_match = sequence(
        require_steam_id(memory, steam_id),
        FetchLastMatchId(api=api, steam_id=steam_id, result=last_match_id),
        RequestMatch(api=api, match_id=last_match_id, result=last_match),
        set_var_from(
            var=match_player, value=MatchPlayer(match=last_match, steam_id=steam_id)
        ),
        GeneratePhraseForPlayer(
            phrase_generator=dota.phrase_generator,
            match_player=match_player,
            result=phrase,
            dota=dota,
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
                    "{minutes} минут", minutes=MatchDurationMinutes(last_match)
                ),
                match_id=last_match_id,
            ),
            thumbnail=PlayerHeroIconUrl(match_player, dota),
            fields=StringDictionary(
                {
                    "KDA": Formatted(
                        "{kills}/{deaths}/{assists}",
                        kills=Attr(match_player, "kills"),
                        deaths=Attr(match_player, "deaths"),
                        assists=Attr(match_player, "assists"),
                    ),
                    ":gold: Золото/Опыт": Formatted(
                        "{gpm} / {xpm}",
                        gpm=Attr(match_player, "gold_per_min"),
                        xpm=Attr(match_player, "xp_per_min"),
                    ),
                    ":crossed_swords: Урона по героям": Formatted(
                        "{value} k",
                        value=Rounded(
                            Divided(
                                Attr(match_player, "hero_damage"), Const(NUMBER, 1000)
                            )
                        ),
                    ),
                    ":homes: Урона по домикам": Formatted(
                        "{value} k",
                        value=Rounded(
                            Divided(
                                Attr(match_player, "tower_damage"), Const(NUMBER, 1000)
                            )
                        ),
                    ),
                    ":heal: Лечения": Formatted(
                        "{value} k",
                        value=Rounded(
                            Divided(
                                Attr(match_player, "hero_healing"), Const(NUMBER, 1000)
                            )
                        ),
                    ),
                    ":creep: Добито крипов": AsString(Attr(match_player, "last_hits")),
                }
            ),
        ),
    )

    matchups = Variable("matchups", ARRAY(DOTA_HERO_MATCHUP))
    m = Variable("_matchup", DOTA_HERO_MATCHUP)

    matchup_string = Formatted(
        "{hero} ({winrate}%)",
        hero=HeroName(Attr(m, "hero_id"), dota),
        winrate=AsString(
            Rounded(
                Divided(
                    Divided(Attr(m, "wins"), Attr(m, "games_played")),
                    Const(NUMBER, 0.01),
                )
            )
        ),
    )

    intent_dota_pick_against = sequence(
        RequestTopHeroMatchups(
            api=api, hero_id=NumberSlotValue("hero_id"), result=matchups, limit=6
        ),
        reply_to_message2(
            Formatted(
                "Против {hero} подойдут:\n{heroes}",
                hero=HeroName(NumberSlotValue("hero_id"), dota),
                heroes=JoinedString("\n", SelectFromArray(matchups, m, matchup_string)),
            )
        ),
    )

    intent_list_medals = reply_to_message2(
        FormattedMedals(Const(ARRAY(DOTA_PLAYER_MEDAL), PLAYER_MEDALS))
    )

    intent_last_match_medals = sequence(
        require_steam_id(memory, steam_id),
        load_or_create_medals(memory, user_medals, user_medals_matches),
        FetchLastMatchId(api=api, steam_id=steam_id, result=last_match_id),
        selector(
            CheckSecondsSinceRecentMatchGreaterThan(
                api, steam_id, seconds=Const(NUMBER, 2 * 60)
            ),
            sequence(
                log("Просим подождать, время с конца катки не прошло"),
                send_message_to_channel(
                    "Похоже что матч завершился совсем недавно, ждем повтор"
                ),
                wait_time(2 * 60),
            ),
        ),
        selector(
            sequence(
                log_value(Formatted("Запрашиваем матч {m}", m=last_match_id)),
                RequestMatch(api=api, match_id=last_match_id, result=last_match),
                CheckMatchIsParsed(last_match),
                log("Матч распаршен, все ок"),
            ),
            sequence(
                log_value(Formatted("Запрашиваем повтор {m}", m=last_match_id)),
                send_message_to_channel(
                    "Минутку, запрашивую у опендоты разбор матча..."
                ),
                RequestParseMatch(api=api, match_id=last_match_id),
                retry_until_success(
                    times=7,
                    child=sequence(
                        wait_time(60),  # Должно быть больше кеша
                        RequestMatch(
                            api=api,
                            match_id=last_match_id,
                            result=last_match,
                            use_cached_if_younger_than=20,
                        ),
                        CheckMatchIsParsed(last_match),
                    ),
                ),
                log("Делаем повторный запрос (должно загрузиться из кеша)"),
                RequestMatch(api=api, match_id=last_match_id, result=last_match),
            ),
            always_fail(
                send_message_to_channel(
                    "Что-то разбор матча у опендоты занял больше обычного, что-то пошло не так"
                )
            ),
        ),
        RequestMatch(api=api, match_id=last_match_id, result=last_match),
        set_var_from(
            var=match_player, value=MatchPlayer(match=last_match, steam_id=steam_id)
        ),
        CalculateMedals(match=last_match, steam_id=steam_id, result=match_medals),
        selector(
            sequence(
                AssignPlayerMedals(
                    match_medals=match_medals,
                    match_id=last_match_id,
                    player_medal_matches=user_medals_matches,
                    player_medals=user_medals,
                ),
                save_medals(memory, user_medals, user_medals_matches),
            ),
            log("Уже давали ачивки за этот матч"),
        ),
        GeneratePhraseForPlayer(
            phrase_generator=dota.phrase_generator,
            match_player=match_player,
            result=phrase,
            dota=dota,
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
                    "{duration} минут", duration=MatchDurationMinutes(last_match)
                ),
                match_id=last_match_id,
                medals=FormattedMedals(match_medals),
            ),
            thumbnail=PlayerHeroIconUrl(match_player, dota),
        ),
    )

    intent_debug_add_random_medal = sequence(
        load_or_create_medals(memory, user_medals, user_medals_matches),
        set_var_from(
            _medal_to_add,
            Fallback(STRING, RandomElementOf(all_medals), Const(STRING, "")),
        ),
        set_value_in_map(
            user_medals,
            _medal_to_add,
            Sum(
                Fallback(NUMBER, Item(user_medals, _medal_to_add), Const(NUMBER, 0)),
                Const(NUMBER, 1),
            ),
        ),
        send_message_to_channel2(
            Formatted("Добавил медальку `{medal}`", medal=_medal_to_add)
        ),
        save_medals(memory, user_medals, user_medals_matches),
    )

    intent_debug_clear_medals = sequence(
        load_or_create_medals(memory, user_medals, user_medals_matches),
        log("Пересоздаем медальки"),
        set_var_from(user_medals, Factory(MAP(STRING, NUMBER), dict)),
        set_var_from(user_medals_matches, Factory(ARRAY(NUMBER), list)),
        send_message_to_channel("Все, твоих медалей больше нет!"),
        save_medals(memory, user_medals, user_medals_matches),
    )

    intent_debug_my_medals = sequence(
        load_or_create_medals(memory, user_medals, user_medals_matches),
        send_message_to_channel2(
            Formatted(
                "Твои медали:\n{medals}",
                medals=JoinedString(
                    "\n",
                    SelectFromMap(
                        collection=user_medals,
                        key=_medal_name,
                        value=_medal_count,
                        fn=Formatted(
                            "x{count} {icon} **{name}** *{desc}*",
                            icon=Attr(MedalFromId(_medal_name), "icon"),
                            name=Attr(MedalFromId(_medal_name), "name"),
                            desc=Attr(MedalFromId(_medal_name), "description"),
                            count=_medal_count,
                        ),
                    ),
                ),
            )
        ),
    )

    intent_debug_calc_medals = sequence(
        require_steam_id(memory, steam_id),
        load_or_create_medals(memory, user_medals, user_medals_matches),
        set_var_from(last_match_id, NumberSlotValue("match_id")),
        log_value(Formatted("Разбираем ачивки матча {match}", match=last_match_id)),
        selector(
            RequestMatch(
                api=api,
                match_id=last_match_id,
                result=last_match,
                use_cached_if_younger_than=60 * 60,
            ),
            always_fail(send_message_to_channel("Не удалось запросить инфу о матче")),
        ),
        selector(
            CheckMatchIsParsed(last_match),
            always_fail(
                send_message_to_channel(
                    "Этот матч не распаршен, зайди на опендоту и кликни анализ повтора"
                )
            ),
        ),
        RequestMatch(api=api, match_id=last_match_id, result=last_match),
        set_var_from(
            var=match_player, value=MatchPlayer(match=last_match, steam_id=steam_id)
        ),
        CalculateMedals(match=last_match, steam_id=steam_id, result=match_medals),
        selector(
            sequence(
                AssignPlayerMedals(
                    match_medals=match_medals,
                    match_id=last_match_id,
                    player_medal_matches=user_medals_matches,
                    player_medals=user_medals,
                ),
                save_medals(memory, user_medals, user_medals_matches),
            ),
            always_fail(send_message_to_channel("За этот матч тебе уже давали ачивки")),
        ),
        send_message_to_channel2(
            Formatted(
                "Добавил медальки за матч {match}:\n{medals}",
                match=last_match_id,
                medals=FormattedMedals(match_medals),
            )
        ),
    )

    return {
        "intent-dotabuff": ScenarioHandler(intent_my_dotabuff),
        "intent-my-mmr": ScenarioHandler(intent_my_mmr),
        "intent-my-best-heroes": ScenarioHandler(intent_my_best_heroes),
        "intent-my-last-match": ScenarioHandler(intent_my_last_match),
        "intent-dota-pick-against": ScenarioHandler(intent_dota_pick_against),
        "intent-list-medals": ScenarioHandler(intent_list_medals),
        "intent-last-match-medals": ScenarioHandler(intent_last_match_medals),
        "intent-debug-add-random-medal": ScenarioHandler(intent_debug_add_random_medal),
        "intent-debug-clear-medals": ScenarioHandler(intent_debug_clear_medals),
        "intent-debug-my-medals": ScenarioHandler(intent_debug_my_medals),
        "intent-debug-calc-medals": ScenarioHandler(intent_debug_calc_medals),
    }
