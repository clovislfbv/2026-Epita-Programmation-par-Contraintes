from core.constants import VOICES, MAJ, MIN, DIM, SOPRANO, BASS_VOICE

def apply_baroque_preferences(model, vars):
    n_ticks = vars['n_ticks']
    costs = []
    
    for t in range(n_ticks):
        quality = vars['qualities'][t]
        is_triad = model.NewBoolVar(f'is_triad_t{t}')
        model.AddAllowedAssignments([quality], [(MAJ,), (MIN,), (DIM,)]) \
            .OnlyEnforceIf(is_triad)
        costs.append((1 - is_triad) * 150)

    for t in range(n_ticks - 1):
        s1, s2 = vars['pitches'][(SOPRANO, t)], vars['pitches'][(SOPRANO, t+1)]
        b1, b2 = vars['pitches'][(BASS_VOICE, t)], vars['pitches'][(BASS_VOICE, t+1)]
        
        s_up = model.NewBoolVar(f's_up_t{t}')
        model.Add(s2 > s1).OnlyEnforceIf(s_up)
        s_down = model.NewBoolVar(f's_down_t{t}')
        model.Add(s2 < s1).OnlyEnforceIf(s_down)
        
        b_up = model.NewBoolVar(f'b_up_t{t}')
        model.Add(b2 > b1).OnlyEnforceIf(b_up)
        b_down = model.NewBoolVar(f'b_down_t{t}')
        model.Add(b2 < b1).OnlyEnforceIf(b_down)
        
        is_contrary = model.NewBoolVar(f'is_contrary_t{t}')
        c1 = model.NewBoolVar(f'c1_t{t}')
        model.AddBoolAnd([s_up, b_down]).OnlyEnforceIf(c1)
        c2 = model.NewBoolVar(f'c2_t{t}')
        model.AddBoolAnd([s_down, b_up]).OnlyEnforceIf(c2)
        model.AddBoolOr([c1, c2]).OnlyEnforceIf(is_contrary)
        
        s_moved = model.NewBoolVar(f's_moved_t{t}')
        model.Add(s1 != s2).OnlyEnforceIf(s_moved)
        b_moved = model.NewBoolVar(f'b_moved_t{t}')
        model.Add(b1 != b2).OnlyEnforceIf(b_moved)
        
        both_moved = model.NewBoolVar(f'both_moved_t{t}')
        model.AddBoolAnd([s_moved, b_moved]).OnlyEnforceIf(both_moved)
        
        costs.append((both_moved - is_contrary) * 80)

    for v in VOICES:
        for t in range(n_ticks - 1):
            p1, p2 = vars['pitches'][(v, t)], vars['pitches'][(v, t+1)]
            
            diff = model.NewIntVar(0, 12, f'b_diff_v{v}_t{t}')
            model.AddAbsEquality(diff, p2 - p1)
            is_jump = model.NewBoolVar(f'b_jump_v{v}_t{t}')
            model.Add(diff > 2).OnlyEnforceIf(is_jump)
            costs.append(is_jump * 40)
            
            is_silent = model.NewBoolVar(f'b_silent_v{v}_t{t}')
            model.Add(p1 == 0).OnlyEnforceIf(is_silent)
            costs.append(is_silent * 30)

    return costs
