"""Auto key matching for covers.

Only whole-octave shifts are harmonically safe: any other semitone offset
transposes the vocal melody out of the instrumental's key. (Applio's own
--proposed_pitch applies a fractional shift toward a fixed target frequency,
which detunes the vocal against the backing track, so we compute the shift
ourselves from the two registers.)
"""

import math

_MAX_OCTAVES = 1


def octave_shift_semitones(voice_f0_hz: float, source_f0_hz: float) -> int:
    """Semitone shift (0 or ±12) moving the source vocal register onto the
    voice model's register. Returns 0 when either register is unknown/invalid."""
    if voice_f0_hz <= 0 or source_f0_hz <= 0:
        return 0
    if math.isnan(voice_f0_hz) or math.isnan(source_f0_hz):
        return 0
    octaves = round(math.log2(voice_f0_hz / source_f0_hz))
    octaves = max(-_MAX_OCTAVES, min(_MAX_OCTAVES, octaves))
    return 12 * octaves
