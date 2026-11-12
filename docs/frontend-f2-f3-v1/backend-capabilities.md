# Application/backend boundary and remaining capabilities

Implemented application adapters call existing engine_platform.validate_config/run_api/check_result, public run_exploratory, verified result importers, project context mutations and artifact publishers. No equations, solver internals, tolerances or scientific contracts are changed.

The new persistent queue supports serial2T/native4T points. Existing2T/native RPM sweeps and0D reference-curve queue retain their own scientific/execution contracts. The common entry describes capabilities instead of pretending all runners offer the same restart semantics. Running jobs have canonical immutable configuration bytes, budgets and origin identity. They never resume automatically.

Native checkpoint resume would require a future versioned scientific API returning an opaque checkpoint artifact with checksum, exact input/model/source identity, complete-cycle boundary, restart eligibility and cancellation semantics. The frontend must not deserialize internal solver state to fabricate this capability. This is a dependency for CP3/scientific ownership, not implemented here.2T's existing explicit checkpoint/study recovery remains in its established workflow; historical checkpoints are untouched.

A shared durable curve planner and native/reference comparison policy remain separately identifiable application/scientific extensions. Reference0D results cannot become native comparison endpoints. Experimental validation and predictive capability remain unperformed/unclaimed. General regression debt and CP3/CP4 acceptance belong to the parallel DeepSeek branch; no files or branches there are modified.

Queue files retain one authority using an OS-aware Qt lock. A second writer is rejected. New/open queue selection preserves previous ledgers;100 retained items is an explicit bound, not automatic cleanup. Closing the application unlocks only after worker shutdown; crash recovery leaves INTERRUPTED jobs and preserved artifacts. Storage admission keeps the shared reserve.
