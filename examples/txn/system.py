from lb.lb import System


# Problem: can we avoid hard coding accounts for each PSP?
# Answer: Yes!!
# We'll introduce separate system for each PSP! We'll:
# 1. Analyze main psp transactions
# 2. Analyze secondary psp transactions
# 3. Merge!
# This way we can setup individual rules per PSP.

# Note: I'll experiment initially now with quite specific rule-sets per PSP. It's
# occurring to me though that it's likely and probably *very* desirable that this
# results in generic rule-sets. E.g. one reusable rule-set for 1-phase and one reusable
# ruleset for 2-phase.

# I think it makes sense to not add abstractions for this piping _initially_, because it
# will be highly likely to hit the wrong abstraction. It does make sense to ponder that
# over time though.
#
# The flow is:
# - Group transactions based on some dimension like PSP.
# - Pass each group of transactions into their respective systems.
# - Merge all subsystems into a main system.
#
# Pondering further: It might be such that the grouping for the subsystems should be per
# payment, so that there might multiple "subsystems" per PSP on a purchase. I don't have
# an entirely clear picture of this in my head, but I'm imagining there might be rules
# that should only be enforced for an individual payment, and not at a global level.
#
# Pondering further as I write this, this train of thought seems to make sense. Perhaps
# it shouldn't be grouped by PSP at all, so that we can have "internal" transactions be
# part of a payment, e.g. "goodwill".

# Question: are there design choices or helpers we can provide to make it easier to work
#           with a mix of single-phase and 2-phase PSPs?

# Question/note: The thought I've had about returning "operations" still seems
# interesting. However, if the only operation in use would be `Persist[*txn]` that will
# probably not make sense.

# Question/note: augmented systems so that we can access the analysis of "sub systems".

credit_card_system = System()
gift_card_system = System()
purchase_system = System()
