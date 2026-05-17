from ortools.sat.python import cp_model
from core.constants import VOICES, CHORD_QUALITIES, TESSITURAS, ALLOWED_DURATIONS, SILENCE

def create_variables(model, n_measures, beats_per_measure=4):

    TICKS_PER_BEAT = 2
    n_beats = n_measures * beats_per_measure
    n_ticks = n_beats * TICKS_PER_BEAT
    
    pitches = {}
    
    for v in VOICES:
        min_pitch, max_pitch = TESSITURAS[v]
        for t in range(n_ticks):
            domain = cp_model.Domain.FromIntervals([[SILENCE, SILENCE], [min_pitch, max_pitch]])
            pitches[(v, t)] = model.NewIntVarFromDomain(domain, f'pitch_v{v}_t{t}')
            
    roots = []
    qualities = []
    degrees = []
    
    for t in range(n_ticks):
        roots.append(model.NewIntVar(0, 11, f'root_t{t}'))
        qualities.append(model.NewIntVar(0, len(CHORD_QUALITIES) - 1, f'quality_t{t}'))
        degrees.append(model.NewIntVar(1, 7, f'degree_t{t}'))
        
    return {
        'pitches': pitches,
        'roots': roots,
        'qualities': qualities,
        'degrees': degrees,
        'n_ticks': n_ticks,
        'n_beats': n_beats,
        'n_measures': n_measures,
        'beats_per_measure': beats_per_measure,
        'ticks_per_beat': TICKS_PER_BEAT
    }
