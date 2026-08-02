#!/usr/bin/env python3

import heapq
import itertools
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


# ============================================================
#  DATE UTILITIES
# ============================================================

def get_today_string() -> str:
    return date.today().isoformat()


def parse_date(s_raw: str):
    """Returns (ok, year, month, day)."""
    s = s_raw
    while s and s[-1] in ("\r", " "):
        s = s[:-1]
    if len(s) != 10 or s[4] != "-" or s[7] != "-":
        return False, 0, 0, 0
    try:
        y = int(s[0:4])
        m = int(s[5:7])
        d = int(s[8:10])
    except ValueError:
        return False, 0, 0, 0
    if m < 1 or m > 12 or d < 1 or d > 31:
        return False, 0, 0, 0
    return True, y, m, d


def date_after_today(date_str: str) -> bool:
    return date_str > get_today_string()


def date_a_before_date_b(a: str, b: str) -> bool:
    return a < b


def strip_line(s: str) -> str:
    while s and s[-1] in ("\r", "\n", " "):
        s = s[:-1]
    return s


def prompt_future_date(label: str) -> str:
    while True:
        d = strip_line(input(f"{label} (YYYY-MM-DD, must be after {get_today_string()}): "))
        ok, y, m, day = parse_date(d)
        if not ok:
            print("  [X] Invalid format. Please use YYYY-MM-DD.")
            continue
        if not date_after_today(d):
            print(f"  [X] Date must be in the future (after {get_today_string()}).")
            continue
        return d


def prompt_date_on_or_after(label: str, min_date: str) -> str:
    while True:
        d = strip_line(input(f"{label} (YYYY-MM-DD, must be on or after {min_date}): "))
        ok, y, m, day = parse_date(d)
        if not ok:
            print("  [X] Invalid format. Please use YYYY-MM-DD.")
            continue
        if not date_after_today(d):
            print(f"  [X] Date must be in the future (after {get_today_string()}).")
            continue
        if d < min_date:
            print(f"  [X] End date must be on or after start date ({min_date}).")
            continue
        return d


# ============================================================
#  ADMIN AUTHENTICATION
# ============================================================

ADMIN_PASSWORD = "JHIN TAPAK DUM DUM"


def authenticate_admin() -> bool:
    pwd = input("\n  Enter Admin Password: ")
    if pwd == ADMIN_PASSWORD:
        print("  [OK] Access granted. Welcome, Admin!")
        return True
    print("  [X] Incorrect password. Access denied.")
    return False


# ============================================================
#  GRAPH  (Route Planning)
# ============================================================

@dataclass
class Route:
    destination: str
    distance: float
    cost: float
    time: float


@dataclass
class PathResult:
    path: list
    total_weight: float
    weight_type: str


class Graph:
    def __init__(self):
        self.cities: dict[str, dict] = {}
        self.routes: dict[str, list] = {}

    def _dijkstra(self, source, destination, weight_type) -> PathResult:
        if source not in self.cities or destination not in self.cities:
            return PathResult([], float("inf"), weight_type)

        distances = {c: float("inf") for c in self.cities}
        previous = {}
        distances[source] = 0
        previous[source] = ""

        pq = [(0.0, source)]
        while pq:
            current_dist, current = heapq.heappop(pq)
            if current == destination:
                break
            if current_dist > distances[current]:
                continue
            for r in self.routes.get(current, []):
                if r.destination not in self.cities:
                    continue
                w = r.distance if weight_type == "distance" else r.cost if weight_type == "cost" else r.time
                nd = current_dist + w
                if nd < distances[r.destination]:
                    distances[r.destination] = nd
                    previous[r.destination] = current
                    heapq.heappush(pq, (nd, r.destination))

        if distances[destination] == float("inf"):
            return PathResult([], float("inf"), weight_type)

        path = []
        cur = destination
        while cur != "":
            path.append(cur)
            if cur not in previous:
                break
            cur = previous[cur]
        path.reverse()
        return PathResult(path, distances[destination], weight_type)

    def add_city(self, city_name, metadata=None) -> bool:
        if city_name not in self.cities:
            self.cities[city_name] = dict(metadata) if metadata else {}
            return True
        return False

    def remove_city(self, city_name) -> bool:
        if city_name not in self.cities:
            return False
        del self.cities[city_name]
        self.routes.pop(city_name, None)
        for c in list(self.routes.keys()):
            self.routes[c] = [r for r in self.routes[c] if r.destination != city_name]
        return True

    def add_route(self, c1, c2, dist, cost, time):
        if c1 not in self.cities or c2 not in self.cities:
            print("  [X] Cannot add route: one or both cities not found.")
            return
        self.routes.setdefault(c1, []).append(Route(c2, dist, cost, time))
        self.routes.setdefault(c2, []).append(Route(c1, dist, cost, time))

    def remove_route(self, c1, c2):
        if c1 in self.routes:
            self.routes[c1] = [r for r in self.routes[c1] if r.destination != c2]
        if c2 in self.routes:
            self.routes[c2] = [r for r in self.routes[c2] if r.destination != c1]

    def get_all_cities(self):
        return sorted(self.cities.keys())

    def find_shortest_path(self, src, dst) -> PathResult:
        return self._dijkstra(src, dst, "distance")

    def find_cheapest_path(self, src, dst) -> PathResult:
        return self._dijkstra(src, dst, "cost")

    def find_fastest_path(self, src, dst) -> PathResult:
        return self._dijkstra(src, dst, "time")

    def find_path_with_stops(self, src, dst, stops) -> PathResult:
        all_stops = [src] + list(stops) + [dst]
        total_path = []
        total_dist = 0.0
        for i in range(len(all_stops) - 1):
            r = self.find_shortest_path(all_stops[i], all_stops[i + 1])
            if not r.path or r.total_weight == float("inf"):
                return PathResult([], float("inf"), "distance")
            total_path.extend(r.path[:-1])
            total_dist += r.total_weight
        total_path.append(dst)
        return PathResult(total_path, total_dist, "distance")

    def get_alternative_paths(self, src, dst, k=3):
        paths = []
        main = self.find_shortest_path(src, dst)
        if not main.path:
            return paths
        paths.append(main)
        for i in range(1, len(main.path) - 1):
            if len(paths) >= k:
                break
            excl = main.path[i]
            tmp = self.routes.get(excl, [])
            self.routes[excl] = []
            alt = self.find_shortest_path(src, dst)
            self.routes[excl] = tmp
            if alt.path and alt.total_weight != float("inf"):
                paths.append(alt)
        return paths


# ============================================================
#  ITINERARY TREE
# ============================================================

class ItineraryNode:
    def __init__(self, node_type: str, data: dict):
        self.node_type = node_type
        self.data = dict(data)
        self.children: list["ItineraryNode"] = []

    def add_child(self, child: "ItineraryNode"):
        self.children.append(child)

    def remove_child(self, child: "ItineraryNode"):
        if child in self.children:
            self.children.remove(child)


