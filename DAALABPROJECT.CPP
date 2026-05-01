#include <iostream>
#include <vector>
#include <unordered_map>
#include <queue>
#include <algorithm>
#include <string>
#include <limits>
#include <ctime>
#include <map>
#include <set>
#include <random>
using namespace std;

string getTodayString() {
    time_t now = time(nullptr);
    struct tm* t = localtime(&now);
    char buf[11];
    strftime(buf, sizeof(buf), "%Y-%m-%d", t);
    return string(buf);
}


bool parseDate(const string& s_raw, int& y, int& m, int& d) {
    string s = s_raw;
    while (!s.empty() && (s.back() == '\r' || s.back() == ' ')) s.pop_back();
    if (s.size() != 10 || s[4] != '-' || s[7] != '-') return false;
    try {
        y = stoi(s.substr(0, 4));
        m = stoi(s.substr(5, 2));
        d = stoi(s.substr(8, 2));
    } catch (...) { return false; }
    if (m < 1 || m > 12 || d < 1 || d > 31) return false;
    return true;
}

bool dateAfterToday(const string& dateStr) {
    return dateStr > getTodayString();
}

bool dateA_before_dateB(const string& a, const string& b) {
    return a < b;
}

static void stripLine(string& s) {
    while (!s.empty() && (s.back() == '\r' || s.back() == '\n' || s.back() == ' '))
        s.pop_back();
}

string promptFutureDate(const string& label) {
    string d;
    while (true) {
        cout << label << " (YYYY-MM-DD, must be after " << getTodayString() << "): ";
        getline(cin, d);
        stripLine(d);
        int y, m, day;
        if (!parseDate(d, y, m, day)) {
            cout << "  [X] Invalid format. Please use YYYY-MM-DD.\n";
            continue;
        }
        if (!dateAfterToday(d)) {
            cout << "  [X] Date must be in the future (after " << getTodayString() << ").\n";
            continue;
        }
        return d;
    }
}

string promptDateOnOrAfter(const string& label, const string& minDate) {
    string d;
    while (true) {
        cout << label << " (YYYY-MM-DD, must be on or after " << minDate << "): ";
        getline(cin, d);
        stripLine(d);
        int y, m, day;
        if (!parseDate(d, y, m, day)) {
            cout << "  [X] Invalid format. Please use YYYY-MM-DD.\n";
            continue;
        }
        if (!dateAfterToday(d)) {
            cout << "  [X] Date must be in the future (after " << getTodayString() << ").\n";
            continue;
        }
        if (d < minDate) {
            cout << "  [X] End date must be on or after start date (" << minDate << ").\n";
            continue;
        }
        return d;
    }
}

//  ADMIN AUTHENTICATION

const string ADMIN_PASSWORD = "JHIN TAPAK DUM DUM";

bool authenticateAdmin() {
    string pwd;
    cout << "\n  Enter Admin Password: ";
    // FIX: safeReadInt already flushed the newline; no extra ignore needed
    getline(cin, pwd);
    if (pwd == ADMIN_PASSWORD) {
        cout << "  [OK] Access granted. Welcome, Admin!\n";
        return true;
    }
    cout << "  [X] Incorrect password. Access denied.\n";
    return false;
}

//  GRAPH  (Route Planning)

struct Route {
    string destination;
    double distance;
    double cost;
    double time;
};

class Graph {
private:
    unordered_map<string, map<string, string>> cities;
    unordered_map<string, vector<Route>> routes;

    struct PathResult {
        vector<string> path;
        double totalWeight;
        string weightType;
    };

    PathResult dijkstra(const string& source, const string& destination, const string& weightType) {
        if (cities.find(source) == cities.end() || cities.find(destination) == cities.end()) {
            return {{}, numeric_limits<double>::infinity(), weightType};
        }

        unordered_map<string, double> distances;
        unordered_map<string, string> previous;

        for (const auto& city : cities)
            distances[city.first] = numeric_limits<double>::infinity();
        distances[source] = 0;
        previous[source] = "";

        auto cmp = [](pair<double,string> a, pair<double,string> b){ return a.first > b.first; };
        priority_queue<pair<double,string>, vector<pair<double,string>>, decltype(cmp)> pq(cmp);
        pq.push({0, source});

        while (!pq.empty()) {
            auto [currentDist, current] = pq.top(); pq.pop();
            if (current == destination) break;
            if (currentDist > distances[current]) continue;

            for (const Route& r : routes[current]) {
                if (cities.find(r.destination) == cities.end()) continue;
                double w = (weightType=="distance") ? r.distance
                         : (weightType=="cost")     ? r.cost
                                                    : r.time;
                double nd = currentDist + w;
                if (nd < distances[r.destination]) {
                    distances[r.destination] = nd;
                    previous[r.destination]  = current;
                    pq.push({nd, r.destination});
                }
            }
        }

        if (distances[destination] == numeric_limits<double>::infinity()) {
            return {{}, numeric_limits<double>::infinity(), weightType};
        }

        vector<string> path;
        string cur = destination;
        while (cur != "") {
            path.push_back(cur);
            auto it = previous.find(cur);
            if (it == previous.end()) break;
            cur = it->second;
        }
        reverse(path.begin(), path.end());
        return {path, distances[destination], weightType};
    }

public:
    bool addCity(const string& cityName, const map<string,string>& metadata = {}) {
        if (cities.find(cityName) == cities.end()) {
            cities[cityName] = metadata;
            return true;
        }
        return false;
    }

    bool removeCity(const string& cityName) {
        if (cities.find(cityName) == cities.end()) return false;
        cities.erase(cityName);
        routes.erase(cityName);
        for (auto& [c, rs] : routes)
            rs.erase(remove_if(rs.begin(), rs.end(),
                [&cityName](const Route& r){ return r.destination == cityName; }), rs.end());
        return true;
    }

    void addRoute(const string& c1, const string& c2, double dist, double cost, double time) {
        // FIX: only add route if both cities exist
        if (cities.find(c1) == cities.end() || cities.find(c2) == cities.end()) {
            cout << "  [X] Cannot add route: one or both cities not found.\n";
            return;
        }
        routes[c1].push_back({c2, dist, cost, time});
        routes[c2].push_back({c1, dist, cost, time});
    }

    void removeRoute(const string& c1, const string& c2) {
        auto& r1 = routes[c1];
        r1.erase(remove_if(r1.begin(), r1.end(),
            [&c2](const Route& r){ return r.destination == c2; }), r1.end());
        auto& r2 = routes[c2];
        r2.erase(remove_if(r2.begin(), r2.end(),
            [&c1](const Route& r){ return r.destination == c1; }), r2.end());
    }

    vector<string> getAllCities() {
        vector<string> v;
        for (const auto& c : cities) v.push_back(c.first);
        sort(v.begin(), v.end());
        return v;
    }

    PathResult findShortestPath(const string& src, const string& dst) { return dijkstra(src,dst,"distance"); }
    PathResult findCheapestPath(const string& src, const string& dst) { return dijkstra(src,dst,"cost"); }
    PathResult findFastestPath (const string& src, const string& dst) { return dijkstra(src,dst,"time"); }

    PathResult findPathWithStops(const string& src, const string& dst, const vector<string>& stops) {
        vector<string> all = {src};
        all.insert(all.end(), stops.begin(), stops.end());
        all.push_back(dst);
        vector<string> totalPath;
        double totalDist = 0;
        for (size_t i = 0; i < all.size()-1; i++) {
            PathResult r = findShortestPath(all[i], all[i+1]);
            if (r.path.empty() || r.totalWeight == numeric_limits<double>::infinity()) {
                return {{}, numeric_limits<double>::infinity(), "distance"};
            }
            totalPath.insert(totalPath.end(), r.path.begin(), r.path.end() - 1);
            totalDist += r.totalWeight;
        }
        totalPath.push_back(dst);
        return {totalPath, totalDist, "distance"};
    }

    vector<PathResult> getAlternativePaths(const string& src, const string& dst, int k=3) {
        vector<PathResult> paths;
        PathResult main = findShortestPath(src,dst);
        if (main.path.empty()) return paths;
        paths.push_back(main);
        for (size_t i=1; i<main.path.size()-1 && (int)paths.size()<k; i++) {
            string excl = main.path[i];
            vector<Route> tmp = routes[excl];
            routes[excl].clear();
            PathResult alt = findShortestPath(src,dst);
            routes[excl] = tmp;
            if (!alt.path.empty() && alt.totalWeight != numeric_limits<double>::infinity())
                paths.push_back(alt);
        }
        return paths;
    }
};

//  ITINERARY TREE

class ItineraryNode {
public:
    string nodeType;
    map<string,string> data;
    vector<ItineraryNode*> children;

    ItineraryNode(const string& t, const map<string,string>& d) : nodeType(t), data(d) {}

    void addChild(ItineraryNode* c) { children.push_back(c); }

    void removeChild(ItineraryNode* c) {
        children.erase(remove(children.begin(), children.end(), c), children.end());
    }

    ~ItineraryNode() { for (auto ch : children) delete ch; }
};

class ItineraryTree {
private:
    vector<ItineraryNode*> trips;
    int activeTrip = -1;

    ItineraryNode* current() {
        if (activeTrip < 0 || activeTrip >= (int)trips.size()) return nullptr;
        return trips[activeTrip];
    }

    void buildDays(ItineraryNode* root, const string& startDate, const string& endDate) {
        int sy, sm, sd_v, ey, em, ed_v;
        parseDate(startDate, sy, sm, sd_v);
        parseDate(endDate,   ey, em, ed_v);
        struct tm cur = {};
        cur.tm_year = sy - 1900; cur.tm_mon = sm - 1; cur.tm_mday = sd_v;
        mktime(&cur);
        struct tm last_day = {};
        last_day.tm_year = ey - 1900; last_day.tm_mon = em - 1; last_day.tm_mday = ed_v;
        mktime(&last_day);
        int dayNum = 1;
        while (dayNum <= 365) {
            char buf[11];
            strftime(buf, sizeof(buf), "%Y-%m-%d", &cur);
            map<string,string> dd = {{"day_number", to_string(dayNum)}, {"date", string(buf)}};
            root->addChild(new ItineraryNode("day", dd));
            if (mktime(&cur) >= mktime(&last_day)) break;
            cur.tm_mday++; mktime(&cur); dayNum++;
        }
    }

public:
    ItineraryTree() {}


    string createItinerary(const string& name, const string& startDate, const string& endDate) {
        if (!dateAfterToday(startDate))
            return "Start date must be in the future (after " + getTodayString() + ").";
        if (!dateAfterToday(endDate))
            return "End date must be in the future (after " + getTodayString() + ").";
        if (endDate < startDate)
            return "End date must be on or after the start date.";
        map<string,string> d = {{"name",name},{"start_date",startDate},{"end_date",endDate}};
        ItineraryNode* root = new ItineraryNode("trip", d);
        buildDays(root, startDate, endDate);
        trips.push_back(root);
        activeTrip = (int)trips.size() - 1;   // auto-select the new trip
        return "";
    }

    vector<string> listTrips() const {
        vector<string> names;
        for (auto t : trips)
            names.push_back(t->data.at("name") + "  [" +
                            t->data.at("start_date") + " -> " +
                            t->data.at("end_date") + "]");
        return names;
    }

