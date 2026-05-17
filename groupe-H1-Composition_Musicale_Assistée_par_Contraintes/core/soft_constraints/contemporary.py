from core.constants import VOICES, DOM7, MAJ7, MIN7, DIM, MELODY_VOICE

def apply_contemporary_preferences(model, vars):
    n_ticks = vars['n_ticks']
    costs = []
    
    for t in range(n_ticks):
        pitch = vars['pitches'][(MELODY_VOICE, t)]
        root = vars['roots'][t]
        
        is_playing = model.NewBoolVar(f'c_play_v0_t{t}')
        model.Add(pitch > 0).OnlyEnforceIf(is_playing)
        
        pitch_pc = model.NewIntVar(0, 11, f'c_pc_v0_t{t}')
        model.AddModuloEquality(pitch_pc, pitch, 12).OnlyEnforceIf(is_playing)
        
        is_root = model.NewBoolVar(f'is_root_v0_t{t}')
        model.Add(pitch_pc == root).OnlyEnforceIf(is_root)
        costs.append(is_root * 100)

    for v in VOICES:
        for t in range(n_ticks - 2):
            active = [model.NewBoolVar(f'a_v{v}_t{t+i}') for i in range(3)]
            for i in range(3):
                model.Add(vars['pitches'][(v, t+i)] > 0).OnlyEnforceIf(active[i])
                model.Add(vars['pitches'][(v, t+i)] == 0).OnlyEnforceIf(active[i].Not())
            
            is_linear = model.NewBoolVar(f'is_linear_v{v}_t{t}')
            model.AddBoolAnd(active).OnlyEnforceIf(is_linear)
            costs.append(is_linear * 40)

    for v in VOICES:
        for t in range(n_ticks - 1):
            p1, p2 = vars['pitches'][(v, t)], vars['pitches'][(v, t+1)]
            p1_play = model.NewBoolVar(f'p1_c_v{v}_t{t}')
            model.Add(p1 > 0).OnlyEnforceIf(p1_play)
            p2_play = model.NewBoolVar(f'p2_c_v{v}_t{t}')
            model.Add(p2 > 0).OnlyEnforceIf(p2_play)
            both = model.NewBoolVar(f'both_c_v{v}_t{t}')
            model.AddBoolAnd([p1_play, p2_play]).OnlyEnforceIf(both)

            diff = model.NewIntVar(0, 24, f'c_diff_v{v}_t{t}')
            model.AddAbsEquality(diff, p2 - p1).OnlyEnforceIf(both)
            
            is_step = model.NewBoolVar(f'is_step_c_v{v}_t{t}')
            model.Add(diff < 6).OnlyEnforceIf(is_step)
            costs.append(is_step * 50)

    return costs
