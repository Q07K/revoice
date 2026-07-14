from app.engines.pitch import octave_shift_semitones


def test_matching_registers_need_no_shift() -> None:
    assert octave_shift_semitones(200.0, 200.0) == 0
    # Within half an octave still rounds to no shift.
    assert octave_shift_semitones(200.0, 260.0) == 0


def test_cross_gender_shifts_one_octave() -> None:
    # Male voice (~110 Hz) covering a female song (~220 Hz) drops an octave.
    assert octave_shift_semitones(110.0, 220.0) == -12
    # Female voice covering a male song goes up an octave.
    assert octave_shift_semitones(220.0, 110.0) == 12


def test_extreme_ratio_is_clamped_to_one_octave() -> None:
    assert octave_shift_semitones(100.0, 500.0) == -12
    assert octave_shift_semitones(500.0, 100.0) == 12


def test_invalid_registers_fall_back_to_no_shift() -> None:
    assert octave_shift_semitones(0.0, 220.0) == 0
    assert octave_shift_semitones(220.0, -1.0) == 0
    assert octave_shift_semitones(float("nan"), 220.0) == 0
