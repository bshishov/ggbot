import os

from jinja2.nativetypes import NativeEnvironment

from ggbot.assets import *
from ggbot.text.tokema_integration import TokemaNlu, rules_from_grammar_dict
from ggbot.dota.phrases import *
from ggbot.spreadsheet import GoogleSpreadsheetsClient


def main():
    import pprint

    player_name = 'Shide'
    hero = '{hero}'

    import json
    with open('opendota_matches_shide.json', encoding='utf-8') as f:
        MATCHES = json.load(f)

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

    for match in MATCHES:
        print('\n\n\n')
        pprint.pprint(match)
        print('\n')
        p = pgen.generate_phrase(match, player_name, hero)


if __name__ == '__main__':
    main()
