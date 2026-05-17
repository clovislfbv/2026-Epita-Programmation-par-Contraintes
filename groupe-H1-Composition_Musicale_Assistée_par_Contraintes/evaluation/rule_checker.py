import numpy as np

def check_consonance(solution):
    pitches = solution['pitches']
    n_ticks = max(t for (v, t) in pitches.keys()) + 1
    
    consonant_intervals = {0, 3, 4, 7, 8, 9, 10}
    checks = 0
    consonances = 0
    
    for t in range(n_ticks):
        for v1 in range(4):
            for v2 in range(v1 + 1, 4):
                p1 = pitches[(v1, t)]
                p2 = pitches[(v2, t)]
                
                if p1 > 0 and p2 > 0:
                    checks += 1
                    interval = abs(p1 - p2) % 12
                    if interval in consonant_intervals:
                        consonances += 1
                        
    return (consonances / checks * 100) if checks > 0 else 100.0

def check_leading_tone_resolution(solution, key_pc=0):
    lt_pc = (key_pc + 11) % 12
    tonic_pc = key_pc % 12
    
    pitches = solution['pitches']
    n_ticks = max(t for (v, t) in pitches.keys()) + 1
    
    checks = 0
    resolutions = 0
    
    for v in range(4):
        for t in range(n_ticks - 1):
            p1 = pitches[(v, t)]
            p2 = pitches[(v, t+1)]
            
            if p1 > 0 and (p1 % 12 == lt_pc):
                if p2 > 0:
                    checks += 1
                    if p2 % 12 == tonic_pc:
                        resolutions += 1
                        
    return (resolutions / checks * 100) if checks > 0 else 100.0

def check_activity(solution):
    pitches = solution['pitches']
    n_ticks = max(t for (v, t) in pitches.keys()) + 1
    
    activities = []
    for v in range(4):
        playing = sum(1 for t in range(n_ticks) if pitches[(v, t)] > 0)
        activities.append(playing / n_ticks * 100)
        
    return np.mean(activities)

def check_diversity(solution):
    pitches = solution['pitches']
    all_notes = [p for p in pitches.values() if p > 0]
    if not all_notes: return 0.0
    
    unique_notes = len(set(all_notes))
    return (unique_notes / len(all_notes) * 100)

def evaluate_solution(solution, style="unknown", key="C"):
    keys = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 
            'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
    k_pc = keys.get(key, 0)
    
    report = {
        "style": style,
        "consonance_rate": check_consonance(solution),
        "leading_tone_resolution": check_leading_tone_resolution(solution, k_pc),
        "avg_voice_activity": check_activity(solution),
        "melodic_diversity": check_diversity(solution)
    }
    return report

def print_report(report):
    print(f"\n--- RAPPORT D'ÉVALUATION ({report['style'].upper()}) ---")
    print(f"Taux de consonance :          {report['consonance_rate']:.1f}%")
    print(f"Résolution de la sensible :   {report['leading_tone_resolution']:.1f}%")
    print(f"Activité moyenne des voix :   {report['avg_voice_activity']:.1f}%")
    print(f"Diversité mélodique :         {report['melodic_diversity']:.1f}%")
    print("-" * 35)
