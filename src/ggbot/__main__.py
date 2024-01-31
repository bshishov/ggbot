import sys
import logging
import asyncio
from pathlib import Path
from typing import Any

import yaml
from jinja2.nativetypes import NativeEnvironment

from ggbot.client import Client
from ggbot.conversation import ConversationManager
from ggbot.context import BotContext
from ggbot.assets import yaml_dict_from_file
from ggbot.text.tokema_integration import TokemaNlu, rules_from_grammar_dict
from ggbot.utils import require_item_from_dict_or_env

_logger = logging.getLogger("MAIN")


async def main(config_path: Path = Path("app.yaml")):
    # Loading config
    _logger.info(f"Loading config from {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.full_load(f)

    # Setting log level
    log_level_name = require_item_from_dict_or_env(config, "logging.level")
    log_level = getattr(logging, log_level_name, logging.INFO)
    logging.basicConfig(level=log_level)

    # Loading grammar files
    grammar_data = {}
    for filename in config["resources"]["grammar_files"]:
        _logger.info(f"Loading grammar from {filename}")
        grammar_part = yaml_dict_from_file(filename).get_data()
        grammar_data.update(grammar_part)

    rules_j2_env = NativeEnvironment()
    rules = rules_from_grammar_dict(grammar_data, rules_j2_env)
    nlu = TokemaNlu(rules)

    """ Bot initialization and startup """
    import time
    import datetime

    template_env = NativeEnvironment()
    template_env.globals["time"] = time.time
    template_env.globals["now"] = datetime.datetime.now

    context = BotContext(template_env=template_env)

    """ IGDB """
    """
    from ggbot.igdb import IgdbClient

    igdb = await IgdbClient.create(
        secret=require_item_from_dict_or_env(config, "igdb.secret"),
        client_id=require_item_from_dict_or_env(config, "igdb.client_id"),
    )
    """

    """ Dota """
    from ggbot.dota import Dota
    from ggbot.dota.phrases import PhraseGenerator, parse_rules
    from ggbot.spreadsheet import GoogleSpreadsheetsClient

    gsc = GoogleSpreadsheetsClient.from_file(
        filename=require_item_from_dict_or_env(config, "dota.gsc_service_account_file")
    )
    phrases_table = gsc.get_table_by_title("ggbot_dota", worksheet="phrases")

    phrase_parsing_grammar: dict[str, list[Any]] = {}
    for filename in config["dota"]["phrase_parsing_grammar_files"]:
        data = yaml_dict_from_file(filename)
        phrase_parsing_grammar.update(data)

    rules = rules_from_grammar_dict(phrase_parsing_grammar, template_env)
    phrases_nlu = TokemaNlu(rules)
    phrase_rules = parse_rules(phrases_table, phrases_nlu)

    dota = Dota(
        opendota_api_key=require_item_from_dict_or_env(config, "opendota.api_key"),
        phrase_generator=PhraseGenerator(phrase_rules),
    )

    """ Memory """
    from ggbot.memory import Memory, PickleDbStorage

    db_filename = require_item_from_dict_or_env(config, "memory.db_file")
    memory = Memory(storage=PickleDbStorage(filename=db_filename))

    components = [
        dota,
        memory,
        # igdb,
    ]

    for component in components:
        await component.init(context)

    # Scenarios / handlers
    from ggbot.scenarios import HANDLERS as COMMON_HANDLERS
    from ggbot.dota.scenarios import create_dota_scenario_handlers
    from ggbot.opendota import OpenDotaApi

    api = OpenDotaApi(dota.api_key)
    dota_handlers = create_dota_scenario_handlers(memory, dota, api)

    handlers = {**COMMON_HANDLERS, **dota_handlers}

    conversation_manager = ConversationManager(
        nlu=nlu, intent_handlers=handlers, context=context
    )
    client = Client(conversation_manager)
    context.client = client

    discord_token = require_item_from_dict_or_env(config, "discord.token")
    try:
        await client.start(discord_token)
    finally:
        if not client.is_closed():
            await client.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(*sys.argv[1:]))
