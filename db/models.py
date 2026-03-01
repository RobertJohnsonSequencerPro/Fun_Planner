"""Shared constants that mirror the allowed values stored in the database."""

CATEGORIES: list[str] = [
    "outdoor",
    "social",
    "creative",
    "travel",
    "food",
    "fitness",
    "entertainment",
    "other",
]

ENERGY_LEVELS: list[str] = ["low", "medium", "high"]

COST_ESTIMATES: list[str] = ["free", "cheap", "moderate", "expensive"]

STATUSES: list[str] = ["idea", "planned", "done", "skipped"]

# Suggested starter steps keyed by category
DEFAULT_STEPS: dict[str, list[str]] = {
    "outdoor": [
        "Check the weather forecast",
        "Plan the route or location",
        "Pack gear and supplies",
        "Book or reserve a spot if needed",
    ],
    "social": [
        "Decide on the guest list",
        "Send invitations",
        "Confirm attendees",
        "Arrange food / drinks / logistics",
        "Send day-before reminders",
    ],
    "creative": [
        "Gather materials and tools",
        "Find inspiration and references",
        "Block off time in your schedule",
        "Prepare your workspace",
    ],
    "travel": [
        "Research the destination",
        "Book transportation",
        "Book accommodation",
        "Plan daily itinerary",
        "Pack bags",
        "Check travel documents",
    ],
    "food": [
        "Find a recipe or restaurant",
        "Buy ingredients / make a reservation",
        "Prepare and cook",
        "Enjoy!",
    ],
    "fitness": [
        "Choose the specific workout or activity",
        "Get equipment ready",
        "Plan a warm-up and cool-down",
        "Track progress afterward",
    ],
    "entertainment": [
        "Check showtimes or availability",
        "Buy tickets if needed",
        "Arrange transport and parking",
    ],
    "other": [
        "Research and plan",
        "Gather what you need",
        "Schedule time on the calendar",
        "Do it!",
    ],
}
