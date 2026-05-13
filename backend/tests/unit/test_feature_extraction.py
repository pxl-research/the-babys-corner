from app.routers.session import _extract_features_from_text, _pick_key_features


def test_extract_features_from_formatted_sections():
    text = """
Naam: Test

Belangrijkste kenmerken
• Eenvoudig inklapbaar
• Lichtgewicht 6,5 kg
• Geschikt tot 22 kg

Technische specificaties
• Afmetingen: 53 x 44 x 23,5 cm
"""
    result = _extract_features_from_text(text)
    assert "• Eenvoudig inklapbaar" in result
    assert "• Lichtgewicht 6,5 kg" in result
    assert "• Geschikt tot 22 kg" in result


def test_extract_features_handles_inline_specificaties():
    text = (
        "Compacte buggy. Specificaties: Gewicht: 7,8 kg. "
        "Afmetingen: 54x42x18 cm. Maximaal laadgewicht: 22 kg. Onderhoud: doek."
    )
    result = _extract_features_from_text(text)
    assert "• Gewicht: 7,8 kg" in result
    assert "• Afmetingen: 54x42x18 cm" in result
    assert "Onderhoud" not in result


def test_pick_key_features_prefers_llm_then_extraction_then_empty():
    stroller = {
        "formatted_description": "Kenmerken:\n• Met één hand opvouwbaar\n• Lichtgewicht",
        "description": "fallback",
    }
    llm = "Compact en wendbaar."
    assert _pick_key_features(stroller, llm) == llm
    assert "• Met één hand opvouwbaar" in _pick_key_features(stroller, "")
    assert _pick_key_features({"formatted_description": "", "description": ""}, None) == ""
