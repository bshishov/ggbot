from ggbot.text.text import match_pattern, tokenize


def pipeline(text: str) -> list:
    return tokenize(text)


def tokens_to_text(tokens: list) -> str:
    return ' '.join(t.raw for t in tokens)


def test_no_slots():
    match = match_pattern(
        pipeline('привет'),
        pipeline('привет')
    )
    assert match.score > 0


def test_mismatch():
    match = match_pattern(
        pipeline('привет'),
        pipeline('банан')
    )
    assert match.score < 0.5


def test_slot_match_whole():
    match = match_pattern(
        pipeline('длинная фраза'),
        pipeline('{slot}')
    )
    assert tokens_to_text(match.slots['slot']) == 'длинная фраза'


def test_slot_at_the_start():
    match = match_pattern(
        pipeline('длинная фраза'),
        pipeline('{slot} фраза')
    )
    assert tokens_to_text(match.slots['slot']) == 'длинная'


def test_slot_at_the_end():
    match = match_pattern(
        pipeline('длинная фраза'),
        pipeline('длинная {slot}')
    )
    assert tokens_to_text(match.slots['slot']) == 'фраза'


def test_slot_int_the_middle():
    match = match_pattern(
        pipeline('очень длинная фраза'),
        pipeline('очень {slot} фраза')
    )
    assert tokens_to_text(match.slots['slot']) == 'длинная'


def test_slot_multi_token_match_start():
    match = match_pattern(
        pipeline('очень длинная фраза'),
        pipeline('{slot} фраза')
    )
    assert tokens_to_text(match.slots['slot']) == 'очень длинная'


def test_slot_multi_token_match_middle():
    match = match_pattern(
        pipeline('очень длинная и сложная фраза'),
        pipeline('очень {slot} фраза')
    )
    assert tokens_to_text(match.slots['slot']) == 'длинная и сложная'


def test_slot_multi_token_match_end():
    match = match_pattern(
        pipeline('очень длинная и сложная фраза'),
        pipeline('очень {slot}')
    )
    assert tokens_to_text(match.slots['slot']) == 'длинная и сложная фраза'


def test_imperfect_match_at_the_start_slot_extraction():
    match = match_pattern(
        pipeline('эй бот, это очень длинная фраза'),
        pipeline('это {slot}')
    )
    assert tokens_to_text(match.slots['slot']) == 'очень длинная фраза'


def test_imperfect_match_at_the_end_slot_extraction():
    match = match_pattern(
        pipeline('это очень длинная фраза! понятненько?!'),
        pipeline('это {slot}!')
    )
    assert tokens_to_text(match.slots['slot']) == 'очень длинная фраза'
