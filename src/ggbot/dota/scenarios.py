from typing import Mapping

from ggbot.memory import Memory
from ggbot.btree import *
from ggbot.actions import *
from ggbot.conversation import *

from .component import *

__all__ = [
    'create_dota_scenario_handlers'
]


def create_dota_scenario_handlers(memory: Memory, dota: Dota) -> Mapping[str, ScenarioHandler]:
    dotabuff_id_user_var = 'dotabuff_id'

    request_dotabuff_from_user = selector(
        memory.check_user_var_exists(dotabuff_id_user_var),
        sequence(
            reply_to_message("""Хз какой у тебя айди, 
            скинь ссылку на свой профиль в Dotabuff или Opendota, я запомню"""),
            retry_until_success(
                2,
                selector(
                    sequence(
                        wait_for_message_from_user(30),
                        parse_dotabuff_id_from_message(target_variable='dotabuff_id'),
                        memory.save_user_var(dotabuff_id_user_var, '{{ dotabuff_id }}')
                    ),
                    always_fail(reply_to_message('Кинь ссылку либо айди'))
                )
            ),
            reply_to_message("""Ок, спасибо!""")
        )
    )

    require_dotabuff = sequence(
        request_dotabuff_from_user,
        memory.check_user_var_exists(dotabuff_id_user_var),
        memory.copy_user_var_to_local(dotabuff_id_user_var, 'dotabuff_id'),
    )

    intent_my_dotabuff = sequence(
        require_dotabuff,
        reply_to_message("https://www.dotabuff.com/players/{{ dotabuff_id }}")
    )

    intent_my_mmr = sequence(
        require_dotabuff,
        RequestOpenDotaAction(
            api_key=dota.api_key,
            query="players/{{ dotabuff_id }}"
        ),
        reply_to_message("Твой ммр по версии opendota: {{ result.mmr_estimate.estimate }}")
    )

    intent_my_best_heroes = sequence(
        require_dotabuff,
        RequestOpenDotaAction(
            api_key=dota.api_key,
            query="players/{{ dotabuff_id }}/rankings"
        ),
        reply_to_message("""Топ герои:
        {% for hero in (result|sort(attribute='score', reverse=False))[:5] %}
        * {{ hero.hero_id|dota_hero_id_to_localized_name }}{% endfor %}""")
    )

    intent_my_last_match = sequence(
        require_dotabuff,
        RequestOpenDotaAction(
            api_key=dota.api_key,
            query="players/{{ dotabuff_id }}/recentMatches"
        ),
        GeneratePhraseAction(dota.phrase_generator),
        SendEmbed(
            #title="""{%- if (result[0].radiant_win and result[0].player_slot|dota_slot_is_radiant) or (not result[0].radiant_win and result[0].player_slot|dota_slot_is_dire) -%}Победа{%- else -%}Поражение{% endif %} на {{ result[0].hero_id|dota_hero_id_to_localized_name }} ({{ result[0].duration // 60 }}:{{ result[0].duration % 60 }})""",
            #description='{{ phrase }}',
            description="""{%- if (result[0].radiant_win and result[0].player_slot|dota_slot_is_radiant) or (not result[0].radiant_win and result[0].player_slot|dota_slot_is_dire) -%}Победа{%- else -%}Поражение{% endif %} на {{ result[0].hero_id|dota_hero_id_to_localized_name }} ({{ result[0].duration // 60 }}:{{ result[0].duration % 60 }})
            Посмотреть на [Dotabuff](https://www.dotabuff.com/matches/{{ result[0].match_id }}), [OpenDota](https://www.opendota.com/matches/{{ result[0].match_id }})""",
            title='{{ phrase }}',
            #url="https://www.dotabuff.com/matches/{{ result[0].match_id }}",
            thumbnail="https://cdn.origin.steamstatic.com/apps/dota2/images/heroes/{{ (result[0].hero_id|dota_hero_id_to_name)[14:] }}_icon.png",
            #thumbnail="https://www.dotabuff.com/assets/heroes/{{ (result[0].hero_id|dota_hero_id_to_name)[14:] }}.jpg",
            fields={
                #"Длительность": "{{ result[0].duration // 60 }}:{{ result[0].duration % 60 }}",
                #№"Герой": "{{ result[0].hero_id|dota_hero_id_to_localized_name }}",
                "KDA": "{{ result[0].kills }}/{{ result[0].deaths }}/{{ result[0].assists }}",
                #"Skill bracket": "{{ result[0].skill|dota_skill_id_to_name }}",
                # Роль: "{{ result[0].lane }} {{ result[0].lane_role }} ({{ result[0].is_roaming }})"
                # radiant_win: "{{ result[0].radiant_win }}"
                ":gold: Золото/Опыт": "{{ result[0].gold_per_min }} / {{ result[0].xp_per_min }}",
                ":crossed_swords: Урона по героям": "{{ (result[0].hero_damage / 1000)|round|int }} k",
                ":homes: Урона по домикам": "{{ (result[0].tower_damage / 1000)|round|int }} k",
                ":heal: Лечения": "{{ (result[0].hero_healing / 1000)|round|int }} k",
                ":creep: Добито крипов": "{{ result[0].last_hits }}",
            },
            #footer="{{ result[0].match_id }} - {{ (result[0].start_time + result[0].duration)|from_timestamp('%d.%m.%Y %H:%M') }}"
            #footer="Посмотреть на [Dotabuff](https://www.dotabuff.com/matches/{{ result[0].match_id }}), [OpenDota](https://www.opendota.com/matches/5936636695)"
        )
    )

    intent_dota_pick_against = sequence(
        RequestOpenDotaAction(
            api_key=dota.api_key,
            query="heroes/{{ match.slots.hero_id }}/matchups"
        ),
        CountMatchupsAction(),
        reply_to_message("""Против {{ match.slots.hero_id|dota_hero_id_to_localized_name }} неплохо заходят:
        {% for hero in result[:5] %}{{ hero.hero_id|dota_hero_id_to_localized_name }} ({{ '{0:0.1f}'.format(hero.winrate * 100) }}%)
        {% endfor %}""")
    )

    return {
        'intent-dotabuff': ScenarioHandler(intent_my_dotabuff),
        'intent-my-mmr': ScenarioHandler(intent_my_mmr),
        'intent-my-best-heroes': ScenarioHandler(intent_my_best_heroes),
        'intent-my-last-match': ScenarioHandler(intent_my_last_match),
        'intent-dota-pick-against': ScenarioHandler(intent_dota_pick_against)
    }
