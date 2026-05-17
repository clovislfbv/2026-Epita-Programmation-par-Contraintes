from core.constants import MAJ7, MIN7, DOM7, VOICES, BASS_VOICE, MELODY_VOICE, COMPING_VOICES

def apply_jazz_preferences(model, vars):
    n_ticks = vars['n_ticks']
    costs = []
    
    for t in range(n_ticks):
        is_7th = model.NewBoolVar(f'is_7th_t{t}')
        model.AddAllowedAssignments([vars['qualities'][t]], [(DOM7,), (MAJ7,), (MIN7,)]) \
            .OnlyEnforceIf(is_7th)
        costs.append((1 - is_7th) * 60)

    for t in range(n_ticks - 1):
        if t % 2 != 0:
            next_root = vars['roots'][t+1]
            bass_pitch = vars['pitches'][(BASS_VOICE, t)]
            
            is_approach = model.NewBoolVar(f'bass_approach_t{t}')
            bass_pc = model.NewIntVar(0, 11, f'bass_pc_t{t}')
            model.AddModuloEquality(bass_pc, bass_pitch, 12)
            
            diff = model.NewIntVar(-11, 11, f'bass_root_diff_t{t}')
            model.Add(diff == bass_pc - next_root)
            abs_diff = model.NewIntVar(0, 11, f'bass_root_abs_diff_t{t}')
            model.AddAbsEquality(abs_diff, diff)
            
            model.AddAllowedAssignments([abs_diff], [(1,), (5,), (7,)]).OnlyEnforceIf(is_approach)
            costs.append((1 - is_approach) * 40)

    for t in range(1, n_ticks):
        if t % 2 != 0:
            p1, p2 = vars['pitches'][(MELODY_VOICE, t-1)], vars['pitches'][(MELODY_VOICE, t)]
            is_start = model.NewBoolVar(f'sax_start_off_t{t}')
            model.Add(p2 != p1).OnlyEnforceIf(is_start)
            model.Add(p2 != 0).OnlyEnforceIf(is_start)
            costs.append((1 - is_start) * 20)

    for v in COMPING_VOICES:
        for t in range(n_ticks):
            pitch, root = vars['pitches'][(v, t)], vars['roots'][t]
            is_playing = model.NewBoolVar(f'comp_p_v{v}_t{t}')
            model.Add(pitch > 0).OnlyEnforceIf(is_playing)
            
            pitch_pc = model.NewIntVar(0, 11, f'comp_pc_v{v}_t{t}')
            model.AddModuloEquality(pitch_pc, pitch, 12).OnlyEnforceIf(is_playing)
            diff_pc = model.NewIntVar(-11, 11, f'c_d_pc_v{v}_t{t}')
            model.Add(diff_pc == pitch_pc - root).OnlyEnforceIf(is_playing)
            rel_pc = model.NewIntVar(0, 11, f'c_r_pc_v{v}_t{t}')
            model.AddModuloEquality(rel_pc, diff_pc + 12, 12).OnlyEnforceIf(is_playing)
            
            is_shell = model.NewBoolVar(f'is_shell_v{v}_t{t}')
            model.AddAllowedAssignments([rel_pc], [(3,), (4,), (10,), (11,)]).OnlyEnforceIf(is_shell)
            costs.append((1 - is_shell) * 60)

    return costs
