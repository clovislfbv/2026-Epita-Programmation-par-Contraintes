"""Provides utility functions for random number generation."""

import random

__all__ = ["random_power_of_two", "random_even"]


def random_power_of_two(min_exp: int = 1, max_exp: int = 6) -> int:
    """Generates a random power of two.

    The exponent is chosen uniformly between `min_exp`
    and `max_exp` (inclusive), and the returned value
    is computed as:

        2 ** exponent

    Parameters
    ----------
    min_exp : int, optional
        Minimum exponent value, by default 1
    max_exp : int, optional
        Maximum exponent value, by default 6

    Returns
    -------
    int
        A random power of two.
    """
    return 2 ** random.randint(min_exp, max_exp)


def random_even(min_val: int, max_val: int) -> int:
    """Generate a random even integer within a given range.

    The function adjusts the boundaries if needed so that
    both become even numbers before generating the value.

    Parameters
    ----------
    min_val : int
        Minimum allowed value.
    max_val : int
        Maximum allowed value.

    Returns
    -------
    int
        A random even integer between `min_val` and `max_val`.

    Raises
    ------
    ValueError
        If no valid even number exists in the range.
    """
    min_val = min_val if min_val % 2 == 0 else min_val + 1
    max_val = max_val if max_val % 2 == 0 else max_val - 1
    if min_val > max_val:
        raise ValueError(
            "Invalid boundaries, min value should be inferior or equal to max."
        )
    val = random.randint(0, (max_val - min_val) // 2)
    return min_val + val * 2
