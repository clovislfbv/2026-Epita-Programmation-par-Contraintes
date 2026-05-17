{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    (pkgs.python3.withPackages (ps: with ps; [
      fastapi
      uvicorn
      ortools
      shapely
      pydantic
      numpy
    ]))
  ];

  shellHook = ''
    echo "Drone Delivery CP-SAT — env ready"
    echo "Run: cd backend && uvicorn main:app --reload"
  '';
}