class ItineraryTree:
    def __init__(self):
        self.trips: list[ItineraryNode] = []
        self.active_trip = -1

    def _current(self) -> Optional[ItineraryNode]:
        if self.active_trip < 0 or self.active_trip >= len(self.trips):
            return None
        return self.trips[self.active_trip]

    def _build_days(self, root: ItineraryNode, start_date_str: str, end_date_str: str):
        _, sy, sm, sd = parse_date(start_date_str)
        _, ey, em, ed = parse_date(end_date_str)
        cur = date(sy, sm, sd)
        last_day = date(ey, em, ed)
        day_num = 1
        while day_num <= 365:
            dd = {"day_number": str(day_num), "date": cur.isoformat()}
            root.add_child(ItineraryNode("day", dd))
            if cur >= last_day:
                break
            cur += timedelta(days=1)
            day_num += 1

    def create_itinerary(self, name: str, start_date: str, end_date: str) -> str:
        if not date_after_today(start_date):
            return f"Start date must be in the future (after {get_today_string()})."
        if not date_after_today(end_date):
            return f"End date must be in the future (after {get_today_string()})."
        if end_date < start_date:
            return "End date must be on or after the start date."
        d = {"name": name, "start_date": start_date, "end_date": end_date}
        root = ItineraryNode("trip", d)
        self._build_days(root, start_date, end_date)
        self.trips.append(root)
        self.active_trip = len(self.trips) - 1
        return ""

    def list_trips(self) -> list:
        return [f"{t.data['name']}  [{t.data['start_date']} -> {t.data['end_date']}]" for t in self.trips]

    def get_trip_count(self) -> int:
        return len(self.trips)

    def get_active_trip(self) -> int:
        return self.active_trip

    def select_trip(self, idx: int) -> str:
        if idx < 1 or idx > len(self.trips):
            return "Invalid trip number."
        self.active_trip = idx - 1
        return ""

    def delete_trip(self, idx: int) -> str:
        if idx < 1 or idx > len(self.trips):
            return "Invalid trip number."
        del self.trips[idx - 1]
        if not self.trips:
            self.active_trip = -1
        else:
            self.active_trip = min(self.active_trip, len(self.trips) - 1)
        return ""

    def add_day(self, day_number: int, date_str: str) -> str:
        root = self._current()
        if not root:
            return "No trip selected. Create or select a trip first."
        if not date_after_today(date_str):
            return f"Day date must be in the future (after {get_today_string()})."
        if date_str < root.data["start_date"] or date_str > root.data["end_date"]:
            return (f"Day date must be within the trip period "
                    f"({root.data['start_date']} to {root.data['end_date']}).")
        d = {"day_number": str(day_number), "date": date_str}
        root.add_child(ItineraryNode("day", d))
        return ""

    def add_activity(self, day_number: int, activity: dict) -> Optional[ItineraryNode]:
        root = self._current()
        if not root:
            return None
        for day_node in root.children:
            if day_node.data["day_number"] == str(day_number):
                act = ItineraryNode("activity", activity)
                day_node.add_child(act)
                return act
        return None

    def remove_activity(self, day_number: int, activity_id: str) -> bool:
        root = self._current()
        if not root:
            return False
        for day_node in root.children:
            if day_node.data["day_number"] == str(day_number):
                for act in day_node.children:
                    if act.data.get("id") == activity_id:
                        day_node.remove_child(act)
                        return True
        return False

    def move_activity(self, from_day: int, to_day: int, activity_id: str) -> Optional[ItineraryNode]:
        root = self._current()
        if not root:
            return None
        act_data: dict = {}
        for day_node in root.children:
            if day_node.data["day_number"] == str(from_day):
                for act in day_node.children:
                    if act.data.get("id") == activity_id:
                        act_data = dict(act.data)
                        day_node.remove_child(act)
                        break
        if act_data:
            return self.add_activity(to_day, act_data)
        return None

    def display_itinerary(self) -> str:
        root = self._current()
        if not root:
            return "No trip selected.\n"
        r = "\n============================================================\n"
        r += f"  Trip: {root.data['name']}\n"
        r += f"  Duration: {root.data['start_date']} to {root.data['end_date']}\n"
        r += "============================================================\n\n"
        for day_node in root.children:
            r += f"Day {day_node.data['day_number']} - {day_node.data['date']}\n"
            r += "  ----------------------------------------\n"
            if not day_node.children:
                r += "    No activities planned\n"
            else:
                for cnt, act in enumerate(day_node.children, start=1):
                    r += f"  {cnt}. {act.data['name']}\n"
                    r += f"     Duration: {act.data['duration']} hrs | Cost: Rs.{act.data['cost']}\n"
            r += "\n"
        return r

    def get_day_schedule(self, day_number: int) -> list:
        root = self._current()
        if not root:
            return []
        for day_node in root.children:
            if day_node.data["day_number"] == str(day_number):
                return [dict(act.data) for act in day_node.children]
        return []

    def get_day_count(self) -> int:
        root = self._current()
        return len(root.children) if root else 0

    def get_total_duration(self) -> float:
        root = self._current()
        if not root:
            return 0.0
        total = 0.0
        for d in root.children:
            for a in d.children:
                v = a.data.get("duration", "")
                if v:
                    try:
                        total += float(v)
                    except ValueError:
                        pass
        return total

    def get_total_cost(self) -> float:
        root = self._current()
        if not root:
            return 0.0
        total = 0.0
        for d in root.children:
            for a in d.children:
                v = a.data.get("cost", "")
                if v:
                    try:
                        total += float(v)
                    except ValueError:
                        pass
        return total


# ============================================================
#  ACTIVITY MANAGER
# ============================================================

@dataclass
class Activity:
    id: str
    name: str
    location: str
    category: str
    cost: float
    rating: float
    duration: float


