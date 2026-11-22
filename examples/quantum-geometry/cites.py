"""Citation registry for the quantum-geometry demo note.

Build from the repository root:
  uv run skills/unfold/scripts/build.py examples/quantum-geometry
  python skills/unfold/scripts/build.py examples/quantum-geometry
The reader's file is written to examples/quantum-geometry/quantum-geometry.html.

The cited PDF is the published version of S. Peotta and P. Törmä, Nat. Commun. 6, 8944 (2015),
licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); see LICENSE.md in this folder."""
import os
from notelib import config, source, pdf

HERE = os.path.dirname(os.path.abspath(__file__))
config(root=HERE, name="quantum-geometry", title="Quantum geometry and topology", out=HERE)

source("pt", "Peotta_Torma_2015_NatCommun.pdf", "Peotta & Törmä, Nat. Commun. 6, 8944 (2015)", "Peotta & Törmä",
       offset=0, cols=2, share="https://doi.org/10.1038/ncomms9944")

# The superfluid weight of a flat band, and the bound by the Chern number (abstract)
pdf("pt-flat", "pt", 1, "abstract",
    "Here we provide a general result for the", "Chern number is nonzero")
# The metric is the real part of one invariant matrix, the Chern number its imaginary part
pdf("pt-tensor", "pt", 2, "Introduction",
    "tensor is the real part of an invariant matrix", "part is the Chern number")
# Positive semidefiniteness of the 2x2 matrix gives the determinant inequality, eq. (23)
pdf("pt-psd", "pt", 6, "eq. (23)",
    "a Riemannian metric", "in appropriate units")
