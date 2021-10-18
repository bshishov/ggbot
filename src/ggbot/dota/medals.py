from typing import Mapping

from attr import dataclass

from ggbot.dota.predicates import *
from ggbot.dota.commons import ItemsIds, PermanentBuffIds


__all__ = [
    'PlayerMedal',
    'PLAYER_MEDALS',
    'PLAYER_MEDALS_DICT'
]


@dataclass
class PlayerMedal:
    id: str
    name: str
    predicate: IPlayerPredicate
    icon: str = '🏅'
    enabled: bool = True
    description: str = 'без описания('


PLAYER_MEDALS = [
    PlayerMedal(
        id='lots_of_kills_zero_deaths',
        name='Терминатор',
        icon='🤖',
        description='Более 20 убийств без смертей',
        predicate=And(ParamHigherThan(P_KILLS, 20), ParamEqual(P_DEATHS, 0)),
    ),
    PlayerMedal(
        id='lots_of_obs_placed',
        name='Директор по наблюдению',
        icon='🎥',
        description='Установлено более 20 обсов',
        predicate=ParamHigherThan(P_OBS_PLACED, 20),
    ),
    PlayerMedal(
        id='lots_of_healing',
        name='Гиппократ',
        icon='🩺',
        description='Более 15к лечения',
        predicate=ParamHigherThan(P_HEALING, 15000),
    ),
    PlayerMedal(
        id='lots_of_stuns',
        name='Фиксатор',
        icon='🧊',
        description='100 секунд контроля',
        predicate=ParamHigherThan(P_STUNS, 100),
    ),
    PlayerMedal(
        id='high_teamfight_participation',
        name='Командный игрок',
        icon='🧑‍🤝‍🧑',
        description='Принял участие в 90% драк',
        predicate=ParamHigherThan(P_TEAMFIGHT_PARTICIPATION, 0.9),
    ),
    PlayerMedal(
        id='lots_of_kills',
        name='Уничтожитель',
        icon=':firecracker:',
        description='Более 20 убийств',
        predicate=ParamHigherThan(P_KILLS, 20),
    ),
    PlayerMedal(
        id='lots_of_assists',
        name='Ассистент',
        icon='🤝',
        description='Более 30 ассистов',
        predicate=ParamHigherThan(P_ASSISTS, 30),
    ),
    PlayerMedal(
        id='lots_of_net_worth',
        name='Шейх',
        icon='🤑',
        description='Ценность выше 40к',
        predicate=ParamHigherThan(P_NET_WORTH, 40000),
    ),
    PlayerMedal(
        id='late_midas',
        name='Stonks',
        icon='📈',
        description='Купить поздний мидас',
        predicate=PurchasedItemAfter(item='midas', time=18 * 60)
    ),
    PlayerMedal(
        id='late_bf',
        name='Сонный дровосек',
        icon='🪓⏰',
        description='Купить поздний бф',
        predicate=PurchasedItemAfter(item='bfury', time=18 * 60)
    ),
    PlayerMedal(
        id='lots_of_sen_placed',
        name='Параноик',
        icon='😱',
        description='Установить более 20 сентрей',
        predicate=ParamHigherThan(P_SEN_PLACED, 20),
    ),
    PlayerMedal(
        id='many_creeps_before_10',
        name='Крипоед',
        icon='🏋️',
        description='Добить более 50 крипов до 10 минуты',
        predicate=LastHitsInTGreaterThan(50, match_minutes=10),
    ),
    PlayerMedal(
        id='100_creeps_before_10',
        name='Impressive',
        icon='💯',
        description='Добить более 99 крипов до 10 минуты',
        predicate=LastHitsInTGreaterThan(99, match_minutes=10),
    ),
    PlayerMedal(
        id='many_smoke_usages',
        name='Вейпер',
        icon=':wind_blowing_face:',
        description='Использовать более 3х смоков за игру',
        predicate=UsedItemTimesMoreThan('smoke_of_deceit', 3),
    ),
    PlayerMedal(
        id='many_movespeed_items',
        name='Гонщик',
        icon='🏎️',
        description='Много предметров на скорость',
        predicate=And(
            Or(
                HasItemInInventory(ItemsIds.travel_boots),
                HasItemInInventory(ItemsIds.travel_boots_2)
            ),
            HasItemInInventory(ItemsIds.cyclone),
            # HasItemInInventory(ItemsIds.ancient_janggo),  # drums :) nobody picks drums
            Or(
                HasItemInInventory(ItemsIds.yasha),
                HasItemInInventory(ItemsIds.yasha_and_kaya),
                HasItemInInventory(ItemsIds.sange_and_yasha),
                HasItemInInventory(ItemsIds.manta),
            )
        ),
    ),
    PlayerMedal(
        id='used_many_flasks',
        name='Обмазанный',
        icon='🧴',
        description='Использовать более 4х фласок',
        predicate=UsedItemTimesMoreThan('flask', 4),
    ),
    PlayerMedal(
        id='fast_bottle',
        name='Непросыхающий',
        icon='👨‍🍼',
        description='Купить бутылку до 1:35',
        predicate=PurchasedItemEarlierThan('bottle', 95),
    ),
    PlayerMedal(
        id='lots_of_deaths',
        name='Завсегдатай таверны',
        icon='🍻',
        description='Умереть более 15 раз',
        predicate=ParamHigherThan(P_DEATHS, 15),
    ),
    PlayerMedal(
        id='many_chat_messages',
        name='Губошлеп',
        icon='😲',
        description='Написать в чат боллее 5 сообщений',
        predicate=PhrasesInChatMoreThan(5),
    ),
    PlayerMedal(
        id='toxic_chat_messages',
        name='Токсик',
        icon='🤬',
        description='Доказать всем в чате',
        predicate=IsToxicChat(),
    ),
    PlayerMedal(
        id='many_dust_usages',
        name='Пыль в глаза',
        icon='💨',
        description='Использовать более 2х дастов',
        predicate=UsedItemTimesMoreThan('dust', 2),
    ),
    PlayerMedal(
        id='many_camps_stacked',
        name='Патимейкер',
        icon=':family_mmbb:',
        description='Стакнуть более 5 лагерей',
        predicate=ParamHigherThan(P_CAMPS_STACKED, 5),
    ),
    PlayerMedal(
        id='won_predicted_match',
        name='Провидец',
        icon='🔮',
        description='Победа в предсказанном матче',
        predicate=And(PredictedVictory(), PLAYER_WON),
    ),
    PlayerMedal(
        id='lots_of_hero_damage',
        name='Потрошитель',
        icon='👹',
        description='Более 60к урона по героям',
        predicate=ParamHigherThan(P_HERO_DAMAGE, 60000),
    ),
    PlayerMedal(
        id='lots_of_tower_damage',
        name='Деконструктор',
        icon='🧱👷',
        description='Более 10к урона по строениям',
        predicate=ParamHigherThan(P_TOWER_DAMAGE, 10000),
    ),
    PlayerMedal(
        id='high_xpm',
        name='Ученик',
        icon='🎓',
        description='Более 800 опыта в минуту',
        predicate=ParamHigherThan(P_XPM, 800),
    ),
    PlayerMedal(
        id='many_bounty_rune_pickups',
        name='Кладоискатель',
        icon='👑',
        description='Подобрать более 7 баунти рун за игру',
        predicate=PickedUpRuneTimesMoreThan(rune_key=5, amount=7),
    ),
    PlayerMedal(
        id='many_utility_items_usage',
        name='Спаситель',
        icon='🚑',
        description='Более 10 раз использовать утилитарный предмет для спасения',
        predicate=Or(
            UsedItemTimesMoreThan('glimmer_cape', 10),  # TODO: exclude self
            UsedItemTimesMoreThan('force_staff', 10),
            UsedItemTimesMoreThan('lotus_orb', 10),
            UsedItemTimesMoreThan('sphere', 10),  # linken sphere
            UsedItemTimesMoreThan('medallion_of_courage', 10),
            UsedItemTimesMoreThan('pipe', 10),
        ),
    ),
    PlayerMedal(
        id='fast_bfury',
        name='Крипоруб',
        icon='🪓',
        description='Собрать БФ до 14й',
        predicate=PurchasedItemEarlierThan('bfury', 14 * 60),
    ),
    PlayerMedal(
        id='ate_shard_and_scepter',
        name='Благословлен аганимом',
        icon='💫',
        description='Съесть аганим и шард',
        predicate=And(
            PermanentBuffStacksMoreThan(buff_id=PermanentBuffIds.aghanims_shard, stacks=-1),
            PermanentBuffStacksMoreThan(buff_id=PermanentBuffIds.ultimate_scepter, stacks=-1),
        ),
    ),
    PlayerMedal(
        id='tango_eater',
        name='Терпила',
        icon='🍡',
        description='Съесть более 6 танго',
        predicate=UsedItemTimesMoreThan('tango', 6),
    ),
    PlayerMedal(
        id='lots_of_silencer_stacks',
        name='Мудреныч',
        icon='🤓',
        description='Набрать более 20 стаков на сайленсере',
        predicate=PermanentBuffStacksMoreThan(
            buff_id=PermanentBuffIds.silencer_glaives_of_wisdom,
            stacks=60
        )
    ),
    PlayerMedal(
        id='lots_of_pudge_stacks',
        name='Жиртрест',
        icon='🥩',
        description='Набрать более 30 стаков на пудже',
        predicate=PermanentBuffStacksMoreThan(
            buff_id=PermanentBuffIds.pudge_flesh_heap,
            stacks=30
        )
    ),
    PlayerMedal(
        id='lots_of_lion_stacks',
        name='Не пальцем деланный',
        icon=':middle_finger:',
        description='Набрать больше 7 стаков на лионе',
        predicate=PermanentBuffStacksMoreThan(
            buff_id=PermanentBuffIds.lion_finger_of_death,
            stacks=7
        )
    ),
    PlayerMedal(
        id='lots_of_duel_stacks',
        name='Дуэлянт',
        icon='⚔️',
        description='Набрать больше 300 урона с дуэлей',
        predicate=PermanentBuffStacksMoreThan(
            buff_id=PermanentBuffIds.legion_commander_duel,
            stacks=300
        )
    ),
    PlayerMedal(
        id='lots_of_slark_stacks',
        name='Крыса',
        icon=':rat:',
        description='Набрать больше 30 стаков на сларке',
        predicate=PermanentBuffStacksMoreThan(
            buff_id=PermanentBuffIds.slark_essence_shift,
            stacks=30
        )
    ),
    PlayerMedal(
        id='lots_of_bh_gold_stolen',
        name='Вор',
        icon=':moneybag:',
        description='Подрезать более 500 золота джинадой',
        predicate=PermanentBuffStacksMoreThan(
            buff_id=PermanentBuffIds.bounty_hunter_jinada,
            stacks=500
        )
    ),
    PlayerMedal(
        id='lots_of_buybacks',
        name='Феникс',
        icon='🥚',
        description='Нажать байбек более 2х раз',
        predicate=BuybackedMoreThan(2)
    ),
    PlayerMedal(
        id='read_lots_of_books',
        name='Проффесор',
        icon='📚',
        description='Прочитать более 4х книжек',
        predicate=PermanentBuffStacksMoreThan(
            buff_id=PermanentBuffIds.tome_of_knowledge,
            stacks=4
        )
    ),
    PlayerMedal(
        id='low_net_worth',
        name='Бомжара',
        icon='🧻',
        description='Иметь ценность ниже 6к',
        predicate=ParamLowerThan(P_NET_WORTH, 6000),
    ),
    PlayerMedal(
        id='high_apm',
        name='Старкрафтер',
        icon='🐙⚡',
        description='Набрать APM более 400',
        predicate=ParamHigherThan(P_APM, 400),
    ),
    PlayerMedal(
        id='lots_of_courier_kills',
        name='Убийца курей',
        icon='🐓',
        description='Убить более 2х курьеров',
        predicate=ParamHigherThan(P_COURIER_KILLS, 2),
    ),
    PlayerMedal(
        id='no_denies',
        name='Ленивый',
        icon='🦥',
        description='Не заденаить ни одного крипа',
        predicate=ParamLowerThan(P_DENIES, 1),
    ),
    PlayerMedal(
        id='won_fast_game',
        name='Спидраннер',
        icon='🏃‍♂️⏩',
        description='Победить за 20 минут',
        predicate=And(PLAYER_WON, MatchShorterThan(20 * 60)),
    ),
    PlayerMedal(
        id='stolen_aegis',
        name='Вор в законе',
        icon=':raccoon:',
        description='Украл аегис',
        predicate=STOLEN_AEGIS,
    ),
    PlayerMedal(
        id='radiance_and_midas',
        name='Инвестор',
        icon='💱️',
        description='Закончить игру с радиком и мидасом',
        predicate=And(
            HasItemInInventory(ItemsIds.radiance),
            HasItemInInventory(ItemsIds.hand_of_midas),
        ),
    ),
    PlayerMedal(
        id='lots_of_defence_items',
        name='Лучок',
        icon='🧅',
        description='Закончить игру с обраткой, кирасой и лотусом',
        predicate=And(
            HasItemInInventory(ItemsIds.blade_mail),
            HasItemInInventory(ItemsIds.assault),
            HasItemInInventory(ItemsIds.lotus_orb),
        )
    ),
    PlayerMedal(
        id='bought_2_rapiers',
        name='Дашкевич. А.Ю',
        icon=':woman_teacher:',
        description='Закончить игру с 2мя рапирами',
        predicate=HasAtLeastNItemsInInventory(ItemsIds.rapier, minimum=2)
    ),
    PlayerMedal(
        id='fast_first_blood',
        name='Кровожадный',
        icon=':man_vampire:',
        description='Оформил фб до начала игры',
        predicate=ClaimedObjectiveOfType('CHAT_MESSAGE_FIRSTBLOOD', before=0)
    ),
    PlayerMedal(
        id='fast_first_blood',
        name='Сладкая булочка',
        icon=':doughnut:',
        description='Отдал фб до начала игры',
        predicate=DiedOfFirstBloodBefore(before=0)
    ),
    PlayerMedal(
        id='zero_lh_and_denies_up_to_10',
        name='Пацифист',
        icon='☮️',
        description='Не добил ни одного крипа (даже своего) до 10й',
        predicate=And(
            Not(LastHitsInTGreaterThan(value=0, match_minutes=10)),
            Not(DeniesInTGreaterThan(value=0, match_minutes=10)),
        )
    ),
    PlayerMedal(
        id='lots_of_denies',
        name='Киллджой',
        icon=':man_gesturing_no:',
        description='Добил больше 20 своих крипов',
        predicate=ParamHigherThan(P_DENIES, 20)
    ),
    PlayerMedal(
        id='lots_of_ancient_kills',
        name='Ведьмак',
        icon=':dagger:',
        description='Добил больше 50 древних крипов',
        predicate=ParamHigherThan(P_ANCIENT_KILLS, 50)
    ),
]
PLAYER_MEDALS_DICT: Mapping[str, PlayerMedal] = {m.id: m for m in PLAYER_MEDALS}