    int getTripCount() const { return (int)trips.size(); }
    int getActiveTrip() const { return activeTrip; }

    string selectTrip(int idx) {
        if (idx < 1 || idx > (int)trips.size())
            return "Invalid trip number.";
        activeTrip = idx - 1;
        return "";
    }

    string deleteTrip(int idx) {
        if (idx < 1 || idx > (int)trips.size())
            return "Invalid trip number.";
        delete trips[idx-1];
        trips.erase(trips.begin() + (idx-1));
        if (trips.empty()) activeTrip = -1;
        else activeTrip = min(activeTrip, (int)trips.size()-1);
        return "";
    }


    string addDay(int dayNumber, const string& date) {
        ItineraryNode* root = current();
        if (!root) return "No trip selected. Create or select a trip first.";
        if (!dateAfterToday(date))
            return "Day date must be in the future (after " + getTodayString() + ").";
        if (date < root->data["start_date"] || date > root->data["end_date"])
            return "Day date must be within the trip period ("
                 + root->data["start_date"] + " to " + root->data["end_date"] + ").";
        map<string,string> d = {{"day_number",to_string(dayNumber)},{"date",date}};
        root->addChild(new ItineraryNode("day", d));
        return "";
    }


    ItineraryNode* addActivity(int dayNumber, const map<string,string>& activity) {
        ItineraryNode* root = current();
        if (!root) return nullptr;
        for (auto dayNode : root->children) {
            if (dayNode->data["day_number"] == to_string(dayNumber)) {
                ItineraryNode* act = new ItineraryNode("activity", activity);
                dayNode->addChild(act);
                return act;
            }
        }
        return nullptr;
    }

    bool removeActivity(int dayNumber, const string& activityId) {
        ItineraryNode* root = current();
        if (!root) return false;
        for (auto dayNode : root->children) {
            if (dayNode->data["day_number"] == to_string(dayNumber)) {
                for (auto act : dayNode->children) {
                    if (act->data["id"] == activityId) {
                        dayNode->removeChild(act);
                        delete act;
                        return true;
                    }
                }
            }
        }
        return false;
    }

    ItineraryNode* moveActivity(int fromDay, int toDay, const string& activityId) {
        map<string,string> actData;
        ItineraryNode* root = current();
        if (!root) return nullptr;
        for (auto dayNode : root->children) {
            if (dayNode->data["day_number"] == to_string(fromDay)) {
                for (auto act : dayNode->children) {
                    if (act->data["id"] == activityId) {
                        actData = act->data;
                        dayNode->removeChild(act);
                        delete act;
                        break;
                    }
                }
            }
        }
        if (!actData.empty()) return addActivity(toDay, actData);
        return nullptr;
    }


    string displayItinerary() {
        ItineraryNode* root = current();
        if (!root) return "No trip selected.\n";
        string r = "\n============================================================\n";
        r += "  Trip: " + root->data["name"] + "\n";
        r += "  Duration: " + root->data["start_date"] + " to " + root->data["end_date"] + "\n";
        r += "============================================================\n\n";
        for (auto dayNode : root->children) {
            r += "Day " + dayNode->data["day_number"] + " - " + dayNode->data["date"] + "\n";
            r += "  ----------------------------------------\n";
            if (dayNode->children.empty()) {
                r += "    No activities planned\n";
            } else {
                int cnt = 1;
                for (auto act : dayNode->children) {
                    r += "  " + to_string(cnt++) + ". " + act->data["name"] + "\n";
                    r += "     Duration: " + act->data["duration"] + " hrs | Cost: Rs." + act->data["cost"] + "\n";
                }
            }
            r += "\n";
        }
        return r;
    }

    vector<map<string,string>> getDaySchedule(int dayNumber) {
        vector<map<string,string>> acts;
        ItineraryNode* root = current();
        if (!root) return acts;
        for (auto dayNode : root->children) {
            if (dayNode->data["day_number"] == to_string(dayNumber)) {
                for (auto act : dayNode->children) acts.push_back(act->data);
                break;
            }
        }
        return acts;
    }

    int getDayCount() {
        ItineraryNode* root = current();
        if (!root) return 0;
        return (int)root->children.size();
    }

    double getTotalDuration() {
        ItineraryNode* root = current();
        if (!root) return 0;
        double t = 0;
        for (auto d : root->children)
            for (auto a : d->children) {
                auto it = a->data.find("duration");
                if (it != a->data.end() && !it->second.empty())
                    try { t += stod(it->second); } catch(...) {}
            }
        return t;
    }

    double getTotalCost() {
        ItineraryNode* root = current();
        if (!root) return 0;
        double t = 0;
        for (auto d : root->children)
            for (auto a : d->children) {
                auto it = a->data.find("cost");
                if (it != a->data.end() && !it->second.empty())
                    try { t += stod(it->second); } catch(...) {}
            }
        return t;
    }

    ~ItineraryTree() { for (auto t : trips) delete t; }
};

//  ACTIVITY MANAGER

struct Activity {
    string id, name, location, category;
    double cost, rating, duration;
};

class ActivityManager {
private:
    // PRIMARY STORE: city -> ordered list of activities (insertion order preserved)
    unordered_map<string, vector<Activity>> db;

    // OPTIMISATION 1: city -> (lowercase-name -> Activity*) for O(1) name lookup
    // Eliminates the O(n log n) re-sort + O(log n) binary search on every query.
    unordered_map<string, unordered_map<string, Activity*>> nameIndex;

    // OPTIMISATION 2: category cache (uppercase -> canonical name)
    // Eliminates the O(all activities) rebuild of a set<string> on every resolveCategory call.
    unordered_map<string, string> categoryIndex; // uppercase -> canonical

    // Call whenever the vector for a city is structurally changed (add/remove).
    void rebuildNameIndex(const string& city) {
        nameIndex[city].clear();
        for (auto& a : db[city])
            nameIndex[city][toLower(a.name)] = &a;
    }

    static string toLower(string s) {
        transform(s.begin(), s.end(), s.begin(), ::tolower);
        return s;
    }
    static string toUpper(string s) {
        transform(s.begin(), s.end(), s.begin(), ::toupper);
        return s;
    }

    vector<Activity> quickSort(vector<Activity> arr, const string& key, const string& order) {
        if (arr.size() <= 1) return arr;
        Activity pivot = arr[arr.size()/2];
        vector<Activity> left, mid, right;
        for (const Activity& a : arr) {
            double pv = (key=="cost") ? pivot.cost : (key=="rating") ? pivot.rating : pivot.duration;
            double av = (key=="cost") ? a.cost     : (key=="rating") ? a.rating     : a.duration;
            if (order=="asc")
                (av<pv?left:av==pv?mid:right).push_back(a);
            else
                (av>pv?left:av==pv?mid:right).push_back(a);
        }
        auto sl = quickSort(left,key,order), sr = quickSort(right,key,order);
        sl.insert(sl.end(), mid.begin(), mid.end());
        sl.insert(sl.end(), sr.begin(), sr.end());
        return sl;
    }

public:
    Activity addActivityToDB(const string& name, const string& location, const string& category,
                             double cost, double rating, double duration) {
        Activity a = { location+"_"+to_string(db[location].size()), name, location, category, cost, rating, duration };
        db[location].push_back(a);
        // OPTIMISATION 1: update name index in O(1) — no full rebuild needed on insert
        nameIndex[location][toLower(name)] = &db[location].back();
        // OPTIMISATION 2: register category in O(1)
        categoryIndex[toUpper(category)] = category;
        return a;
    }

    bool removeActivityFromDB(const string& location, const string& activityName) {
        if (db.find(location) == db.end()) return false;
        auto& v = db[location];
        auto it = remove_if(v.begin(), v.end(), [&](const Activity& a){ return a.name == activityName; });
        if (it == v.end()) return false;
        v.erase(it, v.end());
        // Rebuild index after removal (pointers into vector may have shifted)
        rebuildNameIndex(location);
        return true;
    }

    vector<Activity> getAllActivities(const string& city) { return db[city]; }

    string resolveCity(const string& input) const {
        string lo = input;
        transform(lo.begin(), lo.end(), lo.begin(), ::toupper);
        for (const auto& kv : db) {
            string ku = kv.first;
            transform(ku.begin(), ku.end(), ku.begin(), ::toupper);
            if (ku == lo) return kv.first;
        }
        return "";
    }

    // OPTIMISATION 2: O(1) lookup instead of O(all activities) set rebuild each call
    string resolveCategory(const string& input) const {
        string up = input;
        transform(up.begin(), up.end(), up.begin(), ::toupper);
        auto it = categoryIndex.find(up);
        return (it != categoryIndex.end()) ? it->second : "";
    }

    vector<Activity> getByCategory(const string& cat) {
        vector<Activity> res;
        for (auto& [c, acts] : db)
            for (auto& a : acts)
                if (a.category == cat) res.push_back(a);
        return res;
    }

    vector<Activity> sortByCost    (vector<Activity> v, const string& ord="asc")  { return quickSort(v,"cost",ord); }
    vector<Activity> sortByRating  (vector<Activity> v, const string& ord="desc") { return quickSort(v,"rating",ord); }
    vector<Activity> sortByDuration(vector<Activity> v, const string& ord="asc")  { return quickSort(v,"duration",ord); }

    // OPTIMISATION 1: O(1) hash lookup — no sort, no binary search
    Activity* binarySearchByName(vector<Activity>& /*acts*/, const string& name) {
        // 'acts' parameter kept for API compatibility but no longer used.
        // We search the city-wide name index instead.
        string lo = name;
        transform(lo.begin(), lo.end(), lo.begin(), ::tolower);
        for (auto& [city, idx] : nameIndex) {
            auto it = idx.find(lo);
            if (it != idx.end()) return it->second;
        }
        return nullptr;
    }

    // Overload: search within a specific city (preferred — avoids cross-city ambiguity)
    Activity* findByName(const string& city, const string& name) {
        string lo = name;
        transform(lo.begin(), lo.end(), lo.begin(), ::tolower);
        auto cityIt = nameIndex.find(city);
        if (cityIt == nameIndex.end()) return nullptr;
        auto it = cityIt->second.find(lo);
        return (it != cityIt->second.end()) ? it->second : nullptr;
    }

    vector<Activity> filterActivities(vector<Activity> acts, const map<string,double>& crit) {
        if (crit.count("max_cost"))
            acts.erase(remove_if(acts.begin(),acts.end(),[&](const Activity& a){return a.cost>crit.at("max_cost");}),acts.end());
        if (crit.count("min_rating"))
            acts.erase(remove_if(acts.begin(),acts.end(),[&](const Activity& a){return a.rating<crit.at("min_rating");}),acts.end());
        if (crit.count("max_duration"))
            acts.erase(remove_if(acts.begin(),acts.end(),[&](const Activity& a){return a.duration>crit.at("max_duration");}),acts.end());
        return acts;
    }

