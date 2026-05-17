from midiutil import MIDIFile

def export_to_midi(solution, output_path, ticks_per_beat=2, style='jazz'):
    pitches = solution['pitches']
    
    n_ticks = max(t for (v, t) in pitches.keys()) + 1
    n_voices = max(v for (v, t) in pitches.keys()) + 1
    
    midi = MIDIFile(n_voices)
    tempo = 120 if style != 'baroque' else 100
    time = 0

    if style == 'baroque':
        INSTRUMENTS = {0: 6, 1: 40, 2: 41, 3: 42}
        TRACK_NAMES = {0: "Harpsichord", 1: "Violin", 2: "Viola", 3: "Cello"}
        numerator, denominator = 3, 2
    elif style == 'contemporary':
        INSTRUMENTS = {0: 0, 1: 0, 2: 0, 3: 0}
        TRACK_NAMES = {0: "Piano Solo", 1: "Piano Acc 1", 2: "Piano Acc 2", 3: "Piano Bass"}
        numerator, denominator = 4, 2
    else:
        INSTRUMENTS = {0: 66, 1: 26, 2: 26, 3: 32}
        TRACK_NAMES = {0: "Sax Solo", 1: "Guitar Comp 1", 2: "Guitar Comp 2", 3: "Acoustic Bass"}
        numerator, denominator = 4, 2

    for v in range(n_voices):
        track = v
        channel = v
        midi.addTrackName(track, time, TRACK_NAMES.get(v, f"Voice {v}"))
        midi.addTempo(track, time, tempo)
        midi.addTimeSignature(track, time, numerator, denominator, 24)
        midi.addProgramChange(track, channel, time, INSTRUMENTS.get(v, 0))

        last_pitch = -1
        current_note_start = -1

        for t in range(n_ticks):
            pitch = pitches[(v, t)]

            if pitch != last_pitch:
                if last_pitch > 0:
                    duration_ticks = t - current_note_start
                    duration_beats = duration_ticks * (1.0 / ticks_per_beat)
                    start_beats = current_note_start * (1.0 / ticks_per_beat)
                    
                    if v == 0: volume = 110
                    elif v == 3: volume = 70
                    else: volume = 60
                    
                    midi.addNote(track, channel, last_pitch, start_beats, duration_beats, volume)

                current_note_start = t
                last_pitch = pitch

        if last_pitch > 0:
            duration_ticks = n_ticks - current_note_start
            duration_beats = duration_ticks * (1.0 / ticks_per_beat)
            start_beats = current_note_start * (1.0 / ticks_per_beat)
            volume = 90 if v == 0 else 60
            midi.addNote(track, channel, last_pitch, start_beats, duration_beats, volume)

    with open(output_path, "wb") as output_file:
        midi.writeFile(output_file)
