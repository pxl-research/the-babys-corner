from app.content import load_quiz_config


def test_quiz_config_has_exact_prd_shape():
    config = load_quiz_config()
    assert len(config["questions"]) == 3
    for q in config["questions"]:
        assert len(q["options"]) == 3
        for opt in q["options"]:
            assert opt["profile"] in ("A", "B", "C")


def test_quiz_config_optional_note_copy_matches_prd():
    config = load_quiz_config()
    note = config["optional_note"]
    assert note["text"] == "Is er nog iets dat we mogen meenemen in jullie advies?"
    assert note["skip_label"] == "Niet nodig"
    assert note["continue_label"] == "Bekijk aanbevelingen"
    assert note["max_length"] == 1000


def test_quiz_config_optional_note_max_length():
    config = load_quiz_config()
    assert config["optional_note"]["max_length"] == 1000


def test_quiz_config_profiles_valid():
    config = load_quiz_config()
    for q in config["questions"]:
        profiles = {opt["profile"] for opt in q["options"]}
        assert profiles == {"A", "B", "C"}
