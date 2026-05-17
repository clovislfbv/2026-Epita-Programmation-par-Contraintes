## K1 - Planification urbaine et placement d'infrastructures

La planification urbaine sous contraintes consiste a determiner l'emplacement optimal d'infrastructures (hopitaux, ecoles, centres commerciaux, parcs, stations de recharge) dans une zone urbaine, en maximisant la couverture de la population sous des contraintes de budget, de superficie disponible, de distance maximum aux residents, et de compatibilite entre infrastructures. C'est un probleme de theorie de la localisation (p-median, p-center, MCLP) directement modelisable en CP-SAT avec des variables binaires de localisation et des contraintes de couverture.

### Objectifs

- Modeliser le placement d'infrastructures comme un probleme de localisation (p-median/MCLP) avec CP-SAT
- Implementer les contraintes de budget, de superficie, de distance maximum et de compatibilite entre sites
- Ajouter les contraintes de couverture equitable (minimiser la variance d'accessibilite entre quartiers)
- Evaluer sur des donnees urbaines reelles (OpenStreetMap, donnees INSEE) et des benchmarks synthetiques
- Visualiser les solutions sur une carte (folium, geopandas) pour faciliter l'analyse

### Notebooks CoursIA pertinents

| Notebook                        | Chemin                                                                                                                                                                                | Pertinence               |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| CSP-5 Optimization              | [Search/Part2-CSP/CSP-5-Optimization.ipynb](https://github.com/jsboige/CoursIA/blob/main/MyIA.AI.Notebooks/Search/Part2-CSP/CSP-5-Optimization.ipynb)                                 | Allocation, localisation |
| CSP-1 Fondamentaux              | [Search/Part2-CSP/CSP-1-Fundamentals.ipynb](https://github.com/jsboige/CoursIA/blob/main/MyIA.AI.Notebooks/Search/Part2-CSP/CSP-1-Fundamentals.ipynb)                                 | Modelisation CSP         |
| Search-9 Programmation lineaire | [Search/Part1-Foundations/Search-9-LinearProgramming.ipynb](https://github.com/jsboige/CoursIA/blob/main/MyIA.AI.Notebooks/Search/Part1-Foundations/Search-9-LinearProgramming.ipynb) | PLNE, localisation       |
| CSP-7 Soft Constraints          | [Search/Part2-CSP/CSP-7-Soft.ipynb](https://github.com/jsboige/CoursIA/blob/main/MyIA.AI.Notebooks/Search/Part2-CSP/CSP-7-Soft.ipynb)                                                 | Equite, preferences      |

### References externes

- Church, R., & ReVelle, C. (1974). "The Maximal Covering Location Problem." _Papers of the Regional Science Association_, 32, 101-118. [Springer](https://link.springer.com/chapter/10.1007/978-3-642-51081-8_6)
- Current, J., et al. (2002). "Facility Location: Applications and Theory." _Springer_. [Springer](https://link.springer.com/book/10.1007/978-3-642-56038-7)
- Daskin, M.S. (2013). "Network and Discrete Location." _Wiley_. [Wiley](https://www.wiley.com/en-us/Network+and+Discrete+Location%3A+Models%2C+Algorithms%2C+and+Applications%2C+2nd+Edition-p-9780470905364)
- Murray, A.T. (2016). "Maximal Coverage Location Problem: Impacts, Significance, and Evolution." _International Regional Science Review_, 39(1), 5-27. [SAGE](https://journals.sagepub.com/doi/abs/10.1177/0160017615607229)

### Difficulte : 3/5
