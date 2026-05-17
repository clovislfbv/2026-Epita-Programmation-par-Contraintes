import argparse
import os
from core.model import MusicModel
from export.midi_export import export_to_midi
from evaluation.rule_checker import evaluate_solution, print_report

def main():
    parser = argparse.ArgumentParser(description="Multi-style Music Generator using CP-SAT")
    parser.add_argument("--measures", type=int, default=8)
    parser.add_argument("--key", type=str, default="C")
    parser.add_argument("--mode", type=str, default="major")
    parser.add_argument("--output", type=str, default="output.mid")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--style", choices=['jazz', 'baroque', 'contemporary'], default='jazz')
    parser.add_argument("--eval", action="store_true")
    
    args = parser.parse_args()

    model = MusicModel(n_measures=args.measures, key=args.key, mode=args.mode, style=args.style)
    solution = model.solve(timeout_seconds=args.timeout)
    
    if solution:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        export_to_midi(solution, args.output, style=args.style)
        
        if args.eval:
            report = evaluate_solution(solution, style=args.style, key=args.key)
            print_report(report)
    else:
        print("Failed to generate a valid musical sequence.")

if __name__ == "__main__":
    main()
