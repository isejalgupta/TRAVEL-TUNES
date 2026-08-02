"""
Activity logic for TripTunes.

Pure algorithms, no database or web dependencies - a direct port of
the ActivityManager from the original console app:

  - quicksort by cost / rating / duration
  - 0/1 knapsack DP        -> budget optimiser (max rating within a budget)
  - backtracking            -> optimal schedule (max rating within time + budget)
  - simple attribute filter

Each function takes a plain list of Activity objects, so the API layer
can load them from the database and pass them straight in.
"""

from dataclasses import dataclass


@dataclass
class Activity:
    id: int
    name: str
    location: str
    category: str
    cost: float
    rating: float
    duration: float


# ------------------------------------------------------------------
#  Quicksort (kept as a real 3-way partition, not sorted())
# ------------------------------------------------------------------

def _quick_sort(arr: list, key: str, order: str) -> list:
    if len(arr) <= 1:
        return list(arr)
    pivot = arr[len(arr) // 2]
    pv = getattr(pivot, key)
    left, mid, right = [], [], []
    for a in arr:
        av = getattr(a, key)
        if order == "asc":
            (left if av < pv else mid if av == pv else right).append(a)
        else:
            (left if av > pv else mid if av == pv else right).append(a)
    return _quick_sort(left, key, order) + mid + _quick_sort(right, key, order)


def sort_by_cost(items: list, order: str = "asc") -> list:
    return _quick_sort(items, "cost", order)


def sort_by_rating(items: list, order: str = "desc") -> list:
    return _quick_sort(items, "rating", order)


def sort_by_duration(items: list, order: str = "asc") -> list:
    return _quick_sort(items, "duration", order)


# ------------------------------------------------------------------
#  Filtering
# ------------------------------------------------------------------

def filter_activities(items: list, max_cost=None, min_rating=None, max_duration=None) -> list:
    result = list(items)
    if max_cost is not None:
        result = [a for a in result if a.cost <= max_cost]
    if min_rating is not None:
        result = [a for a in result if a.rating >= min_rating]
    if max_duration is not None:
        result = [a for a in result if a.duration <= max_duration]
    return result


# ------------------------------------------------------------------
#  0/1 Knapsack DP - best activities within a budget (maximise rating)
# ------------------------------------------------------------------

def budget_optimizer(items: list, max_budget: float) -> list:
    if not items:
        return []
    # scale costs to integers (x10) so fractional rupees still work as weights
    # Cap the table width at the total cost of all items: any budget bigger
    # than "buy everything" selects everything anyway, so there's no point
    # allocating columns for it. This stops a huge user-supplied budget
    # (e.g. Rs.50,000 from the chat tool) from OOM-ing the process.
    total_cost = sum(max(0.0, it.cost) for it in items)
    effective_budget = min(max_budget, total_cost)
    W = max(0, int(effective_budget * 10))
    n = len(items)
    dp = [[0.0] * (W + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        wt = int(items[i - 1].cost * 10)
        val = items[i - 1].rating
        for w in range(W + 1):
            dp[i][w] = dp[i - 1][w]
            if wt <= w:
                dp[i][w] = max(dp[i][w], dp[i - 1][w - wt] + val)

    # backtrack which items were chosen
    selected = []
    w = W
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected.append(items[i - 1])
            w -= int(items[i - 1].cost * 10)
    selected.reverse()
    return selected


# ------------------------------------------------------------------
#  Backtracking - best combo within BOTH a time and budget limit
# ------------------------------------------------------------------

def optimal_schedule(items: list, max_hours: float, max_budget: float) -> list:
    if not items:
        return []

    # Suffix sums of rating: the most extra rating still reachable from
    # index i onward (ignoring constraints). This is an admissible upper
    # bound for branch-and-bound pruning below.
    n = len(items)
    suffix = [0.0] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix[i] = suffix[i + 1] + max(0.0, items[i].rating)

    best = {"rating": -1.0, "combo": []}

    def backtrack(idx, time_left, budget_left, current, cur_rating):
        if cur_rating > best["rating"]:
            best["rating"] = cur_rating
            best["combo"] = list(current)
        # Prune: if even taking every remaining activity couldn't beat the
        # best found so far, abandon this branch. Turns the worst-case
        # 2^n enumeration into something tractable in practice.
        if cur_rating + suffix[idx] <= best["rating"]:
            return
        for i in range(idx, n):
            if items[i].duration <= time_left and items[i].cost <= budget_left:
                current.append(items[i])
                backtrack(i + 1, time_left - items[i].duration,
                          budget_left - items[i].cost,
                          current, cur_rating + items[i].rating)
                current.pop()

    backtrack(0, max_hours, max_budget, [], 0.0)
    return best["combo"]


if __name__ == "__main__":
    # Sanity check against hand-computed expectations.
    sample = [
        Activity(1, "Red Fort", "Delhi", "History", 50, 4.7, 3),
        Activity(2, "India Gate", "Delhi", "Sightseeing", 0, 4.5, 1),
        Activity(3, "Chandni Chowk Food Walk", "Delhi", "Food", 0, 4.8, 2),
        Activity(4, "Akshardham Temple", "Delhi", "Spiritual", 0, 4.8, 3),
        Activity(5, "Qutub Minar", "Delhi", "History", 40, 4.6, 2),
    ]

    print("sort by rating (desc):", [a.name for a in sort_by_rating(sample)])
    print("sort by cost (asc):", [(a.name, a.cost) for a in sort_by_cost(sample)])

    budget = budget_optimizer(sample, max_budget=50)
    print("budget<=50 picks:", [a.name for a in budget], "total cost:", sum(a.cost for a in budget))

    sched = optimal_schedule(sample, max_hours=5, max_budget=50)
    print("schedule <=5hrs <=Rs50:", [a.name for a in sched],
          "total hrs:", sum(a.duration for a in sched),
          "total cost:", sum(a.cost for a in sched))