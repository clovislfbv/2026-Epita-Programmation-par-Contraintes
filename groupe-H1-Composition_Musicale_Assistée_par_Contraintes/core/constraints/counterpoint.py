from core.constants import VOICES, SOPRANO, ALTO, TENOR, BASS, CONSONANT_INTERVALS

def apply_voice_leading_constraints(model, vars):
    n_ticks = vars['n_ticks']
    for t in range(n_ticks):
        for i in range(len(VOICES) - 1):
            v_high, v_low = VOICES[i], VOICES[i+1]
            p_high, p_low = vars['pitches'][(v_high, t)], vars['pitches'][(v_low, t)]
            
            h_play = model.NewBoolVar(f'h_p_{v_high}_{v_low}_t{t}')
            model.Add(p_high > 0).OnlyEnforceIf(h_play)
            model.Add(p_high == 0).OnlyEnforceIf(h_play.Not())
            l_play = model.NewBoolVar(f'l_p_{v_high}_{v_low}_t{t}')
            model.Add(p_low > 0).OnlyEnforceIf(l_play)
            model.Add(p_low == 0).OnlyEnforceIf(l_play.Not())
            
            both = model.NewBoolVar(f'both_p_{v_high}_{v_low}_t{t}')
            model.AddBoolAnd([h_play, l_play]).OnlyEnforceIf(both)
            model.AddBoolOr([h_play.Not(), l_play.Not()]).OnlyEnforceIf(both.Not())

            model.Add(p_high >= p_low).OnlyEnforceIf(both)

def apply_consonance_constraints(model, vars):
    n_ticks = vars['n_ticks']
    for t in range(n_ticks):
        for i in range(len(VOICES)):
            for j in range(i + 1, len(VOICES)):
                v1, v2 = VOICES[i], VOICES[j]
                p1, p2 = vars['pitches'][(v1, t)], vars['pitches'][(v2, t)]
                
                p1_p = model.NewBoolVar(f'p1_p_{v1}_{v2}_t{t}')
                model.Add(p1 > 0).OnlyEnforceIf(p1_p)
                model.Add(p1 == 0).OnlyEnforceIf(p1_p.Not())
                p2_p = model.NewBoolVar(f'p2_p_{v1}_{v2}_t{t}')
                model.Add(p2 > 0).OnlyEnforceIf(p2_p)
                model.Add(p2 == 0).OnlyEnforceIf(p2_p.Not())
                both = model.NewBoolVar(f'c_both_{v1}_{v2}_t{t}')
                model.AddBoolAnd([p1_p, p2_p]).OnlyEnforceIf(both)
                model.AddBoolOr([p1_p.Not(), p2_p.Not()]).OnlyEnforceIf(both.Not())

                diff = model.NewIntVar(0, 127, f'diff_{v1}_{v2}_t{t}')
                model.Add(diff == p1 - p2).OnlyEnforceIf(both)
                
                pc_diff = model.NewIntVar(0, 11, f'pc_diff_{v1}_{v2}_t{t}')
                model.AddModuloEquality(pc_diff, diff, 12).OnlyEnforceIf(both)
                
                model.AddAllowedAssignments([pc_diff], [(c,) for c in [0, 3, 4, 7, 8, 9, 10]]).OnlyEnforceIf(both)

def apply_no_parallel_constraints(model, vars):
    n_ticks = vars['n_ticks']
    for t in range(n_ticks - 1):
        for i in range(len(VOICES)):
            for j in range(i + 1, len(VOICES)):
                v1, v2 = VOICES[i], VOICES[j]
                p1_t, p1_n = vars['pitches'][(v1, t)], vars['pitches'][(v1, t+1)]
                p2_t, p2_n = vars['pitches'][(v2, t)], vars['pitches'][(v2, t+1)]
                
                act = [model.NewBoolVar(f'a_{v1}_{v2}_{t}_{k}') for k in range(4)]
                model.Add(p1_t > 0).OnlyEnforceIf(act[0])
                model.Add(p1_n > 0).OnlyEnforceIf(act[1])
                model.Add(p2_t > 0).OnlyEnforceIf(act[2])
                model.Add(p2_n > 0).OnlyEnforceIf(act[3])
                
                all_a = model.NewBoolVar(f'all_a_{v1}_{v2}_{t}')
                model.AddBoolAnd(act).OnlyEnforceIf(all_a)
                model.AddBoolOr([a.Not() for a in act]).OnlyEnforceIf(all_a.Not())
                
                d_t = model.NewIntVar(0, 127, f'dt_{v1}_{v2}_{t}')
                model.Add(d_t == p1_t - p2_t).OnlyEnforceIf(all_a)
                d_n = model.NewIntVar(0, 127, f'dn_{v1}_{v2}_{t}')
                model.Add(d_n == p1_n - p2_n).OnlyEnforceIf(all_a)
                
                para = model.NewBoolVar(f'para_{v1}_{v2}_{t}')
                model.Add(d_t == d_n).OnlyEnforceIf([all_a, para])
                model.Add(d_t != d_n).OnlyEnforceIf([all_a, para.Not()])
                
                pc = model.NewIntVar(0, 11, f'pc_{v1}_{v2}_{t}')
                model.AddModuloEquality(pc, d_t, 12).OnlyEnforceIf(all_a)
                
                forb = model.NewBoolVar(f'forb_{v1}_{v2}_{t}')
                model.AddAllowedAssignments([pc], [(0,), (7,)]).OnlyEnforceIf(forb)
                
                mov = model.NewBoolVar(f'mov_{v1}_{v2}_{t}')
                model.Add(p1_t != p1_n).OnlyEnforceIf(mov)
                
                model.AddImplication(forb, mov.Not()).OnlyEnforceIf(all_a)
