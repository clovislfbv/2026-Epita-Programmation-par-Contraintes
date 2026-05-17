from core.constants import SCALES, CHORD_FORMULAS, CHORD_QUALITIES, VOICES, MAJ, MIN, DOM7, DIM, MAJ7, MIN7

def apply_scale_constraint(model, vars, key_pc, mode='major'):
    scale = SCALES.get(mode, SCALES['major'])
    allowed_pcs = [(p + key_pc) % 12 for p in scale]
    
    for (v, t), pitch_var in vars['pitches'].items():
        is_playing = model.NewBoolVar(f'is_playing_v{v}_t{t}')
        model.Add(pitch_var > 0).OnlyEnforceIf(is_playing)
        model.Add(pitch_var == 0).OnlyEnforceIf(is_playing.Not())
        
        pitch_pc = model.NewIntVar(0, 11, f'pc_v{v}_t{t}')
        model.AddModuloEquality(pitch_pc, pitch_var, 12).OnlyEnforceIf(is_playing)
        model.AddAllowedAssignments([pitch_pc], [(pc,) for pc in allowed_pcs]).OnlyEnforceIf(is_playing)

def apply_chord_constraints(model, vars):
    n_ticks = vars['n_ticks']
    allowed_tuples = []
    for r in range(12):
        for q_idx, q_name in enumerate(['MAJ', 'MIN', 'DOM7', 'DIM', 'MAJ7', 'MIN7']):
            formula = CHORD_FORMULAS[CHORD_QUALITIES[q_idx]]
            for interval in formula:
                allowed_tuples.append((r, q_idx, (r + interval) % 12))

    for t in range(n_ticks):
        root = vars['roots'][t]
        quality = vars['qualities'][t]
        for v in VOICES:
            pitch = vars['pitches'][(v, t)]
            is_playing = model.NewBoolVar(f'is_playing_v{v}_t{t}_chord')
            model.Add(pitch > 0).OnlyEnforceIf(is_playing)
            model.Add(pitch == 0).OnlyEnforceIf(is_playing.Not())
            pitch_pc = model.NewIntVar(0, 11, f'pc_v{v}_t{t}_chord')
            model.AddModuloEquality(pitch_pc, pitch, 12).OnlyEnforceIf(is_playing)
            model.AddAllowedAssignments([root, quality, pitch_pc], allowed_tuples).OnlyEnforceIf(is_playing)

def apply_degree_to_root_constraint(model, vars, key_pc, mode='major', style='jazz'):
    n_ticks = vars['n_ticks']
    scale = SCALES.get(mode, SCALES['major'])
    
    if style == 'baroque':
        degree_to_quality = {1: 0, 2: 1, 3: 1, 4: 0, 5: 0, 6: 1, 7: 3}
    else:
        degree_to_quality = {1: 4, 2: 5, 3: 5, 4: 4, 5: 2, 6: 5, 7: 3}
    
    for t in range(n_ticks):
        degree = vars['degrees'][t]
        root = vars['roots'][t]
        quality = vars['qualities'][t]
        allowed_triplets = []
        for d in range(1, 8):
            root_pc = (key_pc + scale[d-1]) % 12
            q = degree_to_quality[d]
            allowed_triplets.append((d, root_pc, q))
        model.AddAllowedAssignments([degree, root, quality], allowed_triplets)

def apply_chord_progression_constraint(model, vars):
    allowed_transitions = [(2, 5), (5, 1), (1, 2), (1, 4), (4, 5), (6, 2), (1, 6)]
    n_beats = vars['n_beats']
    for b in range(n_beats - 1):
        t1, t2 = b * 2, (b + 1) * 2
        d1, d2 = vars['degrees'][t1], vars['degrees'][t2]
        is_change = model.NewBoolVar(f'deg_change_b{b}')
        model.Add(d1 != d2).OnlyEnforceIf(is_change)
        model.Add(d1 == d2).OnlyEnforceIf(is_change.Not())
        is_classic = model.NewBoolVar(f'classic_trans_b{b}')
        model.AddAllowedAssignments([d1, d2], allowed_transitions).OnlyEnforceIf(is_classic)
        model.AddBoolOr([is_change.Not(), is_classic])

def apply_tonic_constraint(model, vars, key_pc):
    n_ticks = vars['n_ticks']
    model.Add(vars['degrees'][0] == 1)
    model.Add(vars['degrees'][n_ticks - 1] == 1)
    model.Add(vars['roots'][0] == key_pc)
    model.Add(vars['roots'][n_ticks - 1] == key_pc)

def apply_leading_tone_resolution(model, vars, key_pc, mode='major'):
    scale = SCALES.get(mode, SCALES['major'])
    if len(scale) < 7: return
    leading_tone_pc = (key_pc + scale[6]) % 12
    tonic_pc = (key_pc + scale[0]) % 12
    n_ticks = vars['n_ticks']
    for v in VOICES:
        for t in range(n_ticks - 1):
            p1, p2 = vars['pitches'][(v, t)], vars['pitches'][(v, t+1)]
            p1_pc = model.NewIntVar(0, 11, f'lt_pc_v{v}_t{t}')
            model.AddModuloEquality(p1_pc, p1, 12)
            p2_pc = model.NewIntVar(0, 11, f'lt_res_pc_v{v}_t{t}')
            model.AddModuloEquality(p2_pc, p2, 12)
            is_lt = model.NewBoolVar(f'is_lt_v{v}_t{t}')
            model.Add(p1_pc == leading_tone_pc).OnlyEnforceIf(is_lt)
            model.Add(p1_pc != leading_tone_pc).OnlyEnforceIf(is_lt.Not())
            is_playing_next = model.NewBoolVar(f'playing_next_v{v}_t{t}')
            model.Add(p2 > 0).OnlyEnforceIf(is_playing_next)
            model.Add(p2 == 0).OnlyEnforceIf(is_playing_next.Not())
            model.Add(p2_pc == tonic_pc).OnlyEnforceIf([is_lt, is_playing_next])