    vector<Activity> budgetOptimizer(const string& city, double maxBudget) {
        vector<Activity> acts = getAllActivities(city);
        if (acts.empty()) return {};

        int W = (int)(maxBudget * 10);
        int n = (int)acts.size();

        vector<vector<double>> dp(n+1, vector<double>(W+1, 0.0));

        for (int i = 1; i <= n; i++) {
            int wt = (int)(acts[i-1].cost * 10);
            double val = acts[i-1].rating;
            for (int w = 0; w <= W; w++) {
                dp[i][w] = dp[i-1][w];
                if (w >= wt)
                    dp[i][w] = max(dp[i][w], dp[i-1][w-wt] + val);
            }
        }

        vector<Activity> selected;
        int w = W;
        for (int i = n; i >= 1; i--) {
            if (dp[i][w] != dp[i-1][w]) {
                selected.push_back(acts[i-1]);
                w -= (int)(acts[i-1].cost * 10);
            }
        }
        reverse(selected.begin(), selected.end());
        return selected;
    }

private:
    void backtrackSchedule(const vector<Activity>& acts, int idx,
                           double timeLeft, double budgetLeft,
                           vector<Activity>& current, vector<Activity>& best,
                           double& bestRating) {
        double curRating = 0;
        for (auto& a : current) curRating += a.rating;

        if (curRating > bestRating) {
            bestRating = curRating;
            best = current;
        }

        if (idx >= (int)acts.size()) return;

        for (int i = idx; i < (int)acts.size(); i++) {
            if (acts[i].duration > timeLeft) continue;
            if (acts[i].cost > budgetLeft) continue;

            current.push_back(acts[i]);

            backtrackSchedule(acts, i+1,
                              timeLeft  - acts[i].duration,
                              budgetLeft - acts[i].cost,
                              current, best, bestRating);

            current.pop_back();
        }
    }

public:
    vector<Activity> optimalSchedule(const string& city, double maxHours, double maxBudget) {
        vector<Activity> acts = getAllActivities(city);
        if (acts.empty()) return {};

        vector<Activity> current, best;
        double bestRating = -1;
        backtrackSchedule(acts, 0, maxHours, maxBudget, current, best, bestRating);
        return best;
    }
};


//  MUSIC TRIE

struct Song {
    string name, artist;
    map<string,string> metadata;
};

class TrieNode {
public:
    unordered_map<char,TrieNode*> children;
    bool isEnd = false;
    Song* songData = nullptr;
    ~TrieNode() { for (auto& p : children) delete p.second; delete songData; }
};

class MusicTrie {
private:
    TrieNode* root;

    void collect(TrieNode* node, const string& prefix, vector<Song>& out) {
        if (!node) return;
        if (node->isEnd && node->songData) out.push_back(*node->songData);
        for (auto& p : node->children) collect(p.second, prefix+p.first, out);
    }

public:
    MusicTrie() { root = new TrieNode(); }
    ~MusicTrie() { delete root; }

    void insertSong(const string& name, const string& artist, const map<string,string>& meta={}) {
        TrieNode* node = root;
        string lo = name;
        transform(lo.begin(), lo.end(), lo.begin(), ::tolower);
        for (char c : lo) {
            if (!node->children.count(c)) node->children[c] = new TrieNode();
            node = node->children[c];
        }
        node->isEnd = true;
        delete node->songData;                          // FIX: free any previous song before overwriting
        node->songData = new Song{name, artist, meta};
    }

    vector<Song> searchPrefix(const string& prefix) {
        TrieNode* node = root;
        string lo = prefix;
        transform(lo.begin(), lo.end(), lo.begin(), ::tolower);
        for (char c : lo) {
            if (!node->children.count(c)) return {};
            node = node->children[c];
        }
        vector<Song> res;
        collect(node, prefix, res);
        return res;
    }

    vector<Song> autoComplete(const string& prefix, int limit) {
        auto all = searchPrefix(prefix);
        if ((int)all.size() <= limit) return all;
        return {all.begin(), all.begin()+limit};
    }

    bool deleteSong(const string& name) { return deleteHelper(root, name, 0); }

    bool deleteHelper(TrieNode* node, const string& name, int depth) {
        if (!node) return false;
        string lo = name; transform(lo.begin(),lo.end(),lo.begin(),::tolower);
        if (depth==(int)lo.size()) {
            if (!node->isEnd) return false;
            node->isEnd = false; delete node->songData; node->songData=nullptr;
            return node->children.empty();
        }
        char c = lo[depth];
        if (!node->children.count(c)) return false;
        bool del = deleteHelper(node->children[c], name, depth+1);
        if (del) { delete node->children[c]; node->children.erase(c); return !node->isEnd && node->children.empty(); }
        return false;
    }

    vector<Song> getAllSongs() { vector<Song> s; collect(root,"",s); return s; }

    vector<Song> searchByArtist(const string& artist) {
        vector<Song> all = getAllSongs(), res;
        string lo = artist;
        transform(lo.begin(), lo.end(), lo.begin(), ::tolower);
        for (auto& s : all) {
            string slo = s.artist;
            transform(slo.begin(), slo.end(), slo.begin(), ::tolower);
            if (slo == lo) res.push_back(s);
        }
        return res;
    }

private:
    vector<int> buildKMPTable(const string& pattern) {
        int m = (int)pattern.size();
        vector<int> lps(m, 0);
        int len = 0, i = 1;
        while (i < m) {
            if (pattern[i] == pattern[len]) {
                lps[i++] = ++len;
            } else {
                if (len != 0) len = lps[len-1];
                else lps[i++] = 0;
            }
        }
        return lps;
    }

    bool kmpSearch(const string& text, const string& pattern) {
        if (pattern.empty()) return true;
        string t = text, p = pattern;
        transform(t.begin(), t.end(), t.begin(), ::tolower);
        transform(p.begin(), p.end(), p.begin(), ::tolower);

        int n = (int)t.size(), m = (int)p.size();
        vector<int> lps = buildKMPTable(p);

        int i = 0, j = 0;
        while (i < n) {
            if (t[i] == p[j]) { i++; j++; }
            if (j == m) return true;
            else if (i < n && t[i] != p[j]) {
                if (j != 0) j = lps[j-1];
                else i++;
            }
        }
        return false;
    }

public:
    vector<Song> kmpFullTextSearch(const string& query) {
        vector<Song> all = getAllSongs(), res;
        for (auto& s : all)
            if (kmpSearch(s.name, query) || kmpSearch(s.artist, query))
                res.push_back(s);
        return res;
    }
};



class FrequencyTracker {
private:
    unordered_map<string,int> playCount;
    unordered_map<string,Song> meta;
public:
    void incrementPlayCount(const string& id) { playCount[id]++; }
    int  getPlayCount(const string& id)        { return playCount[id]; }

    vector<pair<string,int>> getMostPlayed(int k) {
        vector<pair<string,int>> v(playCount.begin(), playCount.end());
        sort(v.begin(), v.end(), [](auto& a, auto& b){ return a.second > b.second; });
        if ((int)v.size()<=k) return v;
        return {v.begin(), v.begin()+k};
    }

    void resetFrequencies()                          { playCount.clear(); }
    void addSongMetadata(const string& id, const Song& s) { meta[id]=s; playCount.emplace(id,0); }
    Song getSongMetadata(const string& id)           { return meta[id]; }
};


struct SongWithPriority {
    Song song; double priority;
    bool operator<(const SongWithPriority& o) const { return priority < o.priority; }
};

class PlaylistHeap {
private:
    priority_queue<SongWithPriority> heap;
    vector<Song> current;
public:
    void buildMaxHeap(const vector<Song>& songs, const string& criteria="rating") {
        while (!heap.empty()) heap.pop();
        for (auto& s : songs) {
            double p = (s.metadata.count(criteria)) ? stod(s.metadata.at(criteria)) : 1.0;
            heap.push({s, p});
        }
    }

    vector<Song> extractTopK(int k) {
        vector<Song> top;
        auto tmp = heap;
        for (int i=0; i<k && !tmp.empty(); i++) { top.push_back(tmp.top().song); tmp.pop(); }
        return top;
    }

    void insertSong(const Song& s, double p) { heap.push({s,p}); }

    vector<Song> generatePlaylist(int dur, const string& mood, const string& genre) {
        current = extractTopK(max(1, dur/4)); // FIX: ~4 min/song is more realistic than /3
        (void)mood; (void)genre;
        return current;
    }

    vector<Song> getCurrentPlaylist() { return current; }

    void addToPlaylist(const Song& s) { current.push_back(s); }

    bool removeFromPlaylist(const string& name) {
        for (auto it=current.begin(); it!=current.end(); ++it)
            if (it->name==name) { current.erase(it); return true; }
        return false;
    }

    vector<Song> shufflePlaylist() {
        vector<Song> s = current;
        shuffle(s.begin(), s.end(), default_random_engine(time(nullptr)));
        return s;
    }
};



void printPath(const vector<string>& path) {
    for (size_t i=0; i<path.size(); i++) {
        cout << path[i];
        if (i<path.size()-1) cout << " -> ";
    }
    cout << "\n";
}

int safeReadInt() {
    int val;
    while (true) {
        cin >> val;
        if (cin.good()) {
            cin.ignore(numeric_limits<streamsize>::max(), '\n'); // FIX: flush trailing newline
            return val;
        }
        cin.clear();
        cin.ignore(numeric_limits<streamsize>::max(), '\n');
        cout << "  [X] Invalid input. Please enter a number: ";
    }
}

void adminPanel(Graph& graph, ActivityManager& actMgr) {
    cout << "\n--------------------------------------\n";
    cout << "         ADMIN CONTROL PANEL          \n";
    cout << "--------------------------------------\n";

    if (!authenticateAdmin()) return;

    int choice;
    do {
        cout << "\n--- Admin Menu ---\n";
        cout << "1. Add City\n";
        cout << "2. Remove City\n";
        cout << "3. Add Route Between Cities\n";
        cout << "4. Remove Route Between Cities\n";
        cout << "5. Add Activity to a City\n";
        cout << "6. Remove Activity from a City\n";
        cout << "0. Back to Main Menu\n";
        cout << "Choice: ";
        choice = safeReadInt();

        if (choice == 1) {
            string city;
            cout << "Enter city name: ";
            cin.ignore(numeric_limits<streamsize>::max(), '\n'); getline(cin, city);
            if (graph.addCity(city))
                cout << "  [OK] City '" << city << "' added.\n";
            else
                cout << "  [X] City already exists.\n";
        }
        else if (choice == 2) {
            string city;
            cout << "Enter city name to remove: ";
            cin.ignore(numeric_limits<streamsize>::max(), '\n'); getline(cin, city);
            if (graph.removeCity(city))
                cout << "  [OK] City '" << city << "' removed.\n";
            else
                cout << "  [X] City not found.\n";
        }
        else if (choice == 3) {
            string c1, c2; double dist, cost, time;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "First city: ";  getline(cin,c1);
            cout << "Second city: "; getline(cin,c2);
            cout << "Distance (km): "; cin >> dist;
            cout << "Cost (Rs.): ";      cin >> cost;
            cout << "Time (hrs): ";    cin >> time;
            graph.addRoute(c1, c2, dist, cost, time);
            cout << "  [OK] Route added.\n";
        }
        else if (choice == 4) {
            string c1, c2;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "First city: ";  getline(cin,c1);
            cout << "Second city: "; getline(cin,c2);
            graph.removeRoute(c1, c2);
            cout << "  [OK] Route removed.\n";
        }
        else if (choice == 5) {
            string name, loc, cat; double cost, rating, dur;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "Activity name: "; getline(cin,name);
            cout << "City/Location: "; getline(cin,loc);
            cout << "Category: ";      getline(cin,cat);
            cout << "Cost (Rs.): ";      cin >> cost;
            cout << "Rating (0-5): ";  cin >> rating;
            cout << "Duration (hrs): ";cin >> dur;
            actMgr.addActivityToDB(name, loc, cat, cost, rating, dur);
            cout << "  [OK] Activity '" << name << "' added to " << loc << ".\n";
        }
        else if (choice == 6) {
            string loc, name;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "City/Location: ";      getline(cin,loc);
            cout << "Activity name: ";      getline(cin,name);
            if (actMgr.removeActivityFromDB(loc, name))
                cout << "  [OK] Activity removed.\n";
            else
                cout << "  [X] Activity not found.\n";
        }
    } while (choice != 0);
}

