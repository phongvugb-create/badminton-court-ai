import math

def calculate_expected_score(rating_a: int, rating_b: int) -> float:
    """Calculates expected score of player A against player B"""
    return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))

def update_elo(rating_a: int, rating_b: int, score_a: float, k_factor: int = 32) -> tuple[int, int]:
    """
    Update ELO rating after a match.
    score_a: 1.0 (win), 0.5 (draw), 0.0 (loss)
    Returns: (new_rating_a, new_rating_b)
    """
    exp_a = calculate_expected_score(rating_a, rating_b)
    exp_b = calculate_expected_score(rating_b, rating_a)

    score_b = 1.0 - score_a

    new_rating_a = round(rating_a + k_factor * (score_a - exp_a))
    new_rating_b = round(rating_b + k_factor * (score_b - exp_b))

    return (max(100, new_rating_a), max(100, new_rating_b))

def is_matchmaking_suitable(user_elo: int, target_elo: int, max_diff: int = 150) -> bool:
    """Checks if a player qualifies for a matchmaking room based on ELO delta"""
    return abs(user_elo - target_elo) <= max_diff
