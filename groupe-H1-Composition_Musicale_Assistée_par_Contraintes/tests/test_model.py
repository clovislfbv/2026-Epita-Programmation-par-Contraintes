import pytest
from core.model import MusicModel
from core.constants import VOICES

def test_model_initialization():
    model = MusicModel(n_measures=2)
    assert model.n_measures == 2
    assert model.key_name == 'C'
    assert len(model.vars['pitches']) == 4 * 2 * 4 * 2

def test_model_solve():
    model = MusicModel(n_measures=1)
    solution = model.solve(timeout_seconds=10)
    assert solution is not None
    assert 'pitches' in solution
    assert len(solution['pitches']) == 4 * 1 * 4 * 2

def test_voice_leading_constraint():
    model = MusicModel(n_measures=1)
    solution = model.solve(timeout_seconds=10)
    
    from core.constants import SOPRANO, ALTO, TENOR, BASS
    n_ticks = model.vars['n_ticks']
    for t in range(n_ticks):
        p_sop = solution['pitches'][(SOPRANO, t)]
        p_alt = solution['pitches'][(ALTO, t)]
        p_ten = solution['pitches'][(TENOR, t)]
        p_bas = solution['pitches'][(BASS, t)]
        
        if p_sop > 0 and p_alt > 0:
            assert p_sop >= p_alt
        if p_alt > 0 and p_ten > 0:
            assert p_alt >= p_ten
        if p_ten > 0 and p_bas > 0:
            assert p_ten >= p_bas

def test_leading_tone_resolution():
    model = MusicModel(n_measures=1, key='C', mode='major')
    solution = model.solve(timeout_seconds=10)
    
    n_ticks = model.vars['n_ticks']
    for v in range(4):
        for t in range(n_ticks - 1):
            p1 = solution['pitches'][(v, t)]
            p2 = solution['pitches'][(v, t+1)]
            if p1 > 0 and (p1 % 12 == 11) and p2 > 0:
                assert p2 % 12 == 0

def test_metric_accents():
    model = MusicModel(n_measures=1)
    solution = model.solve(timeout_seconds=10)
    
    n_ticks = model.vars['n_ticks']
    for t in range(1, n_ticks):
        if t % 2 != 0:
            assert solution['roots'][t] == solution['roots'][t-1]
            assert solution['qualities'][t] == solution['qualities'][t-1]