//  USER MENUS

void routePlanningMenu(Graph& graph) {
    auto resolveCity = [&](const string& input) -> string {
        auto cities = graph.getAllCities();
        string lo = input;
        transform(lo.begin(), lo.end(), lo.begin(), ::toupper);
        for (const auto& c : cities) {
            string cu = c;
            transform(cu.begin(), cu.end(), cu.begin(), ::toupper);
            if (cu == lo) return c;
        }
        return "";
    };

    int choice;
    do {
        cout << "\n--- ROUTE PLANNING ---\n";
        cout << "1. View All Cities\n";
        cout << "2. Find Shortest Path (by Distance)\n";
        cout << "3. Find Cheapest Path (by Cost)\n";
        cout << "4. Find Fastest Path (by Time)\n";
        cout << "5. Find Path with Stops\n";
        cout << "6. Get Alternative Paths\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        choice = safeReadInt();

        if (choice == 1) {
            auto cities = graph.getAllCities();
            cout << "\n--- Available Cities ---\n";
            for (size_t i=0; i<cities.size(); i++)
                cout << "  " << (i+1) << ". " << cities[i] << "\n";
        }
        else if (choice == 2 || choice == 3 || choice == 4) {
            string srcIn, dstIn;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "Source city: ";      getline(cin,srcIn);
            cout << "Destination city: "; getline(cin,dstIn);
            string src = resolveCity(srcIn);
            string dst = resolveCity(dstIn);
            if (src.empty()) { cout << "  [X] City not found: " << srcIn << "\n"; continue; }
            if (dst.empty()) { cout << "  [X] City not found: " << dstIn << "\n"; continue; }
            if (choice==2) {
                auto r = graph.findShortestPath(src,dst);
                if (r.path.empty()) { cout << "  [X] No path found between " << src << " and " << dst << ".\n"; }
                else { cout << "\n  Path: "; printPath(r.path); cout << "  Total Distance: " << r.totalWeight << " km\n"; }
            } else if (choice==3) {
                auto r = graph.findCheapestPath(src,dst);
                if (r.path.empty()) { cout << "  [X] No path found between " << src << " and " << dst << ".\n"; }
                else { cout << "\n  Path: "; printPath(r.path); cout << "  Total Cost: Rs." << r.totalWeight << "\n"; }
            } else {
                auto r = graph.findFastestPath(src,dst);
                if (r.path.empty()) { cout << "  [X] No path found between " << src << " and " << dst << ".\n"; }
                else { cout << "\n  Path: "; printPath(r.path); cout << "  Total Time: " << r.totalWeight << " hours\n"; }
            }
        }
        else if (choice == 5) {
            string srcIn, dstIn; int n;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "Source: ";      getline(cin,srcIn);
            cout << "Destination: "; getline(cin,dstIn);
            string src = resolveCity(srcIn);
            string dst = resolveCity(dstIn);
            if (src.empty()) { cout << "  [X] City not found: " << srcIn << "\n"; continue; }
            if (dst.empty()) { cout << "  [X] City not found: " << dstIn << "\n"; continue; }
            cout << "Number of stops: "; cin >> n;
            vector<string> stops; cin.ignore(numeric_limits<streamsize>::max(), '\n');
            for (int i=0; i<n; i++) {
                string s; cout << "Stop " << (i+1) << ": "; getline(cin,s);
                string rs = resolveCity(s);
                if (rs.empty()) { cout << "  [X] Stop city not found: " << s << "\n"; rs = s; }
                stops.push_back(rs);
            }
            auto r = graph.findPathWithStops(src,dst,stops);
            if (r.path.empty()) { cout << "  [X] No complete path found.\n"; }
            else { cout << "\n  Path: "; printPath(r.path); cout << "  Total Distance: " << r.totalWeight << " km\n"; }
        }
        else if (choice == 6) {
            string srcIn, dstIn;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "Source: ";      getline(cin,srcIn);
            cout << "Destination: "; getline(cin,dstIn);
            string src = resolveCity(srcIn);
            string dst = resolveCity(dstIn);
            if (src.empty()) { cout << "  [X] City not found: " << srcIn << "\n"; continue; }
            if (dst.empty()) { cout << "  [X] City not found: " << dstIn << "\n"; continue; }
            auto paths = graph.getAlternativePaths(src,dst,3);
            if (paths.empty() || paths[0].path.empty()) { cout << "  [X] No path found.\n"; }
            else {
                cout << "\n--- Alternative Paths ---\n";
                for (size_t i=0; i<paths.size(); i++) {
                    cout << "  Path " << (i+1) << ": ";
                    printPath(paths[i].path);
                    cout << "    Distance: " << paths[i].totalWeight << " km\n";
                }
            }
        }
    } while (choice != 0);
}

static bool selectTripPrompt(ItineraryTree& itinerary) {
    auto names = itinerary.listTrips();
    if (names.empty()) {
        cout << "  No trips yet. Create one first (option 1).\n";
        return false;
    }
    cout << "\n--- Your Trips ---\n";
    for (size_t i = 0; i < names.size(); i++)
        cout << "  " << (i+1) << ". " << names[i] << "\n";
    int active = itinerary.getActiveTrip() + 1;
    cout << "  Currently selected: Trip " << active << "\n";
    cout << "Switch to trip number (0 to keep current): ";
    int pick = safeReadInt();
    if (pick == 0) return true;
    string err = itinerary.selectTrip(pick);
    if (!err.empty()) { cout << "  [X] " << err << "\n"; return false; }
    cout << "  [OK] Switched to Trip " << pick << ": " << itinerary.listTrips()[pick-1] << "\n";
    return true;
}

void itineraryMenu(ItineraryTree& itinerary, ActivityManager& actMgr) {
    int choice;
    do {
        auto names = itinerary.listTrips();
        cout << "\n--- ITINERARY PLANNING ---\n";
        if (names.empty())
            cout << "  No trips created yet.\n";
        else
            cout << "  Active trip: [" << (itinerary.getActiveTrip()+1) << "] "
                 << names[itinerary.getActiveTrip()] << "\n";
        cout << "  (Note: All dates must be in the future - after " << getTodayString() << ")\n";
        cout << "1. Create New Trip\n";
        cout << "2. Switch Active Trip\n";
        cout << "3. Delete a Trip\n";
        cout << "4. Add Activity to a Day\n";
        cout << "5. Remove Activity\n";
        cout << "6. Move Activity to Another Day\n";
        cout << "7. Display Full Itinerary\n";
        cout << "8. View a Day's Schedule\n";
        cout << "9. View Total Cost & Duration\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        choice = safeReadInt();

        if (choice == 1) {
            string name;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "Trip name: "; getline(cin, name); stripLine(name);
            string start = promptFutureDate("Start date");
            string end   = promptDateOnOrAfter("End date  ", start);
            string err = itinerary.createItinerary(name, start, end);
            if (err.empty()) {
                cout << "  [OK] Trip '" << name << "' created! "
                     << itinerary.getDayCount() << " day(s) auto-generated.\n";
                cout << "  Tip: Use option 4 to add activities to each day.\n";
            } else {
                cout << "  [X] " << err << "\n";
            }
        }
        else if (choice == 2) {
            selectTripPrompt(itinerary);
        }
        else if (choice == 3) {
            auto tnames = itinerary.listTrips();
            if (tnames.empty()) { cout << "  No trips to delete.\n"; }
            else {
                cout << "\n--- Your Trips ---\n";
                for (size_t i = 0; i < tnames.size(); i++)
                    cout << "  " << (i+1) << ". " << tnames[i] << "\n";
                cout << "Delete trip number (0 to cancel): ";
                int pick = safeReadInt();
                if (pick != 0) {
                    string err = itinerary.deleteTrip(pick);
                    if (err.empty()) cout << "  [OK] Trip deleted.\n";
                    else             cout << "  [X] " << err << "\n";
                }
            }
        }
        else if (choice == 4) {
            if (itinerary.getTripCount() == 0) { cout << "  No trips yet. Create one first.\n"; }
            else {
                if (itinerary.getTripCount() > 1) {
                    cout << "\n  You have " << itinerary.getTripCount() << " trips. Which trip do you want to add activities to?\n";
                    if (!selectTripPrompt(itinerary)) continue;
                }
                int day;
                cout << "Day number: "; day = safeReadInt();
                cin.ignore(numeric_limits<streamsize>::max(), '\n');
                string cityIn;
                cout << "City for activities: "; getline(cin, cityIn); stripLine(cityIn);
                string city = actMgr.resolveCity(cityIn);
                if (city.empty()) {
                    cout << "  [X] City not found: " << cityIn << "\n";
                } else {
                    auto acts = actMgr.getAllActivities(city);
                    if (acts.empty()) {
                        cout << "  No activities found for " << city << ".\n";
                    } else {
                        cout << "\n--- Activities in " << city << " ---\n";
                        for (size_t i = 0; i < acts.size(); i++)
                            cout << "  " << (i+1) << ". " << acts[i].name
                                 << " | Rs." << acts[i].cost
                                 << " | *" << acts[i].rating
                                 << " | " << acts[i].duration << " hrs\n";
                        cout << "Pick activity number (0 to cancel): ";
                        int pick = safeReadInt();
                        if (pick >= 1 && pick <= (int)acts.size()) {
                            const Activity& sel = acts[pick-1];
                            map<string,string> act = {
                                {"id",       "act_" + to_string(rand()%10000)},
                                {"name",     sel.name},
                                {"duration", to_string(sel.duration)},
                                {"cost",     to_string(sel.cost)}
                            };
                            if (itinerary.addActivity(day, act))
                                cout << "  [OK] '" << sel.name << "' added to Day " << day << "!\n";
                            else
                                cout << "  [X] Day " << day << " not found in this trip.\n";
                        } else if (pick != 0) {
                            cout << "  [X] Invalid selection.\n";
                        }
                    }
                }
            }
        }
        else if (choice == 5) {
            if (itinerary.getTripCount() == 0) { cout << "  No trips yet. Create one first.\n"; continue; }
            if (itinerary.getTripCount() > 1) selectTripPrompt(itinerary);
            int day; string id;
            cout << "Day number: "; day = safeReadInt();
            cout << "Activity ID: "; getline(cin, id); stripLine(id); // FIX: use getline for IDs
            if (itinerary.removeActivity(day,id)) cout << "  [OK] Removed.\n";
            else                                  cout << "  [X] Not found.\n";
        }
        else if (choice == 6) {
            if (itinerary.getTripCount() == 0) { cout << "  No trips yet. Create one first.\n"; continue; }
            if (itinerary.getTripCount() > 1) selectTripPrompt(itinerary);
            int from, to; string id;
            cout << "From day: "; from = safeReadInt();
            cout << "To day: ";   to   = safeReadInt();
            cout << "Activity ID: "; getline(cin, id); stripLine(id); // FIX: use getline
            if (itinerary.moveActivity(from,to,id)) cout << "  [OK] Moved.\n";
            else                                    cout << "  [X] Failed.\n";
        }
        else if (choice == 7) {
            if (itinerary.getTripCount() == 0) { cout << "  No trips yet. Create one first.\n"; continue; }
            if (itinerary.getTripCount() > 1) selectTripPrompt(itinerary);
            cout << itinerary.displayItinerary();
        }
        else if (choice == 8) {
            if (itinerary.getTripCount() == 0) { cout << "  No trips yet. Create one first.\n"; continue; }
            if (itinerary.getTripCount() > 1) selectTripPrompt(itinerary);
            int day; cout << "Day number: "; day = safeReadInt();
            auto sched = itinerary.getDaySchedule(day);
            cout << "\n--- Day " << day << " Schedule ---\n";
            if (sched.empty())
                cout << "  No activities planned for this day.\n";
            else
                for (size_t i = 0; i < sched.size(); i++)
                    cout << "  " << (i+1) << ". " << sched[i]["name"]
                         << " (" << sched[i]["duration"] << " hrs, Rs." << sched[i]["cost"] << ")\n";
        }
        else if (choice == 9) {
            if (itinerary.getTripCount() == 0) { cout << "  No trips yet. Create one first.\n"; continue; }
            if (itinerary.getTripCount() > 1) selectTripPrompt(itinerary);
            cout << "\n--- Trip Summary ---\n";
            cout << "  Total Duration : " << itinerary.getTotalDuration() << " hrs\n";
            cout << "  Total Cost     : Rs." << itinerary.getTotalCost()    << "\n";
        }
    } while (choice != 0);
}

