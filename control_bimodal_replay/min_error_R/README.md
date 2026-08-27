# Control-Bimodal minimum-error R replay

The active replay is `R/intervention.csv`. Run the existing replay workflow
from the `R/` directory so that its input is `./intervention.csv`.

Selection is deterministic: CB10, evaluation case 07, repeat 1 is the formal
successful realised-R result with the smallest `target_xy_error` among all 47
successful Control-Bimodal R rows (4.9821826 mm).

The formal successful EE trace was reflected into the left-handed workspace.
World position uses `y := -y`; orientation uses the matching frame reflection
`R' = S R S`, where `S = diag(1,-1,1)`. The Panda base is `[0,-0.15,0]`, the
cylinder is at `[0.5,-0.25]`, and the target is `[0.5,-0.5]`.

Because the formal JSON stores per-step EE positions but not per-step EE
quaternions or arm joints, sequential PyBullet IK holds the reflected formal
policy-start orientation. A documented post-obstacle x/z clearance corridor
keeps Panda link 4 away from the cylinder before blending back to the formal
target pose. The final PyBullet replay has zero box/robot cylinder-contact
steps, 9.994 mm target error, and an upright cylinder.

See `manifest.json` and `R/reproduction.json` for hashes and full provenance.
