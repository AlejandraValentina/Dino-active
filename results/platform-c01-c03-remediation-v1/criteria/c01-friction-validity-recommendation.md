# C01 friction validity — independent design recommendation

Source reviewed: frozen `353e3f04ca17c59c660ca5b5269a5b9a1755d0b1`. Read-only design recommendation; no solver/tests or repository mutations.

## Decision

Prefer **finite signed correlation coefficients with a guard on the actually evaluated loss**, rather than introducing compulsory new RPM/p_max validity rectangles in this correction.

`api.validate` explicitly documents that validity means a runnable configuration and does not establish physical adequacy. The Chen-Flynn polynomial can contain a negative fitted coefficient while its evaluated FMEP remains nonnegative at a particular operating point. Coefficient sign alone does not prove negative modeled friction. A compulsory new bounding rectangle would add an input/physical-validity policy absent from V1; corner/minimum checks over a declared rectangle do not establish that the correlation is experimentally applicable there.

For C01:

- Require every consumed coefficient and relevant operating/result quantity to be finite with strict scalar types.
- Preserve the original equation and signed coefficients. Do not cast, clamp or replace calculated FMEP with `max(0, FMEP)`.
- A nonfinite or negative **actual calculated FMEP** makes the result ineligible as trusted brake performance. Preserve original summary bytes/numerical values and expose a separate semantic/model-domain issue; an execution envelope may report the domain error without rewriting the physical result.
- Bind FMEP and derived BMEP/power semantics to the resolved config and actual p_max/RPM, using the owning API's definitions. Keep zero FMEP valid.
- Record in remediation disposition that the audit's negative-A input probe alone did not establish universal physical invalidity. The audit remains immutable. NaN acceptance, bool/fractional valve-count coercion and malformed-section exceptions are unambiguous contract defects; accepting negative evaluated loss as trustworthy performance is the relevant friction failure to close.
- Test a negative coefficient with positive evaluated FMEP as a positive control, a configuration/result yielding negative evaluated FMEP as ineligible, and exact zero FMEP as valid. These can be semantic/configuration fixtures without a new simulation campaign.

A scientifically documented correlation-validity domain can be added later through a separately scoped calibration/model-evidence decision. This recommendation does not claim that checking nonnegative FMEP validates the friction correlation against an engine.