class ActivityManager:
    def __init__(self):
        self.db: dict[str, list] = {}
        self.name_index: dict[str, dict] = {}
        self.category_index: dict[str, str] = {}

    def _rebuild_name_index(self, city: str):
        self.name_index[city] = {a.name.lower(): a for a in self.db.get(city, [])}

    def add_activity_to_db(self, name, location, category, cost, rating, duration) -> Activity:
        idx = len(self.db.get(location, []))
        a = Activity(f"{location}_{idx}", name, location, category, cost, rating, duration)
        self.db.setdefault(location, []).append(a)
        self.name_index.setdefault(location, {})[name.lower()] = a
        self.category_index[category.upper()] = category
        return a

    def remove_activity_from_db(self, location, activity_name) -> bool:
        if location not in self.db:
            return False
        before = len(self.db[location])
        self.db[location] = [a for a in self.db[location] if a.name != activity_name]
        if len(self.db[location]) == before:
            return False
        self._rebuild_name_index(location)
        return True

    def get_all_activities(self, city) -> list:
        return list(self.db.get(city, []))

    def resolve_city(self, input_str: str) -> str:
        lo = input_str.upper()
        for city in self.db:
            if city.upper() == lo:
                return city
        return ""

    def resolve_category(self, input_str: str) -> str:
        return self.category_index.get(input_str.upper(), "")

    def get_by_category(self, cat: str) -> list:
        res = []
        for acts in self.db.values():
            for a in acts:
                if a.category == cat:
                    res.append(a)
        return res

    @staticmethod
    def _quick_sort(arr, key, order):
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
        return (ActivityManager._quick_sort(left, key, order) + mid +
                ActivityManager._quick_sort(right, key, order))

    def sort_by_cost(self, v, order="asc"):
        return self._quick_sort(v, "cost", order)

    def sort_by_rating(self, v, order="desc"):
        return self._quick_sort(v, "rating", order)

    def sort_by_duration(self, v, order="asc"):
        return self._quick_sort(v, "duration", order)

    def find_by_name(self, city, name) -> Optional[Activity]:
        return self.name_index.get(city, {}).get(name.lower())

    def binary_search_by_name(self, name) -> Optional[Activity]:
        lo = name.lower()
        for idx in self.name_index.values():
            if lo in idx:
                return idx[lo]
        return None

    def filter_activities(self, acts, crit: dict) -> list:
        result = list(acts)
        if "max_cost" in crit:
            result = [a for a in result if a.cost <= crit["max_cost"]]
        if "min_rating" in crit:
            result = [a for a in result if a.rating >= crit["min_rating"]]
        if "max_duration" in crit:
            result = [a for a in result if a.duration <= crit["max_duration"]]
        return result

    def budget_optimizer(self, city, max_budget) -> list:
        acts = self.get_all_activities(city)
        if not acts:
            return []
        W = int(max_budget * 10)
        n = len(acts)
        dp = [[0.0] * (W + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            wt = int(acts[i - 1].cost * 10)
            val = acts[i - 1].rating
            for w in range(W + 1):
                dp[i][w] = dp[i - 1][w]
                if w >= wt:
                    dp[i][w] = max(dp[i][w], dp[i - 1][w - wt] + val)
        selected = []
        w = W
        for i in range(n, 0, -1):
            if dp[i][w] != dp[i - 1][w]:
                selected.append(acts[i - 1])
                w -= int(acts[i - 1].cost * 10)
        selected.reverse()
        return selected

    def _backtrack_schedule(self, acts, idx, time_left, budget_left, current, best_holder):
        cur_rating = sum(a.rating for a in current)
        if cur_rating > best_holder["rating"]:
            best_holder["rating"] = cur_rating
            best_holder["best"] = list(current)
        if idx >= len(acts):
            return
        for i in range(idx, len(acts)):
            if acts[i].duration > time_left or acts[i].cost > budget_left:
                continue
            current.append(acts[i])
            self._backtrack_schedule(acts, i + 1, time_left - acts[i].duration,
                                      budget_left - acts[i].cost, current, best_holder)
            current.pop()

    def optimal_schedule(self, city, max_hours, max_budget) -> list:
        acts = self.get_all_activities(city)
        if not acts:
            return []
        best_holder = {"rating": -1, "best": []}
        self._backtrack_schedule(acts, 0, max_hours, max_budget, [], best_holder)
        return best_holder["best"]


# ============================================================
#  MUSIC TRIE
# ============================================================

@dataclass
class Song:
    name: str
    artist: str
    metadata: dict = field(default_factory=dict)


class TrieNode:
    __slots__ = ("children", "is_end", "song_data")

    def __init__(self):
        self.children: dict[str, "TrieNode"] = {}
        self.is_end = False
        self.song_data: Optional[Song] = None


class MusicTrie:
    def __init__(self):
        self.root = TrieNode()

    def _collect(self, node: Optional[TrieNode], out: list):
        if node is None:
            return
        if node.is_end and node.song_data:
            out.append(node.song_data)
        for child in node.children.values():
            self._collect(child, out)

    def insert_song(self, name, artist, meta=None):
        node = self.root
        for c in name.lower():
            node = node.children.setdefault(c, TrieNode())
        node.is_end = True
        node.song_data = Song(name, artist, dict(meta) if meta else {})

    def search_prefix(self, prefix) -> list:
        node = self.root
        for c in prefix.lower():
            if c not in node.children:
                return []
            node = node.children[c]
        res: list = []
        self._collect(node, res)
        return res

    def auto_complete(self, prefix, limit) -> list:
        return self.search_prefix(prefix)[:limit]

    def delete_song(self, name) -> bool:
        return self._delete_helper(self.root, name.lower(), 0)

    def _delete_helper(self, node, lo_name, depth) -> bool:
        if node is None:
            return False
        if depth == len(lo_name):
            if not node.is_end:
                return False
            node.is_end = False
            node.song_data = None
            return len(node.children) == 0
        c = lo_name[depth]
        if c not in node.children:
            return False
        should_delete_child = self._delete_helper(node.children[c], lo_name, depth + 1)
        if should_delete_child:
            del node.children[c]
            return not node.is_end and len(node.children) == 0
        return False

    def get_all_songs(self) -> list:
        res: list = []
        self._collect(self.root, res)
        return res

    def search_by_artist(self, artist) -> list:
        lo = artist.lower()
        return [s for s in self.get_all_songs() if s.artist.lower() == lo]

    @staticmethod
    def _build_kmp_table(pattern) -> list:
        m = len(pattern)
        lps = [0] * m
        length = 0
        i = 1
        while i < m:
            if pattern[i] == pattern[length]:
                length += 1
                lps[i] = length
                i += 1
            else:
                if length != 0:
                    length = lps[length - 1]
                else:
                    lps[i] = 0
                    i += 1
        return lps

    @staticmethod
    def _kmp_search(text, pattern) -> bool:
        if not pattern:
            return True
        t = text.lower()
        p = pattern.lower()
        n, m = len(t), len(p)
        lps = MusicTrie._build_kmp_table(p)
        i = j = 0
        while i < n:
            if t[i] == p[j]:
                i += 1
                j += 1
            if j == m:
                return True
            elif i < n and t[i] != p[j]:
                if j != 0:
                    j = lps[j - 1]
                else:
                    i += 1
        return False

    def kmp_full_text_search(self, query) -> list:
        return [s for s in self.get_all_songs()
                if self._kmp_search(s.name, query) or self._kmp_search(s.artist, query)]


class FrequencyTracker:
    def __init__(self):
        self.play_count: dict[str, int] = {}
        self.meta: dict[str, Song] = {}

    def increment_play_count(self, sid: str):
        self.play_count[sid] = self.play_count.get(sid, 0) + 1

    def get_play_count(self, sid: str) -> int:
        return self.play_count.get(sid, 0)

    def get_most_played(self, k: int) -> list:
        items = sorted(self.play_count.items(), key=lambda kv: kv[1], reverse=True)
        return items[:k]

    def reset_frequencies(self):
        self.play_count.clear()

    def add_song_metadata(self, sid: str, song: Song):
        self.meta[sid] = song
        self.play_count.setdefault(sid, 0)

    def get_song_metadata(self, sid: str) -> Optional[Song]:
        return self.meta.get(sid)


class PlaylistHeap:
    def __init__(self):
        self._heap: list = []
        self._counter = itertools.count()
        self.current: list = []

    def build_max_heap(self, songs, criteria="rating"):
        self._heap = []
        for s in songs:
            p = float(s.metadata[criteria]) if criteria in s.metadata else 1.0
            heapq.heappush(self._heap, (-p, next(self._counter), s))

    def extract_top_k(self, k) -> list:
        top = []
        tmp = list(self._heap)
        heapq.heapify(tmp)
        for _ in range(k):
            if not tmp:
                break
            _, _, s = heapq.heappop(tmp)
            top.append(s)
        return top

    def insert_song(self, s: Song, p: float):
        heapq.heappush(self._heap, (-p, next(self._counter), s))

    def generate_playlist(self, dur, mood, genre) -> list:
        self.current = self.extract_top_k(max(1, dur // 4))
        return self.current

    def get_current_playlist(self) -> list:
        return self.current

    def add_to_playlist(self, s: Song):
        self.current.append(s)

    def remove_from_playlist(self, name) -> bool:
        for i, s in enumerate(self.current):
            if s.name == name:
                del self.current[i]
                return True
        return False

    def shuffle_playlist(self) -> list:
        s = list(self.current)
        random.shuffle(s)
        return s


# ============================================================
#  HELPERS
# ============================================================

def print_path(path):
    print(" -> ".join(path))


def safe_read_int(prompt: str = "") -> int:
    while True:
        raw = input(prompt)
        try:
            return int(raw.strip())
        except ValueError:
            prompt = "  [X] Invalid input. Please enter a number: "


def safe_read_float(prompt: str = "") -> float:
    while True:
        raw = input(prompt)
        try:
            return float(raw.strip())
        except ValueError:
            prompt = "  [X] Invalid input. Please enter a number: "


# ============================================================
#  ADMIN PANEL
# ============================================================

def admin_panel(graph: Graph, act_mgr: ActivityManager):
    print("\n--------------------------------------")
    print("         ADMIN CONTROL PANEL          ")
    print("--------------------------------------")

    if not authenticate_admin():
        return

    choice = None
    while choice != 0:
        print("\n--- Admin Menu ---")
        print("1. Add City")
        print("2. Remove City")
        print("3. Add Route Between Cities")
        print("4. Remove Route Between Cities")
        print("5. Add Activity to a City")
        print("6. Remove Activity from a City")
        print("0. Back to Main Menu")
        choice = safe_read_int("Choice: ")

        if choice == 1:
            city = input("Enter city name: ")
            if graph.add_city(city):
                print(f"  [OK] City '{city}' added.")
            else:
                print("  [X] City already exists.")
        elif choice == 2:
            city = input("Enter city name to remove: ")
            if graph.remove_city(city):
                print(f"  [OK] City '{city}' removed.")
            else:
                print("  [X] City not found.")
        elif choice == 3:
            c1 = input("First city: ")
            c2 = input("Second city: ")
            dist = safe_read_float("Distance (km): ")
            cost = safe_read_float("Cost (Rs.): ")
            time_ = safe_read_float("Time (hrs): ")
            graph.add_route(c1, c2, dist, cost, time_)
            print("  [OK] Route added.")
        elif choice == 4:
            c1 = input("First city: ")
            c2 = input("Second city: ")
            graph.remove_route(c1, c2)
            print("  [OK] Route removed.")
        elif choice == 5:
            name = input("Activity name: ")
            loc = input("City/Location: ")
            cat = input("Category: ")
            cost = safe_read_float("Cost (Rs.): ")
            rating = safe_read_float("Rating (0-5): ")
            dur = safe_read_float("Duration (hrs): ")
            act_mgr.add_activity_to_db(name, loc, cat, cost, rating, dur)
            print(f"  [OK] Activity '{name}' added to {loc}.")
        elif choice == 6:
            loc = input("City/Location: ")
            name = input("Activity name: ")
            if act_mgr.remove_activity_from_db(loc, name):
                print("  [OK] Activity removed.")
            else:
                print("  [X] Activity not found.")


# ============================================================
#  USER MENUS
# ============================================================

def route_planning_menu(graph: Graph):
    def resolve_city(input_str):
        lo = input_str.upper()
        for c in graph.get_all_cities():
            if c.upper() == lo:
                return c
        return ""

    choice = None
    while choice != 0:
        print("\n--- ROUTE PLANNING ---")
        print("1. View All Cities")
        print("2. Find Shortest Path (by Distance)")
        print("3. Find Cheapest Path (by Cost)")
        print("4. Find Fastest Path (by Time)")
        print("5. Find Path with Stops")
        print("6. Get Alternative Paths")
        print("0. Back")
        choice = safe_read_int("Choice: ")

        if choice == 1:
            cities = graph.get_all_cities()
            print("\n--- Available Cities ---")
            for i, c in enumerate(cities, 1):
                print(f"  {i}. {c}")
        elif choice in (2, 3, 4):
            src_in = input("Source city: ")
            dst_in = input("Destination city: ")
            src = resolve_city(src_in)
            dst = resolve_city(dst_in)
            if not src:
                print(f"  [X] City not found: {src_in}")
                continue
            if not dst:
                print(f"  [X] City not found: {dst_in}")
                continue
            if choice == 2:
                r = graph.find_shortest_path(src, dst)
                if not r.path:
                    print(f"  [X] No path found between {src} and {dst}.")
                else:
                    print("\n  Path: ", end="")
                    print_path(r.path)
                    print(f"  Total Distance: {r.total_weight} km")
            elif choice == 3:
                r = graph.find_cheapest_path(src, dst)
                if not r.path:
                    print(f"  [X] No path found between {src} and {dst}.")
                else:
                    print("\n  Path: ", end="")
                    print_path(r.path)
                    print(f"  Total Cost: Rs.{r.total_weight}")
            else:
                r = graph.find_fastest_path(src, dst)
                if not r.path:
                    print(f"  [X] No path found between {src} and {dst}.")
                else:
                    print("\n  Path: ", end="")
                    print_path(r.path)
                    print(f"  Total Time: {r.total_weight} hours")
        elif choice == 5:
            src_in = input("Source: ")
            dst_in = input("Destination: ")
            src = resolve_city(src_in)
            dst = resolve_city(dst_in)
            if not src:
                print(f"  [X] City not found: {src_in}")
                continue
            if not dst:
                print(f"  [X] City not found: {dst_in}")
                continue
            n = safe_read_int("Number of stops: ")
            stops = []
            for i in range(n):
                s = input(f"Stop {i + 1}: ")
                rs = resolve_city(s)
                if not rs:
                    print(f"  [X] Stop city not found: {s}")
                    rs = s
                stops.append(rs)
            r = graph.find_path_with_stops(src, dst, stops)
            if not r.path:
                print("  [X] No complete path found.")
            else:
                print("\n  Path: ", end="")
                print_path(r.path)
                print(f"  Total Distance: {r.total_weight} km")
        elif choice == 6:
            src_in = input("Source: ")
            dst_in = input("Destination: ")
            src = resolve_city(src_in)
            dst = resolve_city(dst_in)
            if not src:
                print(f"  [X] City not found: {src_in}")
                continue
            if not dst:
                print(f"  [X] City not found: {dst_in}")
                continue
            paths = graph.get_alternative_paths(src, dst, 3)
            if not paths or not paths[0].path:
                print("  [X] No path found.")
            else:
                print("\n--- Alternative Paths ---")
                for i, p in enumerate(paths, 1):
                    print(f"  Path {i}: ", end="")
                    print_path(p.path)
                    print(f"    Distance: {p.total_weight} km")


def select_trip_prompt(itinerary: ItineraryTree) -> bool:
    names = itinerary.list_trips()
    if not names:
        print("  No trips yet. Create one first (option 1).")
        return False
    print("\n--- Your Trips ---")
    for i, n in enumerate(names, 1):
        print(f"  {i}. {n}")
    active = itinerary.get_active_trip() + 1
    print(f"  Currently selected: Trip {active}")
    pick = safe_read_int("Switch to trip number (0 to keep current): ")
    if pick == 0:
        return True
    err = itinerary.select_trip(pick)
    if err:
        print(f"  [X] {err}")
        return False
    print(f"  [OK] Switched to Trip {pick}: {itinerary.list_trips()[pick - 1]}")
    return True


def itinerary_menu(itinerary: ItineraryTree, act_mgr: ActivityManager):
    choice = None
    while choice != 0:
        names = itinerary.list_trips()
        print("\n--- ITINERARY PLANNING ---")
        if not names:
            print("  No trips created yet.")
        else:
            print(f"  Active trip: [{itinerary.get_active_trip() + 1}] {names[itinerary.get_active_trip()]}")
        print(f"  (Note: All dates must be in the future - after {get_today_string()})")
        print("1. Create New Trip")
        print("2. Switch Active Trip")
        print("3. Delete a Trip")
        print("4. Add Activity to a Day")
        print("5. Remove Activity")
        print("6. Move Activity to Another Day")
        print("7. Display Full Itinerary")
        print("8. View a Day's Schedule")
        print("9. View Total Cost & Duration")
        print("0. Back")
        choice = safe_read_int("Choice: ")

        if choice == 1:
            name = strip_line(input("Trip name: "))
            start = prompt_future_date("Start date")
            end = prompt_date_on_or_after("End date  ", start)
            err = itinerary.create_itinerary(name, start, end)
            if not err:
                print(f"  [OK] Trip '{name}' created! {itinerary.get_day_count()} day(s) auto-generated.")
                print("  Tip: Use option 4 to add activities to each day.")
            else:
                print(f"  [X] {err}")
        elif choice == 2:
            select_trip_prompt(itinerary)
        elif choice == 3:
            tnames = itinerary.list_trips()
            if not tnames:
                print("  No trips to delete.")
            else:
                print("\n--- Your Trips ---")
                for i, n in enumerate(tnames, 1):
                    print(f"  {i}. {n}")
                pick = safe_read_int("Delete trip number (0 to cancel): ")
                if pick != 0:
                    err = itinerary.delete_trip(pick)
                    if not err:
                        print("  [OK] Trip deleted.")
                    else:
                        print(f"  [X] {err}")
        elif choice == 4:
            if itinerary.get_trip_count() == 0:
                print("  No trips yet. Create one first.")
            else:
                if itinerary.get_trip_count() > 1:
                    print(f"\n  You have {itinerary.get_trip_count()} trips. "
                          f"Which trip do you want to add activities to?")
                    if not select_trip_prompt(itinerary):
                        continue
                day = safe_read_int("Day number: ")
                city_in = strip_line(input("City for activities: "))
                city = act_mgr.resolve_city(city_in)
                if not city:
                    print(f"  [X] City not found: {city_in}")
                else:
                    acts = act_mgr.get_all_activities(city)
                    if not acts:
                        print(f"  No activities found for {city}.")
                    else:
                        print(f"\n--- Activities in {city} ---")
                        for i, a in enumerate(acts, 1):
                            print(f"  {i}. {a.name} | Rs.{a.cost} | *{a.rating} | {a.duration} hrs")
                        pick = safe_read_int("Pick activity number (0 to cancel): ")
                        if 1 <= pick <= len(acts):
                            sel = acts[pick - 1]
                            act = {
                                "id": f"act_{random.randint(0, 9999)}",
                                "name": sel.name,
                                "duration": str(sel.duration),
                                "cost": str(sel.cost),
                            }
                            if itinerary.add_activity(day, act):
                                print(f"  [OK] '{sel.name}' added to Day {day}!")
                            else:
                                print(f"  [X] Day {day} not found in this trip.")
                        elif pick != 0:
                            print("  [X] Invalid selection.")
        elif choice == 5:
            if itinerary.get_trip_count() == 0:
                print("  No trips yet. Create one first.")
                continue
            if itinerary.get_trip_count() > 1:
                select_trip_prompt(itinerary)
            day = safe_read_int("Day number: ")
            aid = strip_line(input("Activity ID: "))
            if itinerary.remove_activity(day, aid):
                print("  [OK] Removed.")
            else:
                print("  [X] Not found.")
        elif choice == 6:
            if itinerary.get_trip_count() == 0:
                print("  No trips yet. Create one first.")
                continue
            if itinerary.get_trip_count() > 1:
                select_trip_prompt(itinerary)
            frm = safe_read_int("From day: ")
            to = safe_read_int("To day: ")
            aid = strip_line(input("Activity ID: "))
            if itinerary.move_activity(frm, to, aid):
                print("  [OK] Moved.")
            else:
                print("  [X] Failed.")
        elif choice == 7:
            if itinerary.get_trip_count() == 0:
                print("  No trips yet. Create one first.")
                continue
            if itinerary.get_trip_count() > 1:
                select_trip_prompt(itinerary)
            print(itinerary.display_itinerary())
        elif choice == 8:
            if itinerary.get_trip_count() == 0:
                print("  No trips yet. Create one first.")
                continue
            if itinerary.get_trip_count() > 1:
                select_trip_prompt(itinerary)
            day = safe_read_int("Day number: ")
            sched = itinerary.get_day_schedule(day)
            print(f"\n--- Day {day} Schedule ---")
            if not sched:
                print("  No activities planned for this day.")
            else:
                for i, a in enumerate(sched, 1):
                    print(f"  {i}. {a['name']} ({a['duration']} hrs, Rs.{a['cost']})")
        elif choice == 9:
            if itinerary.get_trip_count() == 0:
                print("  No trips yet. Create one first.")
                continue
            if itinerary.get_trip_count() > 1:
                select_trip_prompt(itinerary)
            print("\n--- Trip Summary ---")
            print(f"  Total Duration : {itinerary.get_total_duration()} hrs")
            print(f"  Total Cost     : Rs.{itinerary.get_total_cost()}")


def activity_menu(act_mgr: ActivityManager):
    def print_acts(acts):
        if not acts:
            print("  No activities found.")
            return
        for i, a in enumerate(acts, 1):
            print(f"  {i}. {a.name} | Rs.{a.cost} | *{a.rating} | {a.duration} hrs | {a.category}")

    def get_city():
        city_in = strip_line(input("City: "))
        city = act_mgr.resolve_city(city_in)
        if not city:
            print(f"  [X] City not found: {city_in}")
        return city

    choice = None
    while choice != 0:
        print("\n--- ACTIVITY EXPLORER ---")
        print("1. View All Activities in a City")
        print("2. Sort by Cost")
        print("3. Sort by Rating")
        print("4. Sort by Duration")
        print("5. Filter Activities")
        print("6. Search Activity by Name")
        print("7. Browse by Category")
        print("8. Budget Optimizer (Best activities within budget)")
        print("9. Optimal Activity Scheduler (Best combo for time + budget)")
        print("0. Back")
        choice = safe_read_int("Choice: ")

        if choice == 1:
            city = get_city()
            if city:
                print_acts(act_mgr.get_all_activities(city))
        elif choice == 2:
            city = get_city()
            if city:
                ord_ = strip_line(input("Order (asc/desc): "))
                print_acts(act_mgr.sort_by_cost(act_mgr.get_all_activities(city), ord_))
        elif choice == 3:
            city = get_city()
            if city:
                print_acts(act_mgr.sort_by_rating(act_mgr.get_all_activities(city)))
        elif choice == 4:
            city = get_city()
            if city:
                ord_ = strip_line(input("Order (asc/desc): "))
                print_acts(act_mgr.sort_by_duration(act_mgr.get_all_activities(city), ord_))
        elif choice == 5:
            city = get_city()
            if city:
                mc = safe_read_float("Max cost (Rs.): ")
                mr = safe_read_float("Min rating (0-5): ")
                md = safe_read_float("Max duration (hrs): ")
                crit = {"max_cost": mc, "min_rating": mr, "max_duration": md}
                print_acts(act_mgr.filter_activities(act_mgr.get_all_activities(city), crit))
        elif choice == 6:
            city = get_city()
            if city:
                name = strip_line(input("Activity name: "))
                found = act_mgr.find_by_name(city, name)
                if found:
                    print(f"  Found: {found.name} | Rs.{found.cost} | *{found.rating} | {found.duration} hrs")
                else:
                    print("  [X] Activity not found.")
        elif choice == 7:
            cat_in = strip_line(input("Category: "))
            cat = act_mgr.resolve_category(cat_in)
            if not cat:
                print(f"  [X] Category not found: {cat_in}")
            else:
                print_acts(act_mgr.get_by_category(cat))
        elif choice == 8:
            city = get_city()
            if city:
                budget = safe_read_float("  Max Budget (Rs.): ")
                result = act_mgr.budget_optimizer(city, budget)
                print("\n--- Budget Optimizer Results (0/1 Knapsack DP) ---")
                print(f"  Best activities within Rs.{budget} to maximise ratings:\n")
                if not result:
                    print("  No activities found within this budget.")
                else:
                    print_acts(result)
                    total_cost = sum(a.cost for a in result)
                    total_rating = sum(a.rating for a in result)
                    print(f"\n  Total Cost   : Rs.{total_cost}")
                    print(f"  Total Rating : {total_rating}")
        elif choice == 9:
            city = get_city()
            if city:
                max_hours = safe_read_float("  Max Time Available (hrs): ")
                max_budget = safe_read_float("  Max Budget (Rs.): ")
                print("\n  [Backtracking in progress...]")
                result = act_mgr.optimal_schedule(city, max_hours, max_budget)
                print("\n--- Optimal Activity Schedule (Backtracking) ---")
                print(f"  Best combination within {max_hours} hrs & Rs.{max_budget}:\n")
                if not result:
                    print("  No valid combination found within these constraints.")
                else:
                    print_acts(result)
                    total_cost = sum(a.cost for a in result)
                    total_dur = sum(a.duration for a in result)
                    total_rating = sum(a.rating for a in result)
                    print(f"\n  Total Duration : {total_dur} hrs")
                    print(f"  Total Cost     : Rs.{total_cost}")
                    print(f"  Total Rating   : {total_rating}")


def music_library_menu(trie: MusicTrie):
    def print_songs(songs):
        if not songs:
            print("  No songs found.")
            return
        for i, s in enumerate(songs, 1):
            mood = s.metadata.get("mood", "")
            rating = s.metadata.get("rating", "?")
            print(f"  {i}. {s.name} - {s.artist} | {mood} | *{rating}")

    choice = None
    while choice != 0:
        print("\n--- MUSIC LIBRARY ---")
        print("1. Search Songs by Prefix")
        print("2. Autocomplete Song Name")
        print("3. Search Songs by Artist")
        print("4. View All Songs")
        print("5. Full-Text Song Search")
        print("0. Back")
        choice = safe_read_int("Choice: ")

        if choice == 1:
            pf = input("Enter prefix: ")
            print_songs(trie.search_prefix(pf))
        elif choice == 2:
            pf = input("Enter prefix: ")
            lim = safe_read_int("Max suggestions: ")
            print_songs(trie.auto_complete(pf, lim))
        elif choice == 3:
            artist = input("Artist name: ")
            print_songs(trie.search_by_artist(artist))
        elif choice == 4:
            print_songs(trie.get_all_songs())
        elif choice == 5:
            query = input("  Enter search keyword (searches song name & artist): ")
            results = trie.kmp_full_text_search(query)
            print(f"\n--- Full-Text Search Results for \"{query}\" ---")
            print("  (Matches any part of song name or artist name)\n")
            print_songs(results)
            print(f"  Total matches: {len(results)}")


def frequency_menu(tracker: FrequencyTracker, trie: MusicTrie):
    choice = None
    while choice != 0:
        print("\n--- SONG FREQUENCY TRACKER ---")
        print("1. Play a Song (Increment Count)")
        print("2. View Play Count for a Song")
        print("3. View Most Played Songs")
        print("4. Reset All Play Counts")
        print("0. Back")
        choice = safe_read_int("Choice: ")

        if choice == 1:
            sid = strip_line(input("Song name: "))
            all_songs = trie.get_all_songs()
            found = next((s for s in all_songs if s.name == sid), None)
            if found:
                tracker.increment_play_count(sid)
                print(f"  [OK] Now playing: '{found.name}' by {found.artist}")
                print(f"  Play count: {tracker.get_play_count(sid)}")
            else:
                tracker.increment_play_count(sid)
                print(f"  [OK] Play count incremented for '{sid}'.")
                print("  (Note: Song not found in library - check spelling)")
        elif choice == 2:
            sid = strip_line(input("Song name: "))
            print(f"  Play count for '{sid}': {tracker.get_play_count(sid)}")
        elif choice == 3:
            k = safe_read_int("Top N songs: ")
            top = tracker.get_most_played(k)
            print(f"\n--- Top {k} Most Played Songs ---")
            if not top:
                print("  No songs played yet.")
            else:
                for i, (name, cnt) in enumerate(top, 1):
                    print(f"  {i}. {name}  ({cnt} plays)")
        elif choice == 4:
            tracker.reset_frequencies()
            print("  [OK] All play counts reset.")


def playlist_menu(heap: PlaylistHeap, trie: MusicTrie):
    def print_songs(songs):
        if not songs:
            print("  Playlist is empty.")
            return
        for i, s in enumerate(songs, 1):
            print(f"  {i}. {s.name} - {s.artist}")

    choice = None
    while choice != 0:
        print("\n--- PLAYLIST GENERATOR ---")
        print("1. Generate Playlist from Library")
        print("2. View Current Playlist")
        print("3. Add Song to Playlist")
        print("4. Remove Song from Playlist")
        print("5. Shuffle Playlist")
        print("0. Back")
        choice = safe_read_int("Choice: ")

        if choice == 1:
            dur = safe_read_int("Trip duration (minutes): ")
            mood = strip_line(input("Mood (Happy/Romantic/Emotional/Party): "))
            print("Available Genres: Bollywood, Punjabi, Sufi, Indie, Tamil, Telugu, Malayalam")
            genre = strip_line(input("Genre preference (or press Enter for any): "))

            all_songs = trie.get_all_songs()
            filtered = []
            for s in all_songs:
                mood_match = not mood or s.metadata.get("mood") == mood
                genre_match = not genre or s.metadata.get("genre") == genre
                if mood_match and genre_match:
                    filtered.append(s)
            if not filtered:
                print(f"  [X] No songs found for mood='{mood}' genre='{genre}'. Try different filters.")
            else:
                heap.build_max_heap(filtered, "rating")
                pl = heap.generate_playlist(dur, mood, genre)
                print(f"\n  [OK] Playlist Generated ({len(pl)} songs):")
                print_songs(pl)
        elif choice == 2:
            print_songs(heap.get_current_playlist())
        elif choice == 3:
            name = strip_line(input("Song name: "))
            all_songs = trie.get_all_songs()
            found = next((s for s in all_songs if s.name == name), None)
            if found:
                p = float(found.metadata.get("rating", 1.0))
                heap.insert_song(found, p)
                heap.add_to_playlist(found)
                print(f"  [OK] Added '{found.name}' by {found.artist} to playlist.")
            else:
                artist = strip_line(input("Song not found in library. Enter artist name: "))
                heap.add_to_playlist(Song(name, artist, {}))
                print("  [OK] Added.")
        elif choice == 4:
            name = input("Song name: ")
            if heap.remove_from_playlist(name):
                print("  [OK] Removed.")
            else:
                print("  [X] Not found.")
        elif choice == 5:
            print_songs(heap.shuffle_playlist())


# ============================================================
#  SAMPLE DATA
# ============================================================

def load_sample_data(graph: Graph, act_mgr: ActivityManager, trie: MusicTrie):
    cities = [
        "Delhi", "Agra", "Jaipur", "Varanasi", "Lucknow",
        "Amritsar", "Chandigarh", "Shimla", "Manali", "Rishikesh",
        "Haridwar", "Dehradun", "Mathura", "Vrindavan", "Udaipur",
        "Mumbai", "Pune", "Goa", "Ahmedabad", "Surat",
        "Vadodara", "Nashik", "Aurangabad", "Shirdi", "Solapur",
        "Bangalore", "Chennai", "Hyderabad", "Kochi", "Mysore",
        "Coimbatore", "Madurai", "Thiruvananthapuram", "Pondicherry", "Ooty",
        "Mangalore", "Vizag", "Tirupati", "Hampi", "Warangal",
        "Kolkata", "Bhubaneswar", "Puri", "Patna", "Guwahati",
        "Shillong", "Darjeeling", "Siliguri", "Ranchi", "Raipur",
        "Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain",
    ]
    for c in cities:
        graph.add_city(c)

    routes = [
        ("Delhi", "Agra", 200, 350, 3.0), ("Delhi", "Jaipur", 280, 450, 5.0),
        ("Delhi", "Lucknow", 550, 700, 7.5), ("Delhi", "Varanasi", 820, 900, 11.0),
        ("Delhi", "Amritsar", 450, 650, 7.0), ("Delhi", "Chandigarh", 250, 400, 4.5),
        ("Delhi", "Dehradun", 300, 450, 5.5), ("Delhi", "Mathura", 145, 250, 2.5),
        ("Delhi", "Rishikesh", 240, 400, 5.0), ("Delhi", "Haridwar", 220, 370, 4.5),
        ("Agra", "Jaipur", 240, 380, 4.0), ("Agra", "Lucknow", 330, 500, 5.0),
        ("Agra", "Mathura", 58, 120, 1.0), ("Mathura", "Vrindavan", 12, 50, 0.5),
        ("Jaipur", "Udaipur", 395, 600, 6.5), ("Jaipur", "Ahmedabad", 650, 850, 9.0),
        ("Lucknow", "Varanasi", 300, 450, 4.5), ("Lucknow", "Patna", 400, 600, 6.0),
        ("Varanasi", "Patna", 250, 400, 4.0), ("Varanasi", "Kolkata", 650, 800, 9.0),
        ("Chandigarh", "Amritsar", 200, 320, 3.5), ("Chandigarh", "Shimla", 115, 250, 3.0),
        ("Shimla", "Manali", 250, 450, 7.0), ("Rishikesh", "Haridwar", 24, 80, 0.5),
        ("Rishikesh", "Dehradun", 43, 120, 1.0), ("Udaipur", "Ahmedabad", 260, 420, 4.5),
        ("Mumbai", "Pune", 150, 300, 3.0), ("Mumbai", "Goa", 600, 800, 9.0),
        ("Mumbai", "Ahmedabad", 530, 700, 8.0), ("Mumbai", "Nashik", 165, 320, 3.5),
        ("Mumbai", "Aurangabad", 335, 550, 6.0), ("Mumbai", "Hyderabad", 710, 900, 11.0),
        ("Mumbai", "Surat", 280, 450, 5.0), ("Pune", "Goa", 450, 650, 7.0),
        ("Pune", "Hyderabad", 560, 750, 8.5), ("Pune", "Solapur", 250, 400, 4.5),
        ("Pune", "Nashik", 210, 350, 4.0), ("Ahmedabad", "Surat", 260, 400, 4.0),
        ("Ahmedabad", "Vadodara", 110, 220, 2.0), ("Ahmedabad", "Bhopal", 490, 700, 8.0),
        ("Nashik", "Shirdi", 90, 180, 2.0), ("Aurangabad", "Shirdi", 125, 250, 3.0),
        ("Solapur", "Hyderabad", 320, 500, 5.5), ("Bangalore", "Chennai", 350, 500, 6.0),
        ("Bangalore", "Hyderabad", 570, 750, 9.0), ("Bangalore", "Mysore", 145, 250, 3.0),
        ("Bangalore", "Kochi", 540, 750, 9.0), ("Bangalore", "Coimbatore", 360, 520, 6.0),
        ("Bangalore", "Mangalore", 350, 550, 6.5), ("Bangalore", "Hampi", 340, 550, 6.0),
        ("Chennai", "Hyderabad", 630, 800, 10.0), ("Chennai", "Kochi", 680, 850, 11.0),
        ("Chennai", "Madurai", 460, 650, 8.0), ("Chennai", "Pondicherry", 150, 280, 3.0),
        ("Chennai", "Tirupati", 140, 260, 2.5), ("Hyderabad", "Vizag", 620, 800, 10.0),
        ("Hyderabad", "Warangal", 145, 280, 3.0), ("Hyderabad", "Tirupati", 540, 750, 9.0),
        ("Kochi", "Thiruvananthapuram", 210, 350, 4.0), ("Kochi", "Mysore", 480, 680, 8.5),
        ("Kochi", "Coimbatore", 180, 320, 3.5), ("Mysore", "Ooty", 120, 240, 3.0),
        ("Coimbatore", "Ooty", 85, 180, 2.5), ("Coimbatore", "Madurai", 210, 360, 4.0),
        ("Madurai", "Thiruvananthapuram", 290, 480, 5.5), ("Kolkata", "Bhubaneswar", 440, 650, 7.0),
        ("Kolkata", "Patna", 540, 750, 8.5), ("Kolkata", "Guwahati", 1000, 1200, 16.0),
        ("Kolkata", "Darjeeling", 600, 800, 10.0), ("Kolkata", "Siliguri", 570, 780, 9.5),
        ("Bhubaneswar", "Puri", 65, 140, 1.5), ("Bhubaneswar", "Vizag", 440, 650, 8.0),
        ("Guwahati", "Shillong", 98, 200, 2.5), ("Darjeeling", "Siliguri", 80, 160, 2.5),
        ("Patna", "Ranchi", 320, 500, 6.0), ("Ranchi", "Raipur", 450, 650, 8.0),
        ("Bhopal", "Indore", 195, 350, 3.5), ("Bhopal", "Jabalpur", 290, 480, 5.0),
        ("Bhopal", "Gwalior", 420, 620, 7.0), ("Bhopal", "Ujjain", 190, 340, 3.5),
        ("Indore", "Ujjain", 55, 130, 1.5), ("Indore", "Ahmedabad", 390, 580, 6.5),
        ("Gwalior", "Agra", 120, 240, 2.5), ("Jabalpur", "Raipur", 340, 520, 6.0),
        ("Raipur", "Hyderabad", 600, 820, 10.0), ("Raipur", "Bhubaneswar", 440, 650, 8.0),
    ]
    for c1, c2, dist, cost, time_ in routes:
        graph.add_route(c1, c2, dist, cost, time_)

    activities = [
        ("Red Fort", "Delhi", "History", 50, 4.7, 3), ("Qutub Minar", "Delhi", "History", 40, 4.6, 2),
        ("India Gate", "Delhi", "Sightseeing", 0, 4.5, 1), ("Humayun's Tomb", "Delhi", "History", 35, 4.7, 2),
        ("Chandni Chowk Food Walk", "Delhi", "Food", 0, 4.8, 2), ("Lotus Temple", "Delhi", "Spiritual", 0, 4.6, 1),
        ("Akshardham Temple", "Delhi", "Spiritual", 0, 4.8, 3), ("Taj Mahal", "Agra", "Sightseeing", 50, 5.0, 3),
        ("Agra Fort", "Agra", "History", 40, 4.6, 2), ("Fatehpur Sikri", "Agra", "History", 40, 4.5, 3),
        ("Mehtab Bagh Sunset", "Agra", "Nature", 30, 4.7, 1), ("Amber Fort", "Jaipur", "History", 100, 4.8, 3),
        ("Hawa Mahal", "Jaipur", "Sightseeing", 50, 4.7, 1), ("City Palace Jaipur", "Jaipur", "Culture", 200, 4.6, 2),
        ("Jantar Mantar Jaipur", "Jaipur", "History", 50, 4.4, 1), ("Nahargarh Fort", "Jaipur", "History", 50, 4.5, 2),
        ("Ganga Aarti", "Varanasi", "Spiritual", 0, 4.9, 2),
        ("Kashi Vishwanath Temple", "Varanasi", "Spiritual", 0, 4.8, 2),
        ("Boat Ride on Ganga", "Varanasi", "Nature", 150, 4.7, 2),
        ("Sarnath Stupa", "Varanasi", "History", 30, 4.5, 2),
        ("Golden Temple", "Amritsar", "Spiritual", 0, 5.0, 3),
        ("Wagah Border Ceremony", "Amritsar", "Sightseeing", 0, 4.8, 2),
        ("Jallianwala Bagh", "Amritsar", "History", 0, 4.6, 1),
        ("Mall Road Shimla", "Shimla", "Sightseeing", 0, 4.5, 2),
        ("Kufri Snow Point", "Shimla", "Adventure", 200, 4.6, 3),
        ("Christ Church Shimla", "Shimla", "Culture", 0, 4.4, 1),
        ("Rohtang Pass", "Manali", "Adventure", 500, 4.8, 6),
        ("Solang Valley", "Manali", "Adventure", 300, 4.7, 4),
        ("Hadimba Temple", "Manali", "Spiritual", 0, 4.6, 1),
        ("River Rafting", "Rishikesh", "Adventure", 600, 4.8, 4),
        ("Laxman Jhula", "Rishikesh", "Sightseeing", 0, 4.5, 1),
        ("Beatles Ashram", "Rishikesh", "Culture", 150, 4.4, 2),
        ("Bungee Jumping Rishikesh", "Rishikesh", "Adventure", 3500, 4.9, 2),
        ("Gateway of India", "Mumbai", "Sightseeing", 0, 4.6, 1),
        ("Marine Drive", "Mumbai", "Sightseeing", 0, 4.7, 2),
        ("Elephanta Caves", "Mumbai", "History", 40, 4.5, 4),
        ("Dharavi Walk Tour", "Mumbai", "Culture", 500, 4.4, 3),
        ("Siddhivinayak Temple", "Mumbai", "Spiritual", 0, 4.7, 1),
        ("Juhu Beach", "Mumbai", "Nature", 0, 4.3, 2),
        ("Baga Beach", "Goa", "Nature", 0, 4.6, 4),
        ("Dudhsagar Falls", "Goa", "Nature", 400, 4.8, 6),
        ("Old Goa Churches", "Goa", "History", 0, 4.5, 2),
        ("Casino Night Cruise", "Goa", "Entertainment", 2000, 4.3, 4),
        ("Scuba Diving Goa", "Goa", "Adventure", 3000, 4.7, 3),
        ("City Palace Udaipur", "Udaipur", "History", 300, 4.8, 3),
        ("Lake Pichola Boat Ride", "Udaipur", "Nature", 400, 4.7, 2),
        ("Saheliyon ki Bari", "Udaipur", "Nature", 25, 4.4, 1),
        ("Vintage Car Museum", "Udaipur", "Culture", 250, 4.5, 2),
        ("Sabarmati Ashram", "Ahmedabad", "History", 0, 4.7, 2),
        ("Kite Museum", "Ahmedabad", "Culture", 25, 4.3, 1),
        ("Adalaj Stepwell", "Ahmedabad", "History", 0, 4.6, 1),
        ("Ajanta Caves", "Aurangabad", "History", 40, 4.9, 5),
        ("Ellora Caves", "Aurangabad", "History", 40, 4.9, 5),
        ("Bibi Ka Maqbara", "Aurangabad", "History", 25, 4.5, 2),
        ("Lalbagh Botanical Garden", "Bangalore", "Nature", 20, 4.5, 2),
        ("Bangalore Palace", "Bangalore", "History", 230, 4.3, 2),
        ("ISKCON Temple Bangalore", "Bangalore", "Spiritual", 0, 4.7, 1),
        ("Nandi Hills", "Bangalore", "Nature", 30, 4.6, 4),
        ("Mysore Palace", "Mysore", "History", 50, 4.9, 3),
        ("Chamundi Hills", "Mysore", "Spiritual", 0, 4.6, 2),
        ("Brindavan Gardens", "Mysore", "Nature", 40, 4.5, 2),
        ("Chinese Fishing Nets", "Kochi", "Sightseeing", 0, 4.5, 1),
        ("Alleppey Backwaters", "Kochi", "Nature", 800, 4.9, 5),
        ("Mattancherry Palace", "Kochi", "History", 20, 4.4, 2),
        ("Fort Kochi Heritage Walk", "Kochi", "Culture", 200, 4.6, 3),
        ("Charminar", "Hyderabad", "History", 20, 4.7, 2),
        ("Golconda Fort", "Hyderabad", "History", 15, 4.6, 3),
        ("Ramoji Film City", "Hyderabad", "Entertainment", 1200, 4.5, 8),
        ("Hussain Sagar Lake", "Hyderabad", "Nature", 100, 4.4, 2),
        ("Marina Beach", "Chennai", "Nature", 0, 4.5, 2),
        ("Kapaleeshwarar Temple", "Chennai", "Spiritual", 0, 4.7, 1),
        ("Government Museum", "Chennai", "Culture", 15, 4.4, 2),
        ("Victoria Memorial", "Kolkata", "History", 30, 4.8, 2),
        ("Howrah Bridge", "Kolkata", "Sightseeing", 0, 4.6, 1),
        ("Dakshineswar Temple", "Kolkata", "Spiritual", 0, 4.7, 2),
        ("Street Food Tour Kolkata", "Kolkata", "Food", 0, 4.8, 3),
        ("Tiger Hill Sunrise", "Darjeeling", "Nature", 100, 4.8, 4),
        ("Toy Train Ride", "Darjeeling", "Culture", 600, 4.7, 4),
        ("Tea Garden Visit", "Darjeeling", "Nature", 200, 4.6, 3),
        ("Jagannath Temple", "Puri", "Spiritual", 0, 4.9, 2),
        ("Puri Beach", "Puri", "Nature", 0, 4.5, 3),
        ("Virupaksha Temple", "Hampi", "Spiritual", 30, 4.8, 2),
        ("Hampi Ruins Exploration", "Hampi", "History", 40, 4.9, 5),
        ("Tirumala Venkateswara", "Tirupati", "Spiritual", 50, 5.0, 4),
        ("Mahakaleshwar Temple", "Ujjain", "Spiritual", 0, 4.9, 2),
        ("Kshipra River Aarti", "Ujjain", "Spiritual", 0, 4.6, 1),
    ]
    for name, loc, cat, cost, rating, dur in activities:
        act_mgr.add_activity_to_db(name, loc, cat, cost, rating, dur)

    # (name, artist, genre, mood, rating)
    songs = [
        ("Badtameez Dil", "Benny Dayal", "Bollywood", "Happy", "4.7"),
        ("Gallan Goodiyaan", "Shankar Mahadevan", "Bollywood", "Happy", "4.8"),
        ("London Thumakda", "Labh Janjua", "Bollywood", "Happy", "4.7"),
        ("Nagada Sang Dhol", "Shreya Ghoshal", "Bollywood", "Happy", "4.6"),
        ("Balam Pichkari", "Shalmali Kholgade", "Bollywood", "Happy", "4.5"),
        ("Kar Gayi Chull", "Fazilpuria", "Bollywood", "Happy", "4.5"),
        ("Dil Dhadakne Do", "Shankar Ehsaan", "Bollywood", "Happy", "4.6"),
        ("Dhinka Chika", "Neeraj Shridhar", "Bollywood", "Happy", "4.4"),
        ("Senorita", "Shaan", "Bollywood", "Happy", "4.5"),
        ("Zindagi Na Milegi Dobara", "Shankar Mahadevan", "Bollywood", "Happy", "4.8"),
        ("Jai Ho", "A.R. Rahman", "Bollywood", "Happy", "4.9"),
        ("Vande Mataram", "A.R. Rahman", "Patriotic", "Happy", "5.0"),
        ("Maa Tujhe Salaam", "A.R. Rahman", "Patriotic", "Happy", "4.9"),
        ("Rang De Basanti", "Daler Mehndi", "Bollywood", "Happy", "4.7"),
        ("Zinda", "Siddharth Mahadevan", "Bollywood", "Happy", "4.8"),
        ("Nashe Si Chadh Gayi", "Arijit Singh", "Bollywood", "Happy", "4.6"),
        ("Swag Se Swagat", "Vishal Dadlani", "Bollywood", "Happy", "4.5"),
        ("Photocopy", "Anushka Manchanda", "Bollywood", "Happy", "4.4"),
        ("Naatu Naatu", "Rahul Sipligunj", "Telugu", "Happy", "5.0"),
        ("G.O.A.T", "Diljit Dosanjh", "Punjabi", "Happy", "4.7"),
        ("Lover", "Diljit Dosanjh", "Punjabi", "Happy", "4.6"),
        ("Lahore", "Guru Randhawa", "Punjabi", "Happy", "4.5"),
        ("Morni Banke", "Neha Kakkar", "Bollywood", "Happy", "4.4"),
        ("Unakenna Venum Sollu", "Anirudh Ravichander", "Tamil", "Happy", "4.6"),
        ("Saibo", "Shreya Ghoshal", "Bollywood", "Happy", "4.7"),
        ("Tum Hi Ho", "Arijit Singh", "Bollywood", "Emotional", "4.9"),
        ("Channa Mereya", "Arijit Singh", "Bollywood", "Emotional", "4.9"),
        ("Kal Ho Naa Ho", "Sonu Nigam", "Bollywood", "Emotional", "4.8"),
        ("Ae Dil Hai Mushkil", "Arijit Singh", "Bollywood", "Emotional", "4.7"),
        ("Kabhi Alvida Naa Kehna", "Sonu Nigam", "Bollywood", "Emotional", "4.7"),
        ("Dil To Pagal Hai", "Lata Mangeshkar", "Bollywood", "Emotional", "4.8"),
        ("Phir Le Aya Dil", "Rekha Bhardwaj", "Bollywood", "Emotional", "4.6"),
        ("Hamari Adhuri Kahani", "Arijit Singh", "Bollywood", "Emotional", "4.6"),
        ("Dard Dilo Ke", "Mohammed Irfan", "Bollywood", "Emotional", "4.5"),
        ("Main Dhoondne Ko Zamaane", "Arijit Singh", "Bollywood", "Emotional", "4.6"),
        ("Jeena Jeena", "Atif Aslam", "Bollywood", "Emotional", "4.7"),
        ("O Saathi", "Atif Aslam", "Bollywood", "Emotional", "4.6"),
        ("Tera Hone Laga Hoon", "Atif Aslam", "Bollywood", "Emotional", "4.5"),
        ("Bulleya", "Amit Mishra", "Sufi", "Emotional", "4.8"),
        ("Ik Onkar", "Harshdeep Kaur", "Sufi", "Emotional", "4.9"),
        ("Dil Diyan Gallan", "Atif Aslam", "Indie", "Emotional", "4.7"),
        ("Pasoori", "Ali Sethi", "Indie", "Emotional", "5.0"),
        ("Ve Maahi", "Arijit Singh", "Bollywood", "Emotional", "4.8"),
        ("Agar Tum Saath Ho", "Arijit Singh", "Bollywood", "Emotional", "4.9"),
        ("Chaiyya Chaiyya", "Sukhwinder Singh", "Bollywood", "Emotional", "5.0"),
        ("Kannazhaga", "Shreya Ghoshal", "Tamil", "Emotional", "4.8"),
        ("Vathikkalu Vathikkalu", "K.S. Chithra", "Malayalam", "Emotional", "4.7"),
        ("Nenjukkul Peidhidum", "Harris Jayaraj", "Tamil", "Emotional", "4.8"),
        ("Kesariya", "Arijit Singh", "Bollywood", "Emotional", "4.9"),
        ("Raabta", "Arijit Singh", "Bollywood", "Emotional", "4.5"),
        ("Tujh Mein Rab Dikhta Hai", "Roop Kumar Rathod", "Bollywood", "Romantic", "4.9"),
        ("Pehla Nasha", "Udit Narayan", "Bollywood", "Romantic", "5.0"),
        ("Lag Ja Gale", "Lata Mangeshkar", "Bollywood", "Romantic", "5.0"),
        ("Kuch Kuch Hota Hai", "Udit Narayan", "Bollywood", "Romantic", "4.9"),
        ("Tere Liye", "Atif Aslam", "Bollywood", "Romantic", "4.7"),
        ("Sun Saathiya", "Shreya Ghoshal", "Bollywood", "Romantic", "4.6"),
        ("Teri Meri Prem Kahani", "Udit Narayan", "Bollywood", "Romantic", "4.6"),
        ("Jab Se Tere Naina", "Udit Narayan", "Bollywood", "Romantic", "4.7"),
        ("Soch Na Sake", "Arijit Singh", "Punjabi", "Romantic", "4.7"),
        ("Enna Sona", "Arijit Singh", "Bollywood", "Romantic", "4.8"),
        ("Dil Ko Karaar Aaya", "Neha Kakkar", "Bollywood", "Romantic", "4.6"),
        ("Hawayein", "Arijit Singh", "Bollywood", "Romantic", "4.9"),
        ("Rehnaa Hai Terre Dil Mein", "Rehman", "Bollywood", "Romantic", "4.8"),
        ("Pehli Baar Mohabbat", "Mohit Chauhan", "Bollywood", "Romantic", "4.7"),
        ("Abhi Mujh Mein Kahin", "Sonu Nigam", "Bollywood", "Romantic", "4.8"),
        ("Tera Ban Jaunga", "Akhil Sachdeva", "Bollywood", "Romantic", "4.7"),
        ("Apna Bana Le", "Arijit Singh", "Bollywood", "Romantic", "4.7"),
        ("Mere Haath Mein", "Udit Narayan", "Bollywood", "Romantic", "4.6"),
        ("Tere Sang Yaara", "Atif Aslam", "Bollywood", "Romantic", "4.7"),
        ("Kho Gaye Hum Kahan", "Jasleen Royal", "Indie", "Romantic", "4.8"),
        ("Mahi Ve", "Udit Narayan", "Bollywood", "Romantic", "4.7"),
        ("Ilahi", "Mohit Chauhan", "Bollywood", "Romantic", "4.6"),
        ("Manike Mage Hithe", "Yohani", "Indie", "Romantic", "4.6"),
        ("Kalank", "Arijit Singh", "Bollywood", "Romantic", "4.5"),
        ("Tujhe Kitna Chahne Lage", "Arijit Singh", "Bollywood", "Romantic", "4.9"),
        ("Lungi Dance", "Honey Singh", "Bollywood", "Party", "4.6"),
        ("Angrezi Beat", "Honey Singh", "Punjabi", "Party", "4.5"),
        ("Party All Night", "Honey Singh", "Punjabi", "Party", "4.5"),
        ("Desi Beat", "Honey Singh", "Punjabi", "Party", "4.4"),
        ("Hookah Bar", "Akshay Kumar", "Bollywood", "Party", "4.4"),
        ("Dancefloor", "Badshah", "Punjabi", "Party", "4.5"),
        ("Abcd", "Badshah", "Punjabi", "Party", "4.6"),
        ("DJ Waley Babu", "Badshah", "Punjabi", "Party", "4.5"),
        ("Garmi", "Badshah", "Bollywood", "Party", "4.6"),
        ("Paagal", "Badshah", "Punjabi", "Party", "4.5"),
        ("Kala Chashma", "Baar Baar Dekho", "Bollywood", "Party", "4.7"),
        ("Saturday Saturday", "Indeep Bakshi", "Bollywood", "Party", "4.5"),
        ("Malhari", "Vishal Dadlani", "Bollywood", "Party", "4.8"),
        ("Tattad Tattad", "Aditya Narayan", "Bollywood", "Party", "4.5"),
        ("Bhaag DK Bose", "Raghu Dixit", "Bollywood", "Party", "4.4"),
        ("Ainvayi Ainvayi", "Salim Merchant", "Bollywood", "Party", "4.5"),
        ("Jhoome Jo Pathaan", "Arijit Singh", "Bollywood", "Party", "4.6"),
        ("Besharam Rang", "Caralisa Monteiro", "Bollywood", "Party", "4.5"),
        ("Ghungroo", "Arijit Singh", "Bollywood", "Party", "4.7"),
        ("Oo Antava", "Indravathi Chauhan", "Telugu", "Party", "4.7"),
        ("Bijlee Bijlee", "Harrdy Sandhu", "Punjabi", "Party", "4.6"),
        ("Koka", "Diljit Dosanjh", "Punjabi", "Party", "4.5"),
        ("Patiala Peg", "Diljit Dosanjh", "Punjabi", "Party", "4.5"),
        ("Amplifier", "Imran Khan", "Punjabi", "Party", "4.6"),
        ("Kar Har Maidaan Fateh", "Sukhwinder Singh", "Bollywood", "Party", "4.8"),
    ]
    for name, artist, genre, mood, rating in songs:
        trie.insert_song(name, artist, {"genre": genre, "mood": mood, "rating": rating})


# ============================================================
#  MAIN
# ============================================================

def main():
    random.seed()

    graph = Graph()
    itinerary = ItineraryTree()
    act_mgr = ActivityManager()
    music_trie = MusicTrie()
    tracker = FrequencyTracker()
    playlist_heap = PlaylistHeap()

    load_sample_data(graph, act_mgr, music_trie)

    choice = None
    while choice != 0:
        print("\n----------------------------------------------------------")
        print("                       TRIPTUNES                         ")
        print("          Your Travel & Music Companion                   ")
        print("----------------------------------------------------------")
        print("----------------------------------------------------------")
        print("  1.  Route Planning                                      ")
        print("  2.  Itinerary Planning                                  ")
        print("  3.  Activity Explorer                                   ")
        print("  4.  Music Library                                       ")
        print("  5.  Song Frequency Tracker                              ")
        print("  6.  Playlist Generator                                  ")
        print("  7.  Admin Control Panel                                 ")
        print("  0.  Exit                                                ")
        print("----------------------------------------------------------")
        choice = safe_read_int("Enter choice: ")

        if choice == 1:
            route_planning_menu(graph)
        elif choice == 2:
            itinerary_menu(itinerary, act_mgr)
        elif choice == 3:
            activity_menu(act_mgr)
        elif choice == 4:
            music_library_menu(music_trie)
        elif choice == 5:
            frequency_menu(tracker, music_trie)
        elif choice == 6:
            playlist_menu(playlist_heap, music_trie)
        elif choice == 7:
            admin_panel(graph, act_mgr)
        elif choice == 0:
            print("\n  Thank you for using TripTunes! Happy travels!\n")
        else:
            print("  Invalid choice. Please try again.")


if __name__ == "__main__":
    main()