from core.soft_constraints.baroque import apply_baroque_preferences
from core.soft_constraints.contemporary import apply_contemporary_preferences
from core.soft_constraints.jazz import apply_jazz_preferences
from ortools.sat.python import cp_model
from core.variables import create_variables
from core.constraints.harmony import (
    apply_scale_constraint, 
    apply_chord_constraints, 
    apply_tonic_constraint, 
    apply_degree_to_root_constraint, 
    apply_chord_progression_constraint,
    apply_leading_tone_resolution
)
from core.constraints.counterpoint import (
    apply_voice_leading_constraints, 
    apply_consonance_constraints, 
    apply_no_parallel_constraints
)
from core.constraints.rhythm import apply_rhythm_constraints, apply_metric_accent_constraints

class MusicModel:
    def __init__(self, n_measures, key='C', mode='major', style='jazz'):
        self.model = cp_model.CpModel()
        self.n_measures = n_measures
        self.key_name = key
        self.mode = mode
        self.style = style
        self.key_pc = self._key_to_pc(key)
        
        self.beats_per_measure = 3 if style == 'baroque' else 4
        self.vars = create_variables(self.model, n_measures, beats_per_measure=self.beats_per_measure)

    def _key_to_pc(self, key):
        keys = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 
                'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
        return keys.get(key, 0)

    def apply_all_constraints(self):
        apply_scale_constraint(self.model, self.vars, self.key_pc, self.mode)
        apply_degree_to_root_constraint(self.model, self.vars, self.key_pc, self.mode, style=self.style)
        apply_chord_constraints(self.model, self.vars)
        apply_chord_progression_constraint(self.model, self.vars)
        apply_tonic_constraint(self.model, self.vars, self.key_pc)
        
        if self.style != 'contemporary':
            apply_leading_tone_resolution(self.model, self.vars, self.key_pc, self.mode)
            
        apply_voice_leading_constraints(self.model, self.vars)
        apply_consonance_constraints(self.model, self.vars)
        apply_no_parallel_constraints(self.model, self.vars)
        apply_rhythm_constraints(self.model, self.vars)
        apply_metric_accent_constraints(self.model, self.vars)
        
        costs = []
        if self.style == 'jazz':
            costs = apply_jazz_preferences(self.model, self.vars)
        elif self.style == 'baroque':
            costs = apply_baroque_preferences(self.model, self.vars)
        elif self.style == 'contemporary':
            costs = apply_contemporary_preferences(self.model, self.vars)
            
        if costs:
            self.model.Minimize(sum(costs))

    def solve(self, timeout_seconds=60):
        self.apply_all_constraints()
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = timeout_seconds
        # REMOVE PROGRESS LOGS TO SPEED UP
        solver.parameters.log_search_progress = False
        
        status = solver.Solve(self.model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self._extract_solution(solver)
        else:
            return None

    def _extract_solution(self, solver):
        solution = {
            'pitches': {},
            'roots': [],
            'qualities': [],
            'degrees': []
        }
        
        n_ticks = self.vars['n_ticks']
        
        for (v, t), var in self.vars['pitches'].items():
            solution['pitches'][(v, t)] = solver.Value(var)
        
        for t in range(n_ticks):
            solution['roots'].append(solver.Value(self.vars['roots'][t]))
            solution['qualities'].append(solver.Value(self.vars['qualities'][t]))
            solution['degrees'].append(solver.Value(self.vars['degrees'][t]))
            
        return solution
