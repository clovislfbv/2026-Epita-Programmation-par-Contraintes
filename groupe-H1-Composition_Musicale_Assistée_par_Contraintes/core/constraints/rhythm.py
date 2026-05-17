from core.constants import VOICES

def apply_rhythm_constraints(model, vars):
    n_ticks = vars['n_ticks']
    
    for v in VOICES:
        activity = []
        for t in range(n_ticks):
            is_playing = model.NewBoolVar(f'active_v{v}_t{t}')
            model.Add(vars['pitches'][(v, t)] > 0).OnlyEnforceIf(is_playing)
            model.Add(vars['pitches'][(v, t)] == 0).OnlyEnforceIf(is_playing.Not())
            activity.append(is_playing)
        
        model.Add(sum(activity) >= int(n_ticks * 0.6))

def apply_metric_accent_constraints(model, vars):
    n_ticks = vars['n_ticks']
    for t in range(1, n_ticks):
        if t % 2 != 0:
            model.Add(vars['roots'][t] == vars['roots'][t-1])
            model.Add(vars['qualities'][t] == vars['qualities'][t-1])
            model.Add(vars['degrees'][t] == vars['degrees'][t-1])

def apply_total_duration_constraint(model, vars, expected_sixteenths):
    pass