void activityMenu(ActivityManager& actMgr) {
    int choice;
    do {
        cout << "\n--- ACTIVITY EXPLORER ---\n";
        cout << "1. View All Activities in a City\n";
        cout << "2. Sort by Cost\n";
        cout << "3. Sort by Rating\n";
        cout << "4. Sort by Duration\n";
        cout << "5. Filter Activities\n";
        cout << "6. Search Activity by Name\n";
        cout << "7. Browse by Category\n";
        cout << "8. Budget Optimizer (Best activities within budget)\n";
        cout << "9. Optimal Activity Scheduler (Best combo for time + budget)\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        choice = safeReadInt();

        auto printActs = [](const vector<Activity>& acts) {
            if (acts.empty()) { cout << "  No activities found.\n"; return; }
            for (size_t i=0; i<acts.size(); i++)
                cout << "  " << (i+1) << ". " << acts[i].name
                     << " | Rs." << acts[i].cost
                     << " | *" << acts[i].rating
                     << " | " << acts[i].duration << " hrs"
                     << " | " << acts[i].category << "\n";
        };

        auto getCity = [&]() -> string {
            string cityIn; cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "City: "; getline(cin, cityIn); stripLine(cityIn);
            string city = actMgr.resolveCity(cityIn);
            if (city.empty()) cout << "  [X] City not found: " << cityIn << "\n";
            return city;
        };

        if (choice == 1) {
            string city = getCity();
            if (!city.empty()) printActs(actMgr.getAllActivities(city));
        }
        else if (choice == 2) {
            string city = getCity();
            if (!city.empty()) {
                string ord; cout << "Order (asc/desc): "; cin >> ord; stripLine(ord);
                printActs(actMgr.sortByCost(actMgr.getAllActivities(city), ord));
            }
        }
        else if (choice == 3) {
            string city = getCity();
            if (!city.empty()) printActs(actMgr.sortByRating(actMgr.getAllActivities(city)));
        }
        else if (choice == 4) {
            string city = getCity();
            if (!city.empty()) {
                string ord; cout << "Order (asc/desc): "; cin >> ord; stripLine(ord);
                printActs(actMgr.sortByDuration(actMgr.getAllActivities(city), ord));
            }
        }
        else if (choice == 5) {
            string city = getCity();
            if (!city.empty()) {
                double mc, mr, md;
                cout << "Max cost (Rs.): ";     cin >> mc;
                cout << "Min rating (0-5): ";   cin >> mr;
                cout << "Max duration (hrs): "; cin >> md;
                map<string,double> crit = {{"max_cost",mc},{"min_rating",mr},{"max_duration",md}};
                printActs(actMgr.filterActivities(actMgr.getAllActivities(city), crit));
            }
        }
        else if (choice == 6) {
            string city = getCity();
            if (!city.empty()) {
                string name; cout << "Activity name: "; getline(cin, name); stripLine(name);
                // OPTIMISATION: O(1) hash lookup via nameIndex (no sort, no copy)
                Activity* found = actMgr.findByName(city, name);
                if (found)
                    cout << "  Found: " << found->name << " | Rs." << found->cost
                         << " | *" << found->rating << " | " << found->duration << " hrs\n";
                else
                    cout << "  [X] Activity not found.\n";
            }
        }
        else if (choice == 7) {
            string catIn; cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "Category: "; getline(cin, catIn); stripLine(catIn);
            string cat = actMgr.resolveCategory(catIn);
            if (cat.empty()) cout << "  [X] Category not found: " << catIn << "\n";
            else printActs(actMgr.getByCategory(cat));
        }
        else if (choice == 8) {
            string city = getCity();
            if (!city.empty()) {
                double budget; cout << "  Max Budget (Rs.): "; cin >> budget;
                auto result = actMgr.budgetOptimizer(city, budget);
                cout << "\n--- Budget Optimizer Results (0/1 Knapsack DP) ---\n";
                cout << "  Best activities within Rs." << budget << " to maximise ratings:\n\n";
                if (result.empty()) { cout << "  No activities found within this budget.\n"; }
                else {
                    double totalCost = 0, totalRating = 0;
                    printActs(result);
                    for (auto& a : result) { totalCost += a.cost; totalRating += a.rating; }
                    cout << "\n  Total Cost   : Rs." << totalCost << "\n";
                    cout << "  Total Rating : " << totalRating << "\n";
                }
            }
        }
        else if (choice == 9) {
            string city = getCity();
            if (!city.empty()) {
                double maxHours, maxBudget;
                cout << "  Max Time Available (hrs): "; cin >> maxHours;
                cout << "  Max Budget (Rs.): ";         cin >> maxBudget;
                cout << "\n  [Backtracking in progress...]\n";
                auto result = actMgr.optimalSchedule(city, maxHours, maxBudget);
                cout << "\n--- Optimal Activity Schedule (Backtracking) ---\n";
                cout << "  Best combination within " << maxHours << " hrs & Rs." << maxBudget << ":\n\n";
                if (result.empty()) { cout << "  No valid combination found within these constraints.\n"; }
                else {
                    double totalCost = 0, totalDur = 0, totalRating = 0;
                    printActs(result);
                    for (auto& a : result) { totalCost += a.cost; totalDur += a.duration; totalRating += a.rating; }
                    cout << "\n  Total Duration : " << totalDur    << " hrs\n";
                    cout << "  Total Cost     : Rs." << totalCost  << "\n";
                    cout << "  Total Rating   : " << totalRating   << "\n";
                }
            }
        }
    } while (choice != 0);
}

void musicLibraryMenu(MusicTrie& trie) {
    int choice;
    do {
        cout << "\n--- MUSIC LIBRARY ---\n";
        cout << "1. Search Songs by Prefix\n";
        cout << "2. Autocomplete Song Name\n";
        cout << "3. Search Songs by Artist\n";
        cout << "4. View All Songs\n";
        cout << "5. Full-Text Song Search\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        choice = safeReadInt();

        auto printSongs = [](const vector<Song>& songs) {
            if (songs.empty()) { cout << "  No songs found.\n"; return; }
            for (size_t i=0; i<songs.size(); i++)
                cout << "  " << (i+1) << ". " << songs[i].name
                     << " - " << songs[i].artist
                     << " | " << (songs[i].metadata.count("mood") ? songs[i].metadata.at("mood") : "")
                     << " | *" << (songs[i].metadata.count("rating") ? songs[i].metadata.at("rating") : "?")
                     << "\n";
        };

        if (choice == 1) {
            string pf; cin.ignore(numeric_limits<streamsize>::max(), '\n'); cout << "Enter prefix: "; getline(cin,pf);
            printSongs(trie.searchPrefix(pf));
        }
        else if (choice == 2) {
            string pf; int lim;
            cin.ignore(numeric_limits<streamsize>::max(), '\n'); cout << "Enter prefix: "; getline(cin,pf);
            cout << "Max suggestions: "; cin >> lim;
            printSongs(trie.autoComplete(pf,lim));
        }
        else if (choice == 3) {
            string artist; cin.ignore(numeric_limits<streamsize>::max(), '\n'); cout << "Artist name: "; getline(cin,artist);
            printSongs(trie.searchByArtist(artist));
        }
        else if (choice == 4) {
            printSongs(trie.getAllSongs());
        }
        else if (choice == 5) {
            string query;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "  Enter search keyword (searches song name & artist): ";
            getline(cin, query);

            auto results = trie.kmpFullTextSearch(query);

            cout << "\n--- Full-Text Search Results for \"" << query << "\" ---\n";
            cout << "  (Matches any part of song name or artist name)\n\n";
            printSongs(results);
            cout << "  Total matches: " << results.size() << "\n";
        }
    } while (choice != 0);
}

void frequencyMenu(FrequencyTracker& tracker, MusicTrie& trie) {
    int choice;
    do {
        cout << "\n--- SONG FREQUENCY TRACKER ---\n";
        cout << "1. Play a Song (Increment Count)\n";
        cout << "2. View Play Count for a Song\n";
        cout << "3. View Most Played Songs\n";
        cout << "4. Reset All Play Counts\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        choice = safeReadInt();

        if (choice == 1) {
            string id; cin.ignore(numeric_limits<streamsize>::max(), '\n'); cout << "Song name: "; getline(cin,id); stripLine(id);
            // Verify the song exists in the library
            auto allSongs = trie.getAllSongs();
            bool found = false;
            for (auto& s : allSongs) {
                if (s.name == id) {
                    tracker.incrementPlayCount(id);
                    cout << "  [OK] Now playing: '" << s.name << "' by " << s.artist << "\n";
                    cout << "  Play count: " << tracker.getPlayCount(id) << "\n";
                    found = true; break;
                }
            }
            if (!found) {
                tracker.incrementPlayCount(id);
                cout << "  [OK] Play count incremented for '" << id << "'.\n";
                cout << "  (Note: Song not found in library - check spelling)\n";
            }
        }
        else if (choice == 2) {
            string id; cin.ignore(numeric_limits<streamsize>::max(), '\n'); cout << "Song name: "; getline(cin,id); stripLine(id);
            cout << "  Play count for '" << id << "': " << tracker.getPlayCount(id) << "\n";
        }
        else if (choice == 3) {
            int k; cout << "Top N songs: "; cin >> k;
            auto top = tracker.getMostPlayed(k);
            cout << "\n--- Top " << k << " Most Played Songs ---\n";
            if (top.empty()) { cout << "  No songs played yet.\n"; }
            else {
                for (size_t i=0; i<top.size(); i++)
                    cout << "  " << (i+1) << ". " << top[i].first
                         << "  (" << top[i].second << " plays)\n";
            }
        }
        else if (choice == 4) {
            tracker.resetFrequencies();
            cout << "  [OK] All play counts reset.\n";
        }
    } while (choice != 0);
}

