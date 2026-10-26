# Mesh diagnostic thermal mapping, before calculation

The input inspection found explicit exhaust heat-transfer surfaces attached to
each original duct cell. Copying their cell indices onto a refined mesh would
change the physical location and distribution of heat exchange. This is a mesh
mapping requirement, not permission to alter heat coefficients or temperatures.

For each duct-attached surface, split its given area between two daughter cells
according to the integral of the original linearly varying radius. First fraction
is (3*rleft+rright)/(4*(rleft+rright)); second is its complement. The same ratio
applies with or without the common frustum slant factor. Preserve the supplied
parent area exactly to rounding, h, wall temperature/map, kind and provenance.
Map daughter surfaces to indices 2*i and 2*i+1. Chamber surfaces stay unchanged.

Verify area and uniform-gas heat-transfer conservation before the run. Reject
unrecognized thermal locations and moving-cell reed bindings rather than silently
retaining an invalid index mapping. Native input has static reeds. All physical
and execution thresholds in integrated-mesh-protocol-v1 remain unchanged.
