import json
import pprint
import logging

from jinja2.nativetypes import NativeEnvironment

from ggbot.assets import *
from ggbot.text.tokema_integration import TokemaNlu, rules_from_grammar_dict
from ggbot.dota.phrases import *
from ggbot.spreadsheet import GoogleSpreadsheetsClient


def main():
    logging.basicConfig(level=logging.DEBUG)

    player_name = 'Shide'
    hero = '{hero}'

    with open('opendota_matches_shide.json', encoding='utf-8') as f:
        opendota_matches = json.load(f)

    grammar = {
        **yaml_dict_from_file('../resources/dota/phrase_rules.yaml'),
        **yaml_dict_from_file('../resources/dota/heroes.yaml')
    }

    j2env = NativeEnvironment()
    rules = rules_from_grammar_dict(grammar, j2env)
    nlu = TokemaNlu(rules)

    client = GoogleSpreadsheetsClient.from_file('../.gsc_service_account.json')
    phrases_table = client.get_table_by_title('ggbot_dota', worksheet='phrases')
    phrase_rules = parse_rules(phrases_table, nlu)
    pgen = PhraseGenerator(phrase_rules)

    variables = get_dota_variables()

    for match in opendota_matches:
        print('\n\n\n')
        pprint.pprint(match)
        print('\n')
        p = pgen.generate_phrase(match_id=1, player=match, player_name=player_name, hero_name=hero)

        for v in variables:
            if v.name in match:
                value = match[v.name]
                #linguistic_value = v.fuzzify_max(value)
                res = v.fuzzify_all(value)
                print(f'{v.name}: {value}')
                print(res)

                print()

        break


if __name__ == '__main__':
    main()