void playlistMenu(PlaylistHeap& heap, MusicTrie& trie) {
    int choice;
    do {
        cout << "\n--- PLAYLIST GENERATOR ---\n";
        cout << "1. Generate Playlist from Library\n";
        cout << "2. View Current Playlist\n";
        cout << "3. Add Song to Playlist\n";
        cout << "4. Remove Song from Playlist\n";
        cout << "5. Shuffle Playlist\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        choice = safeReadInt();

        auto printSongs = [](const vector<Song>& songs) {
            if (songs.empty()) { cout << "  Playlist is empty.\n"; return; }
            for (size_t i=0; i<songs.size(); i++)
                cout << "  " << (i+1) << ". " << songs[i].name << " - " << songs[i].artist << "\n";
        };

        if (choice == 1) {
            int dur; string mood, genre;
            cout << "Trip duration (minutes): "; cin >> dur;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "Mood (Happy/Romantic/Emotional/Party): "; getline(cin,mood);
            stripLine(mood);
            cout << "Available Genres: Bollywood, Punjabi, Sufi, Indie, Tamil, Telugu, Malayalam\n";
            cout << "Genre preference (or press Enter for any): "; getline(cin,genre);
            stripLine(genre);

            // Filter songs by mood and genre BEFORE building the heap
            auto allSongs = trie.getAllSongs();
            vector<Song> filtered;
            for (auto& s : allSongs) {
                bool moodMatch = mood.empty() ||
                    (s.metadata.count("mood") && s.metadata.at("mood") == mood);
                bool genreMatch = genre.empty() ||
                    (s.metadata.count("genre") && s.metadata.at("genre") == genre);
                if (moodMatch && genreMatch) filtered.push_back(s);
            }
            if (filtered.empty()) {
                cout << "  [X] No songs found for mood='" << mood
                     << "' genre='" << genre << "'. Try different filters.\n";
            } else {
                heap.buildMaxHeap(filtered, "rating");
                auto pl = heap.generatePlaylist(dur, mood, genre);
                cout << "\n  [OK] Playlist Generated (" << pl.size() << " songs):\n";
                printSongs(pl);
            }
        }
        else if (choice == 2) {
            printSongs(heap.getCurrentPlaylist());
        }
        else if (choice == 3) {
            string name;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            cout << "Song name: "; getline(cin,name); stripLine(name);
            // Try to find the song in the library to preserve metadata
            auto allSongs = trie.getAllSongs();
            bool found = false;
            for (auto& s : allSongs) {
                if (s.name == name) {
                    double p = s.metadata.count("rating") ? stod(s.metadata.at("rating")) : 1.0;
                    heap.insertSong(s, p);
                    heap.addToPlaylist(s);
                    cout << "  [OK] Added '" << s.name << "' by " << s.artist << " to playlist.\n";
                    found = true; break;
                }
            }
            if (!found) {
                string artist;
                cout << "Song not found in library. Enter artist name: "; getline(cin,artist); stripLine(artist);
                heap.addToPlaylist({name, artist, {}});
                cout << "  [OK] Added.\n";
            }
        }
        else if (choice == 4) {
            string name; cin.ignore(numeric_limits<streamsize>::max(), '\n'); cout << "Song name: "; getline(cin,name);
            if (heap.removeFromPlaylist(name)) cout << "  [OK] Removed.\n";
            else                               cout << "  [X] Not found.\n";
        }
        else if (choice == 5) {
            printSongs(heap.shufflePlaylist());
        }
    } while (choice != 0);
}

void loadSampleData(Graph& graph, ActivityManager& actMgr, MusicTrie& trie) {

    vector<string> cities = {
        "Delhi","Agra","Jaipur","Varanasi","Lucknow",
        "Amritsar","Chandigarh","Shimla","Manali","Rishikesh",
        "Haridwar","Dehradun","Mathura","Vrindavan","Udaipur",
        "Mumbai","Pune","Goa","Ahmedabad","Surat",
        "Vadodara","Nashik","Aurangabad","Shirdi","Solapur",
        "Bangalore","Chennai","Hyderabad","Kochi","Mysore",
        "Coimbatore","Madurai","Thiruvananthapuram","Pondicherry","Ooty",
        "Mangalore","Vizag","Tirupati","Hampi","Warangal",
        "Kolkata","Bhubaneswar","Puri","Patna","Guwahati",
        "Shillong","Darjeeling","Siliguri","Ranchi","Raipur",
        "Bhopal","Indore","Jabalpur","Gwalior","Ujjain"
    };
    for (auto& c : cities) graph.addCity(c);

    graph.addRoute("Delhi","Agra",200,350,3.0);
    graph.addRoute("Delhi","Jaipur",280,450,5.0);
    graph.addRoute("Delhi","Lucknow",550,700,7.5);
    graph.addRoute("Delhi","Varanasi",820,900,11.0);
    graph.addRoute("Delhi","Amritsar",450,650,7.0);
    graph.addRoute("Delhi","Chandigarh",250,400,4.5);
    graph.addRoute("Delhi","Dehradun",300,450,5.5);
    graph.addRoute("Delhi","Mathura",145,250,2.5);
    graph.addRoute("Delhi","Rishikesh",240,400,5.0);
    graph.addRoute("Delhi","Haridwar",220,370,4.5);
    graph.addRoute("Agra","Jaipur",240,380,4.0);
    graph.addRoute("Agra","Lucknow",330,500,5.0);
    graph.addRoute("Agra","Mathura",58,120,1.0);
    graph.addRoute("Mathura","Vrindavan",12,50,0.5);
    graph.addRoute("Jaipur","Udaipur",395,600,6.5);
    graph.addRoute("Jaipur","Ahmedabad",650,850,9.0);
    graph.addRoute("Lucknow","Varanasi",300,450,4.5);
    graph.addRoute("Lucknow","Patna",400,600,6.0);
    graph.addRoute("Varanasi","Patna",250,400,4.0);
    graph.addRoute("Varanasi","Kolkata",650,800,9.0);
    graph.addRoute("Chandigarh","Amritsar",200,320,3.5);
    graph.addRoute("Chandigarh","Shimla",115,250,3.0);
    graph.addRoute("Shimla","Manali",250,450,7.0);
    graph.addRoute("Rishikesh","Haridwar",24,80,0.5);
    graph.addRoute("Rishikesh","Dehradun",43,120,1.0);
    graph.addRoute("Udaipur","Ahmedabad",260,420,4.5);
    graph.addRoute("Mumbai","Pune",150,300,3.0);
    graph.addRoute("Mumbai","Goa",600,800,9.0);
    graph.addRoute("Mumbai","Ahmedabad",530,700,8.0);
    graph.addRoute("Mumbai","Nashik",165,320,3.5);
    graph.addRoute("Mumbai","Aurangabad",335,550,6.0);
    graph.addRoute("Mumbai","Hyderabad",710,900,11.0);
    graph.addRoute("Mumbai","Surat",280,450,5.0);
    graph.addRoute("Pune","Goa",450,650,7.0);
    graph.addRoute("Pune","Hyderabad",560,750,8.5);
    graph.addRoute("Pune","Solapur",250,400,4.5);
    graph.addRoute("Pune","Nashik",210,350,4.0);
    graph.addRoute("Ahmedabad","Surat",260,400,4.0);
    graph.addRoute("Ahmedabad","Vadodara",110,220,2.0);
    graph.addRoute("Ahmedabad","Bhopal",490,700,8.0);
    graph.addRoute("Nashik","Shirdi",90,180,2.0);
    graph.addRoute("Aurangabad","Shirdi",125,250,3.0);
    graph.addRoute("Solapur","Hyderabad",320,500,5.5);
    graph.addRoute("Bangalore","Chennai",350,500,6.0);
    graph.addRoute("Bangalore","Hyderabad",570,750,9.0);
    graph.addRoute("Bangalore","Mysore",145,250,3.0);
    graph.addRoute("Bangalore","Kochi",540,750,9.0);
    graph.addRoute("Bangalore","Coimbatore",360,520,6.0);
    graph.addRoute("Bangalore","Mangalore",350,550,6.5);
    graph.addRoute("Bangalore","Hampi",340,550,6.0);
    graph.addRoute("Chennai","Hyderabad",630,800,10.0);
    graph.addRoute("Chennai","Kochi",680,850,11.0);
    graph.addRoute("Chennai","Madurai",460,650,8.0);
    graph.addRoute("Chennai","Pondicherry",150,280,3.0);
    graph.addRoute("Chennai","Tirupati",140,260,2.5);
    graph.addRoute("Hyderabad","Vizag",620,800,10.0);
    graph.addRoute("Hyderabad","Warangal",145,280,3.0);
    graph.addRoute("Hyderabad","Tirupati",540,750,9.0);
    graph.addRoute("Kochi","Thiruvananthapuram",210,350,4.0);
    graph.addRoute("Kochi","Mysore",480,680,8.5);
    graph.addRoute("Kochi","Coimbatore",180,320,3.5);
    graph.addRoute("Mysore","Ooty",120,240,3.0);
    graph.addRoute("Coimbatore","Ooty",85,180,2.5);
    graph.addRoute("Coimbatore","Madurai",210,360,4.0);
    graph.addRoute("Madurai","Thiruvananthapuram",290,480,5.5);
    graph.addRoute("Kolkata","Bhubaneswar",440,650,7.0);
    graph.addRoute("Kolkata","Patna",540,750,8.5);
    graph.addRoute("Kolkata","Guwahati",1000,1200,16.0);
    graph.addRoute("Kolkata","Darjeeling",600,800,10.0);
    graph.addRoute("Kolkata","Siliguri",570,780,9.5);
    graph.addRoute("Bhubaneswar","Puri",65,140,1.5);
    graph.addRoute("Bhubaneswar","Vizag",440,650,8.0);
    graph.addRoute("Guwahati","Shillong",98,200,2.5);
    graph.addRoute("Darjeeling","Siliguri",80,160,2.5);
    graph.addRoute("Patna","Ranchi",320,500,6.0);
    graph.addRoute("Ranchi","Raipur",450,650,8.0);
    graph.addRoute("Bhopal","Indore",195,350,3.5);
    graph.addRoute("Bhopal","Jabalpur",290,480,5.0);
    graph.addRoute("Bhopal","Gwalior",420,620,7.0);
    graph.addRoute("Bhopal","Ujjain",190,340,3.5);
    graph.addRoute("Indore","Ujjain",55,130,1.5);
    graph.addRoute("Indore","Ahmedabad",390,580,6.5);
    graph.addRoute("Gwalior","Agra",120,240,2.5);
    graph.addRoute("Jabalpur","Raipur",340,520,6.0);
    graph.addRoute("Raipur","Hyderabad",600,820,10.0);
    graph.addRoute("Raipur","Bhubaneswar",440,650,8.0);

    actMgr.addActivityToDB("Red Fort","Delhi","History",50,4.7,3);
    actMgr.addActivityToDB("Qutub Minar","Delhi","History",40,4.6,2);
    actMgr.addActivityToDB("India Gate","Delhi","Sightseeing",0,4.5,1);
    actMgr.addActivityToDB("Humayun's Tomb","Delhi","History",35,4.7,2);
    actMgr.addActivityToDB("Chandni Chowk Food Walk","Delhi","Food",0,4.8,2);
    actMgr.addActivityToDB("Lotus Temple","Delhi","Spiritual",0,4.6,1);
    actMgr.addActivityToDB("Akshardham Temple","Delhi","Spiritual",0,4.8,3);
    actMgr.addActivityToDB("Taj Mahal","Agra","Sightseeing",50,5.0,3);
    actMgr.addActivityToDB("Agra Fort","Agra","History",40,4.6,2);
    actMgr.addActivityToDB("Fatehpur Sikri","Agra","History",40,4.5,3);
    actMgr.addActivityToDB("Mehtab Bagh Sunset","Agra","Nature",30,4.7,1);
    actMgr.addActivityToDB("Amber Fort","Jaipur","History",100,4.8,3);
    actMgr.addActivityToDB("Hawa Mahal","Jaipur","Sightseeing",50,4.7,1);
    actMgr.addActivityToDB("City Palace Jaipur","Jaipur","Culture",200,4.6,2);
    actMgr.addActivityToDB("Jantar Mantar Jaipur","Jaipur","History",50,4.4,1);
    actMgr.addActivityToDB("Nahargarh Fort","Jaipur","History",50,4.5,2);
    actMgr.addActivityToDB("Ganga Aarti","Varanasi","Spiritual",0,4.9,2);
    actMgr.addActivityToDB("Kashi Vishwanath Temple","Varanasi","Spiritual",0,4.8,2);
    actMgr.addActivityToDB("Boat Ride on Ganga","Varanasi","Nature",150,4.7,2);
    actMgr.addActivityToDB("Sarnath Stupa","Varanasi","History",30,4.5,2);
    actMgr.addActivityToDB("Golden Temple","Amritsar","Spiritual",0,5.0,3);
    actMgr.addActivityToDB("Wagah Border Ceremony","Amritsar","Sightseeing",0,4.8,2);
    actMgr.addActivityToDB("Jallianwala Bagh","Amritsar","History",0,4.6,1);
    actMgr.addActivityToDB("Mall Road Shimla","Shimla","Sightseeing",0,4.5,2);
    actMgr.addActivityToDB("Kufri Snow Point","Shimla","Adventure",200,4.6,3);
    actMgr.addActivityToDB("Christ Church Shimla","Shimla","Culture",0,4.4,1);
    actMgr.addActivityToDB("Rohtang Pass","Manali","Adventure",500,4.8,6);
    actMgr.addActivityToDB("Solang Valley","Manali","Adventure",300,4.7,4);
    actMgr.addActivityToDB("Hadimba Temple","Manali","Spiritual",0,4.6,1);
    actMgr.addActivityToDB("River Rafting","Rishikesh","Adventure",600,4.8,4);
    actMgr.addActivityToDB("Laxman Jhula","Rishikesh","Sightseeing",0,4.5,1);
    actMgr.addActivityToDB("Beatles Ashram","Rishikesh","Culture",150,4.4,2);
    actMgr.addActivityToDB("Bungee Jumping Rishikesh","Rishikesh","Adventure",3500,4.9,2);
    actMgr.addActivityToDB("Gateway of India","Mumbai","Sightseeing",0,4.6,1);
    actMgr.addActivityToDB("Marine Drive","Mumbai","Sightseeing",0,4.7,2);
    actMgr.addActivityToDB("Elephanta Caves","Mumbai","History",40,4.5,4);
    actMgr.addActivityToDB("Dharavi Walk Tour","Mumbai","Culture",500,4.4,3);
    actMgr.addActivityToDB("Siddhivinayak Temple","Mumbai","Spiritual",0,4.7,1);
    actMgr.addActivityToDB("Juhu Beach","Mumbai","Nature",0,4.3,2);
    actMgr.addActivityToDB("Baga Beach","Goa","Nature",0,4.6,4);
    actMgr.addActivityToDB("Dudhsagar Falls","Goa","Nature",400,4.8,6);
    actMgr.addActivityToDB("Old Goa Churches","Goa","History",0,4.5,2);
    actMgr.addActivityToDB("Casino Night Cruise","Goa","Entertainment",2000,4.3,4);
    actMgr.addActivityToDB("Scuba Diving Goa","Goa","Adventure",3000,4.7,3);
    actMgr.addActivityToDB("City Palace Udaipur","Udaipur","History",300,4.8,3);
    actMgr.addActivityToDB("Lake Pichola Boat Ride","Udaipur","Nature",400,4.7,2);
    actMgr.addActivityToDB("Saheliyon ki Bari","Udaipur","Nature",25,4.4,1);
    actMgr.addActivityToDB("Vintage Car Museum","Udaipur","Culture",250,4.5,2);
    actMgr.addActivityToDB("Sabarmati Ashram","Ahmedabad","History",0,4.7,2);
    actMgr.addActivityToDB("Kite Museum","Ahmedabad","Culture",25,4.3,1);
    actMgr.addActivityToDB("Adalaj Stepwell","Ahmedabad","History",0,4.6,1);
    actMgr.addActivityToDB("Ajanta Caves","Aurangabad","History",40,4.9,5);
    actMgr.addActivityToDB("Ellora Caves","Aurangabad","History",40,4.9,5);
    actMgr.addActivityToDB("Bibi Ka Maqbara","Aurangabad","History",25,4.5,2);
    actMgr.addActivityToDB("Lalbagh Botanical Garden","Bangalore","Nature",20,4.5,2);
    actMgr.addActivityToDB("Bangalore Palace","Bangalore","History",230,4.3,2);
    actMgr.addActivityToDB("ISKCON Temple Bangalore","Bangalore","Spiritual",0,4.7,1);
    actMgr.addActivityToDB("Nandi Hills","Bangalore","Nature",30,4.6,4);
    actMgr.addActivityToDB("Mysore Palace","Mysore","History",50,4.9,3);
    actMgr.addActivityToDB("Chamundi Hills","Mysore","Spiritual",0,4.6,2);
    actMgr.addActivityToDB("Brindavan Gardens","Mysore","Nature",40,4.5,2);
    actMgr.addActivityToDB("Chinese Fishing Nets","Kochi","Sightseeing",0,4.5,1);
    actMgr.addActivityToDB("Alleppey Backwaters","Kochi","Nature",800,4.9,5);
    actMgr.addActivityToDB("Mattancherry Palace","Kochi","History",20,4.4,2);
    actMgr.addActivityToDB("Fort Kochi Heritage Walk","Kochi","Culture",200,4.6,3);
    actMgr.addActivityToDB("Charminar","Hyderabad","History",20,4.7,2);
    actMgr.addActivityToDB("Golconda Fort","Hyderabad","History",15,4.6,3);
    actMgr.addActivityToDB("Ramoji Film City","Hyderabad","Entertainment",1200,4.5,8);
    actMgr.addActivityToDB("Hussain Sagar Lake","Hyderabad","Nature",100,4.4,2);
    actMgr.addActivityToDB("Marina Beach","Chennai","Nature",0,4.5,2);
    actMgr.addActivityToDB("Kapaleeshwarar Temple","Chennai","Spiritual",0,4.7,1);
    actMgr.addActivityToDB("Government Museum","Chennai","Culture",15,4.4,2);
    actMgr.addActivityToDB("Victoria Memorial","Kolkata","History",30,4.8,2);
    actMgr.addActivityToDB("Howrah Bridge","Kolkata","Sightseeing",0,4.6,1);
    actMgr.addActivityToDB("Dakshineswar Temple","Kolkata","Spiritual",0,4.7,2);
    actMgr.addActivityToDB("Street Food Tour Kolkata","Kolkata","Food",0,4.8,3);
    actMgr.addActivityToDB("Tiger Hill Sunrise","Darjeeling","Nature",100,4.8,4);
    actMgr.addActivityToDB("Toy Train Ride","Darjeeling","Culture",600,4.7,4);
    actMgr.addActivityToDB("Tea Garden Visit","Darjeeling","Nature",200,4.6,3);
    actMgr.addActivityToDB("Jagannath Temple","Puri","Spiritual",0,4.9,2);
    actMgr.addActivityToDB("Puri Beach","Puri","Nature",0,4.5,3);
    actMgr.addActivityToDB("Virupaksha Temple","Hampi","Spiritual",30,4.8,2);
    actMgr.addActivityToDB("Hampi Ruins Exploration","Hampi","History",40,4.9,5);
    actMgr.addActivityToDB("Tirumala Venkateswara","Tirupati","Spiritual",50,5.0,4);
    actMgr.addActivityToDB("Mahakaleshwar Temple","Ujjain","Spiritual",0,4.9,2);
    actMgr.addActivityToDB("Kshipra River Aarti","Ujjain","Spiritual",0,4.6,1);

    trie.insertSong("Badtameez Dil","Benny Dayal",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.7"}});
    trie.insertSong("Gallan Goodiyaan","Shankar Mahadevan",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.8"}});
    trie.insertSong("London Thumakda","Labh Janjua",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.7"}});
    trie.insertSong("Nagada Sang Dhol","Shreya Ghoshal",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.6"}});
    trie.insertSong("Balam Pichkari","Shalmali Kholgade",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.5"}});
    trie.insertSong("Kar Gayi Chull","Fazilpuria",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.5"}});
    trie.insertSong("Dil Dhadakne Do","Shankar Ehsaan",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.6"}});
    trie.insertSong("Dhinka Chika","Neeraj Shridhar",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.4"}});
    trie.insertSong("Senorita","Shaan",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.5"}});
    trie.insertSong("Zindagi Na Milegi Dobara","Shankar Mahadevan",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.8"}});
    trie.insertSong("Jai Ho","A.R. Rahman",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.9"}});
    trie.insertSong("Vande Mataram","A.R. Rahman",{{"genre","Patriotic"},{"mood","Happy"},{"rating","5.0"}});
    trie.insertSong("Maa Tujhe Salaam","A.R. Rahman",{{"genre","Patriotic"},{"mood","Happy"},{"rating","4.9"}});
    trie.insertSong("Rang De Basanti","Daler Mehndi",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.7"}});
    trie.insertSong("Zinda","Siddharth Mahadevan",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.8"}});
    trie.insertSong("Nashe Si Chadh Gayi","Arijit Singh",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.6"}});
    trie.insertSong("Swag Se Swagat","Vishal Dadlani",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.5"}});
    trie.insertSong("Photocopy","Anushka Manchanda",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.4"}});
    trie.insertSong("Naatu Naatu","Rahul Sipligunj",{{"genre","Telugu"},{"mood","Happy"},{"rating","5.0"}});
    trie.insertSong("G.O.A.T","Diljit Dosanjh",{{"genre","Punjabi"},{"mood","Happy"},{"rating","4.7"}});
    trie.insertSong("Lover","Diljit Dosanjh",{{"genre","Punjabi"},{"mood","Happy"},{"rating","4.6"}});
    trie.insertSong("Lahore","Guru Randhawa",{{"genre","Punjabi"},{"mood","Happy"},{"rating","4.5"}});
    trie.insertSong("Morni Banke","Neha Kakkar",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.4"}});
    trie.insertSong("Unakenna Venum Sollu","Anirudh Ravichander",{{"genre","Tamil"},{"mood","Happy"},{"rating","4.6"}});
    trie.insertSong("Saibo","Shreya Ghoshal",{{"genre","Bollywood"},{"mood","Happy"},{"rating","4.7"}});

    trie.insertSong("Tum Hi Ho","Arijit Singh",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.9"}});
    trie.insertSong("Channa Mereya","Arijit Singh",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.9"}});
    trie.insertSong("Kal Ho Naa Ho","Sonu Nigam",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.8"}});
    trie.insertSong("Ae Dil Hai Mushkil","Arijit Singh",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.7"}});
    trie.insertSong("Kabhi Alvida Naa Kehna","Sonu Nigam",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.7"}});
    trie.insertSong("Dil To Pagal Hai","Lata Mangeshkar",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.8"}});
    trie.insertSong("Phir Le Aya Dil","Rekha Bhardwaj",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.6"}});
    trie.insertSong("Hamari Adhuri Kahani","Arijit Singh",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.6"}});
    trie.insertSong("Dard Dilo Ke","Mohammed Irfan",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.5"}});
    trie.insertSong("Main Dhoondne Ko Zamaane","Arijit Singh",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.6"}});
    trie.insertSong("Jeena Jeena","Atif Aslam",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.7"}});
    trie.insertSong("O Saathi","Atif Aslam",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.6"}});
    trie.insertSong("Tera Hone Laga Hoon","Atif Aslam",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.5"}});
    trie.insertSong("Bulleya","Amit Mishra",{{"genre","Sufi"},{"mood","Emotional"},{"rating","4.8"}});
    trie.insertSong("Ik Onkar","Harshdeep Kaur",{{"genre","Sufi"},{"mood","Emotional"},{"rating","4.9"}});
    trie.insertSong("Dil Diyan Gallan","Atif Aslam",{{"genre","Indie"},{"mood","Emotional"},{"rating","4.7"}});
    trie.insertSong("Pasoori","Ali Sethi",{{"genre","Indie"},{"mood","Emotional"},{"rating","5.0"}});
    trie.insertSong("Ve Maahi","Arijit Singh",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.8"}});
    trie.insertSong("Agar Tum Saath Ho","Arijit Singh",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.9"}});
    trie.insertSong("Chaiyya Chaiyya","Sukhwinder Singh",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","5.0"}});
    trie.insertSong("Kannazhaga","Shreya Ghoshal",{{"genre","Tamil"},{"mood","Emotional"},{"rating","4.8"}});
    trie.insertSong("Vathikkalu Vathikkalu","K.S. Chithra",{{"genre","Malayalam"},{"mood","Emotional"},{"rating","4.7"}});
    trie.insertSong("Nenjukkul Peidhidum","Harris Jayaraj",{{"genre","Tamil"},{"mood","Emotional"},{"rating","4.8"}});
    trie.insertSong("Kesariya","Arijit Singh",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.9"}});
    trie.insertSong("Raabta","Arijit Singh",{{"genre","Bollywood"},{"mood","Emotional"},{"rating","4.5"}});

    trie.insertSong("Tujh Mein Rab Dikhta Hai","Roop Kumar Rathod",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.9"}});
    trie.insertSong("Pehla Nasha","Udit Narayan",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","5.0"}});
    trie.insertSong("Lag Ja Gale","Lata Mangeshkar",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","5.0"}});
    trie.insertSong("Kuch Kuch Hota Hai","Udit Narayan",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.9"}});
    trie.insertSong("Tere Liye","Atif Aslam",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.7"}});
    trie.insertSong("Sun Saathiya","Shreya Ghoshal",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.6"}});
    trie.insertSong("Teri Meri Prem Kahani","Udit Narayan",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.6"}});
    trie.insertSong("Jab Se Tere Naina","Udit Narayan",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.7"}});
    trie.insertSong("Soch Na Sake","Arijit Singh",{{"genre","Punjabi"},{"mood","Romantic"},{"rating","4.7"}});
    trie.insertSong("Enna Sona","Arijit Singh",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.8"}});
    trie.insertSong("Dil Ko Karaar Aaya","Neha Kakkar",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.6"}});
    trie.insertSong("Hawayein","Arijit Singh",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.9"}});
    trie.insertSong("Rehnaa Hai Terre Dil Mein","Rehman",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.8"}});
    trie.insertSong("Pehli Baar Mohabbat","Mohit Chauhan",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.7"}});
    trie.insertSong("Abhi Mujh Mein Kahin","Sonu Nigam",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.8"}});
    trie.insertSong("Tera Ban Jaunga","Akhil Sachdeva",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.7"}});
    trie.insertSong("Apna Bana Le","Arijit Singh",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.7"}});
    trie.insertSong("Mere Haath Mein","Udit Narayan",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.6"}});
    trie.insertSong("Tere Sang Yaara","Atif Aslam",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.7"}});
    trie.insertSong("Kho Gaye Hum Kahan","Jasleen Royal",{{"genre","Indie"},{"mood","Romantic"},{"rating","4.8"}});
    trie.insertSong("Mahi Ve","Udit Narayan",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.7"}});
    trie.insertSong("Ilahi","Mohit Chauhan",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.6"}});
    trie.insertSong("Manike Mage Hithe","Yohani",{{"genre","Indie"},{"mood","Romantic"},{"rating","4.6"}});
    trie.insertSong("Kalank","Arijit Singh",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.5"}});
    trie.insertSong("Tujhe Kitna Chahne Lage","Arijit Singh",{{"genre","Bollywood"},{"mood","Romantic"},{"rating","4.9"}});

    trie.insertSong("Lungi Dance","Honey Singh",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.6"}});
    trie.insertSong("Angrezi Beat","Honey Singh",{{"genre","Punjabi"},{"mood","Party"},{"rating","4.5"}});
    trie.insertSong("Party All Night","Honey Singh",{{"genre","Punjabi"},{"mood","Party"},{"rating","4.5"}});
    trie.insertSong("Desi Beat","Honey Singh",{{"genre","Punjabi"},{"mood","Party"},{"rating","4.4"}});
    trie.insertSong("Hookah Bar","Akshay Kumar",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.4"}});
    trie.insertSong("Dancefloor","Badshah",{{"genre","Punjabi"},{"mood","Party"},{"rating","4.5"}});
    trie.insertSong("Abcd","Badshah",{{"genre","Punjabi"},{"mood","Party"},{"rating","4.6"}});
    trie.insertSong("DJ Waley Babu","Badshah",{{"genre","Punjabi"},{"mood","Party"},{"rating","4.5"}});
    trie.insertSong("Garmi","Badshah",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.6"}});
    trie.insertSong("Paagal","Badshah",{{"genre","Punjabi"},{"mood","Party"},{"rating","4.5"}});
    trie.insertSong("Kala Chashma","Baar Baar Dekho",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.7"}});
    trie.insertSong("Saturday Saturday","Indeep Bakshi",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.5"}});
    trie.insertSong("Malhari","Vishal Dadlani",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.8"}});
    trie.insertSong("Tattad Tattad","Aditya Narayan",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.5"}});
    trie.insertSong("Bhaag DK Bose","Raghu Dixit",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.4"}});
    trie.insertSong("Ainvayi Ainvayi","Salim Merchant",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.5"}});
    trie.insertSong("Jhoome Jo Pathaan","Arijit Singh",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.6"}});
    trie.insertSong("Besharam Rang","Caralisa Monteiro",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.5"}});
    trie.insertSong("Ghungroo","Arijit Singh",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.7"}});
    trie.insertSong("Oo Antava","Indravathi Chauhan",{{"genre","Telugu"},{"mood","Party"},{"rating","4.7"}});
    trie.insertSong("Bijlee Bijlee","Harrdy Sandhu",{{"genre","Punjabi"},{"mood","Party"},{"rating","4.6"}});
    trie.insertSong("Koka","Diljit Dosanjh",{{"genre","Punjabi"},{"mood","Party"},{"rating","4.5"}});
    trie.insertSong("Patiala Peg","Diljit Dosanjh",{{"genre","Punjabi"},{"mood","Party"},{"rating","4.5"}});
    trie.insertSong("Amplifier","Imran Khan",{{"genre","Punjabi"},{"mood","Party"},{"rating","4.6"}});
    trie.insertSong("Kar Har Maidaan Fateh","Sukhwinder Singh",{{"genre","Bollywood"},{"mood","Party"},{"rating","4.8"}});
}

//  MAIN

int main() {
    srand(time(nullptr));

    Graph          graph;
    ItineraryTree  itinerary;
    ActivityManager actMgr;
    MusicTrie      musicTrie;
    FrequencyTracker tracker;
    PlaylistHeap   playlistHeap;

    loadSampleData(graph, actMgr, musicTrie);

    int choice;
    do {
        cout << "\n----------------------------------------------------------\n";
        cout << "                       TRIPTUNES                         \n";
        cout << "          Your Travel & Music Companion                   \n";
        cout << "----------------------------------------------------------\n";
        cout << "----------------------------------------------------------\n";
        cout << "  1.  Route Planning                                      \n";
        cout << "  2.  Itinerary Planning                                  \n";
        cout << "  3.  Activity Explorer                                   \n";
        cout << "  4.  Music Library                                       \n";
        cout << "  5.  Song Frequency Tracker                              \n";
        cout << "  6.  Playlist Generator                                  \n";
        cout << "  7.  Admin Control Panel                                 \n";
        cout << "  0.  Exit                                                \n";
        cout << "----------------------------------------------------------\n";
        cout << "Enter choice: ";
        choice = safeReadInt();

        switch (choice) {
            case 1: routePlanningMenu(graph);              break;
            case 2: itineraryMenu(itinerary, actMgr);             break;
            case 3: activityMenu(actMgr);                  break;
            case 4: musicLibraryMenu(musicTrie);           break;
            case 5: frequencyMenu(tracker, musicTrie);        break;
            case 6: playlistMenu(playlistHeap, musicTrie); break;
            case 7: adminPanel(graph, actMgr);             break;
            case 0: cout << "\n  Thank you for using TripTunes! Happy travels!\n\n"; break;
            default: cout << "  Invalid choice. Please try again.\n";
        }
    } while (choice != 0);

    return 0;
}
