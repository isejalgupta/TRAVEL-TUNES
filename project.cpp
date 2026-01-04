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

using namespace std;

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
        unordered_map<string, double> distances;
        unordered_map<string, string> previous;

        for (const auto& city : cities) {
            distances[city.first] = numeric_limits<double>::infinity();
        }
        distances[source] = 0;

        auto cmp = [](pair<double, string> a, pair<double, string> b) {
            return a.first > b.first;
        };
        priority_queue<pair<double, string>, vector<pair<double, string>>, decltype(cmp)> pq(cmp);
        pq.push({0, source});

        while (!pq.empty()) {
            auto [currentDist, current] = pq.top();
            pq.pop();

            if (current == destination) break;
            if (currentDist > distances[current]) continue;

            for (const Route& route : routes[current]) {
                double weight = 0;
                if (weightType == "distance") weight = route.distance;
                else if (weightType == "cost") weight = route.cost;
                else if (weightType == "time") weight = route.time;

                double distance = currentDist + weight;

                if (distance < distances[route.destination]) {
                    distances[route.destination] = distance;
                    previous[route.destination] = current;
                    pq.push({distance, route.destination});
                }
            }
        }

        vector<string> path;
        string current = destination;
        while (!current.empty()) {
            path.push_back(current);
            current = previous[current];
        }
        reverse(path.begin(), path.end());

        return {path, distances[destination], weightType};
    }

public:
    bool addCity(const string& cityName, const map<string, string>& metadata = {}) {
        if (cities.find(cityName) == cities.end()) {
            cities[cityName] = metadata;
            return true;
        }
        return false;
    }

    void addRoute(const string& city1, const string& city2, double distance, double cost, double time) {
        routes[city1].push_back({city2, distance, cost, time});
        routes[city2].push_back({city1, distance, cost, time});
    }

    void removeRoute(const string& city1, const string& city2) {
        auto& routes1 = routes[city1];
        routes1.erase(remove_if(routes1.begin(), routes1.end(),
            [&city2](const Route& r) { return r.destination == city2; }), routes1.end());

        auto& routes2 = routes[city2];
        routes2.erase(remove_if(routes2.begin(), routes2.end(),
            [&city1](const Route& r) { return r.destination == city1; }), routes2.end());
    }

    vector<string> getAllCities() {
        vector<string> cityList;
        for (const auto& city : cities) {
            cityList.push_back(city.first);
        }
        return cityList;
    }

    PathResult findShortestPath(const string& source, const string& destination) {
        return dijkstra(source, destination, "distance");
    }

    PathResult findCheapestPath(const string& source, const string& destination) {
        return dijkstra(source, destination, "cost");
    }

    PathResult findFastestPath(const string& source, const string& destination) {
        return dijkstra(source, destination, "time");
    }

    PathResult findPathWithStops(const string& source, const string& destination, const vector<string>& stops) {
        vector<string> allStops = {source};
        allStops.insert(allStops.end(), stops.begin(), stops.end());
        allStops.push_back(destination);

        vector<string> totalPath;
        double totalDistance = 0;

        for (size_t i = 0; i < allStops.size() - 1; i++) {
            PathResult result = findShortestPath(allStops[i], allStops[i + 1]);
            totalPath.insert(totalPath.end(), result.path.begin(), result.path.end() - 1);
            totalDistance += result.totalWeight;
        }
        totalPath.push_back(destination);

        return {totalPath, totalDistance, "distance"};
    }

    vector<PathResult> getAlternativePaths(const string& source, const string& destination, int k = 3) {
        vector<PathResult> paths;
        PathResult mainPath = findShortestPath(source, destination);
        paths.push_back(mainPath);

        for (size_t i = 1; i < mainPath.path.size() - 1 && paths.size() < k; i++) {
            string excludeCity = mainPath.path[i];
            vector<Route> tempRoutes = routes[excludeCity];
            routes[excludeCity].clear();

            PathResult altPath = findShortestPath(source, destination);
            if (altPath.totalWeight != numeric_limits<double>::infinity()) {
                paths.push_back(altPath);
            }

            routes[excludeCity] = tempRoutes;
        }

        return paths;
    }
};

class ItineraryNode {
public:
    string nodeType;
    map<string, string> data;
    vector<ItineraryNode*> children;

    ItineraryNode(const string& type, const map<string, string>& nodeData)
        : nodeType(type), data(nodeData) {}

    void addChild(ItineraryNode* child) {
        children.push_back(child);
    }

    void removeChild(ItineraryNode* child) {
        children.erase(remove(children.begin(), children.end(), child), children.end());
    }

    ~ItineraryNode() {
        for (auto child : children) {
            delete child;
        }
    }
};

class ItineraryTree {
private:
    ItineraryNode* root;

public:
    ItineraryTree() : root(nullptr) {}

    ItineraryNode* createItinerary(const string& tripName, const string& startDate, const string& endDate) {
        map<string, string> data = {
            {"name", tripName},
            {"start_date", startDate},
            {"end_date", endDate}
        };
        root = new ItineraryNode("trip", data);
        return root;
    }

    ItineraryNode* addDay(int dayNumber, const string& date) {
        if (!root) return nullptr;

        map<string, string> data = {
            {"day_number", to_string(dayNumber)},
            {"date", date}
        };
        ItineraryNode* dayNode = new ItineraryNode("day", data);
        root->addChild(dayNode);
        return dayNode;
    }

    ItineraryNode* addActivity(int dayNumber, const map<string, string>& activity) {
        if (!root) return nullptr;

        for (auto dayNode : root->children) {
            if (dayNode->data["day_number"] == to_string(dayNumber)) {
                ItineraryNode* activityNode = new ItineraryNode("activity", activity);
                dayNode->addChild(activityNode);
                return activityNode;
            }
        }
        return nullptr;
    }

    bool removeActivity(int dayNumber, const string& activityId) {
        if (!root) return false;

        for (auto dayNode : root->children) {
            if (dayNode->data["day_number"] == to_string(dayNumber)) {
                for (auto activityNode : dayNode->children) {
                    if (activityNode->data["id"] == activityId) {
                        dayNode->removeChild(activityNode);
                        delete activityNode;
                        return true;
                    }
                }
            }
        }
        return false;
    }

    ItineraryNode* moveActivity(int fromDay, int toDay, const string& activityId) {
        map<string, string> activityData;
        ItineraryNode* activityToMove = nullptr;

        for (auto dayNode : root->children) {
            if (dayNode->data["day_number"] == to_string(fromDay)) {
                for (auto activityNode : dayNode->children) {
                    if (activityNode->data["id"] == activityId) {
                        activityData = activityNode->data;
                        dayNode->removeChild(activityNode);
                        delete activityNode;
                        break;
                    }
                }
            }
        }

        if (!activityData.empty()) {
            return addActivity(toDay, activityData);
        }
        return nullptr;
    }

    string displayItinerary() {
        if (!root) return "No itinerary created";

        string result = "\n============================================================\n";
        result += "Trip: " + root->data["name"] + "\n";
        result += "Duration: " + root->data["start_date"] + " to " + root->data["end_date"] + "\n";
        result += "============================================================\n\n";

        for (auto dayNode : root->children) {
            result += "Day " + dayNode->data["day_number"] + " - " + dayNode->data["date"] + "\n";
            result += "----------------------------------------\n";

            if (dayNode->children.empty()) {
                result += "  No activities planned\n";
            } else {
                int count = 1;
                for (auto activity : dayNode->children) {
                    result += "  " + to_string(count++) + ". " + activity->data["name"] + "\n";
                    result += "     Duration: " + activity->data["duration"] + " | ";
                    result += "Cost: $" + activity->data["cost"] + "\n";
                }
            }
            result += "\n";
        }

        return result;
    }

    vector<map<string, string>> getDaySchedule(int dayNumber) {
        vector<map<string, string>> activities;
        if (!root) return activities;

        for (auto dayNode : root->children) {
            if (dayNode->data["day_number"] == to_string(dayNumber)) {
                for (auto activity : dayNode->children) {
                    activities.push_back(activity->data);
                }
                break;
            }
        }
        return activities;
    }

    double getTotalDuration() {
        if (!root) return 0;

        double total = 0;
        for (auto dayNode : root->children) {
            for (auto activity : dayNode->children) {
                total += stod(activity->data["duration"]);
            }
        }
        return total;
    }

    double getTotalCost() {
        if (!root) return 0;

        double total = 0;
        for (auto dayNode : root->children) {
            for (auto activity : dayNode->children) {
                total += stod(activity->data["cost"]);
            }
        }
        return total;
    }

    vector<map<string, string>> inOrderTraversal() {
        vector<map<string, string>> result;
        inOrderHelper(root, result);
        return result;
    }

    void inOrderHelper(ItineraryNode* node, vector<map<string, string>>& result) {
        if (!node) return;

        if (!node->children.empty()) {
            inOrderHelper(node->children[0], result);
        }

        result.push_back(node->data);

        for (size_t i = 1; i < node->children.size(); i++) {
            inOrderHelper(node->children[i], result);
        }
    }

    vector<pair<int, map<string, string>>> preOrderTraversal() {
        vector<pair<int, map<string, string>>> result;
        preOrderHelper(root, result, 0);
        return result;
    }

    void preOrderHelper(ItineraryNode* node, vector<pair<int, map<string, string>>>& result, int level) {
        if (!node) return;

        result.push_back({level, node->data});
        for (auto child : node->children) {
            preOrderHelper(child, result, level + 1);
        }
    }

    ~ItineraryTree() {
        delete root;
    }
};


struct Activity {
    string id;
    string name;
    string location;
    string category;
    double cost;
    double rating;
    double duration;
};

class ActivityManager {
private:
    unordered_map<string, vector<Activity>> activitiesDB;

    vector<Activity> quickSort(vector<Activity> arr, const string& key, const string& order) {
        if (arr.size() <= 1) return arr;

        Activity pivot = arr[arr.size() / 2];
        vector<Activity> left, middle, right;

        for (const Activity& a : arr) {
            double pivotVal = 0, aVal = 0;

            if (key == "cost") {
                pivotVal = pivot.cost;
                aVal = a.cost;
            } else if (key == "rating") {
                pivotVal = pivot.rating;
                aVal = a.rating;
            } else if (key == "duration") {
                pivotVal = pivot.duration;
                aVal = a.duration;
            }

            if (order == "asc") {
                if (aVal < pivotVal) left.push_back(a);
                else if (aVal == pivotVal) middle.push_back(a);
                else right.push_back(a);
            } else {
                if (aVal > pivotVal) left.push_back(a);
                else if (aVal == pivotVal) middle.push_back(a);
                else right.push_back(a);
            }
        }

        vector<Activity> sortedLeft = quickSort(left, key, order);
        vector<Activity> sortedRight = quickSort(right, key, order);

        sortedLeft.insert(sortedLeft.end(), middle.begin(), middle.end());
        sortedLeft.insert(sortedLeft.end(), sortedRight.begin(), sortedRight.end());

        return sortedLeft;
    }

public:
    Activity addActivityToDB(const string& name, const string& location, const string& category,
                            double cost, double rating, double duration) {
        Activity activity = {
            location + "_" + to_string(activitiesDB[location].size()),
            name, location, category, cost, rating, duration
        };

        activitiesDB[location].push_back(activity);
        return activity;
    }

    vector<Activity> getAllActivities(const string& city) {
        return activitiesDB[city];
    }

    vector<Activity> getActivityByCategory(const string& category) {
        vector<Activity> result;
        for (const auto& cityPair : activitiesDB) {
            for (const Activity& a : cityPair.second) {
                if (a.category == category) {
                    result.push_back(a);
                }
            }
        }
        return result;
    }

    vector<Activity> sortByCost(vector<Activity> activities, const string& order = "asc") {
        return quickSort(activities, "cost", order);
    }

    vector<Activity> sortByRating(vector<Activity> activities, const string& order = "desc") {
        return quickSort(activities, "rating", order);
    }

    vector<Activity> sortByDuration(vector<Activity> activities, const string& order = "asc") {
        return quickSort(activities, "duration", order);
    }


vector<Activity> sortByDistance(vector<Activity> activities, const string& currentLocation) {
    sort(activities.begin(), activities.end(),
        [&currentLocation](const Activity& a, const Activity& b) {
            size_t hashA = hash<string>{}(a.location);
            size_t hashB = hash<string>{}(b.location);
            size_t hashCurrent = hash<string>{}(currentLocation);

            long long diffA = static_cast<long long>(hashA) - static_cast<long long>(hashCurrent);
            long long diffB = static_cast<long long>(hashB) - static_cast<long long>(hashCurrent);

            long long absDiffA = (diffA < 0) ? -diffA : diffA;
            long long absDiffB = (diffB < 0) ? -diffB : diffB;

            return absDiffA < absDiffB;
        });
    return activities;
}

    Activity* binarySearchByName(vector<Activity>& activities, const string& name) {
        sort(activities.begin(), activities.end(),
            [](const Activity& a, const Activity& b) { return a.name < b.name; });

        int left = 0, right = activities.size() - 1;

        while (left <= right) {
            int mid = left + (right - left) / 2;

            if (activities[mid].name == name) {
                return &activities[mid];
            } else if (activities[mid].name < name) {
                left = mid + 1;
            } else {
                right = mid - 1;
            }
        }
        return nullptr;
    }

    vector<Activity> binarySearchByPrice(vector<Activity> activities, double maxPrice) {
        sort(activities.begin(), activities.end(),
            [](const Activity& a, const Activity& b) { return a.cost < b.cost; });

        vector<Activity> result;
        for (const Activity& a : activities) {
            if (a.cost <= maxPrice) {
                result.push_back(a);
            } else {
                break;
            }
        }
        return result;
    }

    vector<Activity> linearSearchByCategory(const vector<Activity>& activities, const string& category) {
        vector<Activity> result;
        for (const Activity& a : activities) {
            if (a.category == category) {
                result.push_back(a);
            }
        }
        return result;
    }

    vector<Activity> filterActivities(vector<Activity> activities, const map<string, double>& criteria) {
        vector<Activity> result = activities;

        if (criteria.find("max_cost") != criteria.end()) {
            result.erase(remove_if(result.begin(), result.end(),
                [&criteria](const Activity& a) { return a.cost > criteria.at("max_cost"); }), result.end());
        }

        if (criteria.find("min_rating") != criteria.end()) {
            result.erase(remove_if(result.begin(), result.end(),
                [&criteria](const Activity& a) { return a.rating < criteria.at("min_rating"); }), result.end());
        }

        if (criteria.find("max_duration") != criteria.end()) {
            result.erase(remove_if(result.begin(), result.end(),
                [&criteria](const Activity& a) { return a.duration > criteria.at("max_duration"); }), result.end());
        }

        return result;
    }
};


struct Song {
    string name;
    string artist;
    map<string, string> metadata;
};

class TrieNode {
public:
    unordered_map<char, TrieNode*> children;
    bool isEnd;
    Song* songData;

    TrieNode() : isEnd(false), songData(nullptr) {}

    ~TrieNode() {
        for (auto& pair : children) {
            delete pair.second;
        }
        delete songData;
    }
};

class MusicTrie {
private:
    TrieNode* root;

    void collectSongs(TrieNode* node, string prefix, vector<Song>& songs) {
        if (!node) return;

        if (node->isEnd && node->songData) {
            songs.push_back(*node->songData);
        }

        for (auto& pair : node->children) {
            collectSongs(pair.second, prefix + pair.first, songs);
        }
    }

    void collectAllSongsHelper(TrieNode* node, vector<Song>& songs) {
        if (!node) return;

        if (node->isEnd && node->songData) {
            songs.push_back(*node->songData);
        }

        for (auto& pair : node->children) {
            collectAllSongsHelper(pair.second, songs);
        }
    }

public:
    MusicTrie() {
        root = new TrieNode();
    }

    void insertSong(const string& songName, const string& artist, const map<string, string>& metadata = {}) {
        TrieNode* node = root;
        string lowerName = songName;
        transform(lowerName.begin(), lowerName.end(), lowerName.begin(), ::tolower);

        for (char c : lowerName) {
            if (node->children.find(c) == node->children.end()) {
                node->children[c] = new TrieNode();
            }
            node = node->children[c];
        }

        node->isEnd = true;
        node->songData = new Song{songName, artist, metadata};
    }

    vector<Song> searchPrefix(const string& prefix) {
        TrieNode* node = root;
        string lowerPrefix = prefix;
        transform(lowerPrefix.begin(), lowerPrefix.end(), lowerPrefix.begin(), ::tolower);

        for (char c : lowerPrefix) {
            if (node->children.find(c) == node->children.end()) {
                return vector<Song>();
            }
            node = node->children[c];
        }

        vector<Song> songs;
        collectSongs(node, prefix, songs);
        return songs;
    }

    vector<Song> autoComplete(const string& prefix, int limit) {
        vector<Song> allMatches = searchPrefix(prefix);

        if (allMatches.size() <= limit) {
            return allMatches;
        }

        return vector<Song>(allMatches.begin(), allMatches.begin() + limit);
    }

    bool deleteSong(const string& songName) {
        return deleteSongHelper(root, songName, 0);
    }

    bool deleteSongHelper(TrieNode* node, const string& songName, int depth) {
        if (!node) return false;

        string lowerName = songName;
        transform(lowerName.begin(), lowerName.end(), lowerName.begin(), ::tolower);

        if (depth == lowerName.length()) {
            if (!node->isEnd) return false;

            node->isEnd = false;
            delete node->songData;
            node->songData = nullptr;

            return node->children.empty();
        }

        char c = lowerName[depth];
        if (node->children.find(c) == node->children.end()) {
            return false;
        }

        bool shouldDeleteChild = deleteSongHelper(node->children[c], songName, depth + 1);

        if (shouldDeleteChild) {
            delete node->children[c];
            node->children.erase(c);
            return !node->isEnd && node->children.empty();
        }

        return false;
    }

    vector<Song> getAllSongs() {
        vector<Song> songs;
        collectAllSongsHelper(root, songs);
        return songs;
    }

    vector<Song> searchByArtist(const string& artistName) {
        vector<Song> allSongs = getAllSongs();
        vector<Song> result;

        for (const Song& song : allSongs) {
            if (song.artist == artistName) {
                result.push_back(song);
            }
        }

        return result;
    }

    ~MusicTrie() {
        delete root;
    }
};


class FrequencyTracker {
private:
    unordered_map<string, int> playCount;
    unordered_map<string, Song> songMetadata;

public:
    void initializeFrequencyMap() {
        playCount.clear();
        songMetadata.clear();
    }

    void incrementPlayCount(const string& songId) {
        playCount[songId]++;
    }

    int getPlayCount(const string& songId) {
        return playCount[songId];
    }

    vector<pair<string, int>> getMostPlayed(int k) {
        vector<pair<string, int>> songs(playCount.begin(), playCount.end());

        sort(songs.begin(), songs.end(),
            [](const pair<string, int>& a, const pair<string, int>& b) {
                return a.second > b.second;
            });

        if (songs.size() <= k) {
            return songs;
        }

        return vector<pair<string, int>>(songs.begin(), songs.begin() + k);
    }

    void resetFrequencies() {
        playCount.clear();
    }

    Song getSongMetadata(const string& songId) {
        return songMetadata[songId];
    }

    void updateSongInfo(const string& songId, const Song& newData) {
        songMetadata[songId] = newData;
    }

    void addSongMetadata(const string& songId, const Song& song) {
        songMetadata[songId] = song;
        if (playCount.find(songId) == playCount.end()) {
            playCount[songId] = 0;
        }
    }
};


struct SongWithPriority {
    Song song;
    double priority;

    bool operator<(const SongWithPriority& other) const {
        return priority < other.priority;
    }
};

class PlaylistHeap {
private:
    priority_queue<SongWithPriority> maxHeap;
    vector<Song> currentPlaylist;

public:
    void buildMaxHeap(const vector<Song>& songs, const string& criteria = "rating") {
        while (!maxHeap.empty()) maxHeap.pop();

        for (const Song& song : songs) {
            double priority = 0;

            if (criteria == "rating" && song.metadata.find("rating") != song.metadata.end()) {
                priority = stod(song.metadata.at("rating"));
            } else if (criteria == "frequency" && song.metadata.find("frequency") != song.metadata.end()) {
                priority = stod(song.metadata.at("frequency"));
            } else {
                priority = 1.0;
            }

            maxHeap.push({song, priority});
        }
    }

    vector<Song> extractTopK(int k) {
        vector<Song> topSongs;
        priority_queue<SongWithPriority> tempHeap = maxHeap;

        for (int i = 0; i < k && !tempHeap.empty(); i++) {
            topSongs.push_back(tempHeap.top().song);
            tempHeap.pop();
        }

        return topSongs;
    }

    void insertSong(const Song& song, double priority) {
        maxHeap.push({song, priority});
    }

    void heapify() {
        vector<SongWithPriority> temp;
        while (!maxHeap.empty()) {
            temp.push_back(maxHeap.top());
            maxHeap.pop();
        }

        for (const auto& item : temp) {
            maxHeap.push(item);
        }
    }

    vector<Song> getTopSongs(int k, const string& criteria) {
        return extractTopK(k);
    }

    vector<Song> mergePlaylists(const vector<Song>& playlist1, const vector<Song>& playlist2) {
        vector<Song> merged = playlist1;
        merged.insert(merged.end(), playlist2.begin(), playlist2.end());
        return merged;
    }

    vector<Song> generatePlaylist(int tripDuration, const string& mood, const string& genre) {
        vector<Song> playlist = extractTopK(tripDuration / 3);
        currentPlaylist = playlist;
        return playlist;
    }

    vector<Song> optimizePlaylistOrder(const vector<Song>& songs) {
        return songs;
    }

    void addToPlaylist(const Song& song) {
        currentPlaylist.push_back(song);
    }

    bool removeFromPlaylist(const string& songId) {
        for (auto it = currentPlaylist.begin(); it != currentPlaylist.end(); ++it) {
            if (it->name == songId) {
                currentPlaylist.erase(it);
                return true;
            }
        }
        return false;
    }

    vector<Song> shufflePlaylist() {
        vector<Song> shuffled = currentPlaylist;
        random_shuffle(shuffled.begin(), shuffled.end());
        return shuffled;
    }

    vector<Song> getCurrentPlaylist() {
        return currentPlaylist;
    }
};

void displayMainMenu() {
    cout << "\n========================================================\n";
    cout << "       TRAVEL PLANNING & MUSIC SYSTEM                   \n";
    cout << "========================================================\n";
    cout << "1.  Route Planning (Graph)\n";
    cout << "2.  Itinerary Management (Tree)\n";
    cout << "3.  Activity Search & Sort\n";
    cout << "4.  Music Library (Trie)\n";
    cout << "5.  Song Frequency Tracking\n";
    cout << "6.  Playlist Generation (Heap)\n";
    cout << "0.  Exit\n";
    cout << "--------------------------------------------------------\n";
    cout << "Enter your choice: ";
}

void routePlanningMenu(Graph& graph) {
    int choice;
    do {
        cout << "\n--- ROUTE PLANNING ---\n";
        cout << "1. Add City\n";
        cout << "2. Add Route\n";
        cout << "3. Find Shortest Path\n";
        cout << "4. Find Cheapest Path\n";
        cout << "5. Find Fastest Path\n";
        cout << "6. Find Path with Stops\n";
        cout << "7. Get Alternative Paths\n";
        cout << "8. View All Cities\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        cin >> choice;

        if (choice == 1) {
            string city;
            cout << "Enter city name: ";
            cin.ignore();
            getline(cin, city);
            if (graph.addCity(city)) {
                cout << "✓ City added successfully!\n";
            } else {
                cout << "✗ City already exists!\n";
            }
        }
        else if (choice == 2) {
            string city1, city2;
            double distance, cost, time;
            cout << "Enter first city: ";
            cin.ignore();
            getline(cin, city1);
            cout << "Enter second city: ";
            getline(cin, city2);
            cout << "Enter distance (km): ";
            cin >> distance;
            cout << "Enter cost ($): ";
            cin >> cost;
            cout << "Enter time (hours): ";
            cin >> time;
            graph.addRoute(city1, city2, distance, cost, time);
            cout << "✓ Route added successfully!\n";
        }
        else if (choice == 3) {
            string source, dest;
            cout << "Enter source city: ";
            cin.ignore();
            getline(cin, source);
            cout << "Enter destination city: ";
            getline(cin, dest);
            auto result = graph.findShortestPath(source, dest);
            cout << "\n--- Shortest Path ---\n";
            cout << "Path: ";
            for (size_t i = 0; i < result.path.size(); i++) {
                cout << result.path[i];
                if (i < result.path.size() - 1) cout << " → ";
            }
            cout << "\nTotal Distance: " << result.totalWeight << " km\n";
        }
        else if (choice == 4) {
            string source, dest;
            cout << "Enter source city: ";
            cin.ignore();
            getline(cin, source);
            cout << "Enter destination city: ";
            getline(cin, dest);
            auto result = graph.findCheapestPath(source, dest);
            cout << "\n--- Cheapest Path ---\n";
            cout << "Path: ";
            for (size_t i = 0; i < result.path.size(); i++) {
                cout << result.path[i];
                if (i < result.path.size() - 1) cout << " → ";
            }
            cout << "\nTotal Cost: $" << result.totalWeight << "\n";
        }
        else if (choice == 5) {
            string source, dest;
            cout << "Enter source city: ";
            cin.ignore();
            getline(cin, source);
            cout << "Enter destination city: ";
            getline(cin, dest);
            auto result = graph.findFastestPath(source, dest);
            cout << "\n--- Fastest Path ---\n";
            cout << "Path: ";
            for (size_t i = 0; i < result.path.size(); i++) {
                cout << result.path[i];
                if (i < result.path.size() - 1) cout << " → ";
            }
            cout << "\nTotal Time: " << result.totalWeight << " hours\n";
        }
        else if (choice == 6) {
            string source, dest;
            int numStops;
            cout << "Enter source city: ";
            cin.ignore();
            getline(cin, source);
            cout << "Enter destination city: ";
            getline(cin, dest);
            cout << "Number of stops: ";
            cin >> numStops;
            vector<string> stops;
            cin.ignore();
            for (int i = 0; i < numStops; i++) {
                string stop;
                cout << "Stop " << (i + 1) << ": ";
                getline(cin, stop);
                stops.push_back(stop);
            }
            auto result = graph.findPathWithStops(source, dest, stops);
            cout << "\n--- Path with Stops ---\n";
            cout << "Path: ";
            for (size_t i = 0; i < result.path.size(); i++) {
                cout << result.path[i];
                if (i < result.path.size() - 1) cout << " → ";
            }
            cout << "\nTotal Distance: " << result.totalWeight << " km\n";
        }
        else if (choice == 7) {
            string source, dest;
            cout << "Enter source city: ";
            cin.ignore();
            getline(cin, source);
            cout << "Enter destination city: ";
            getline(cin, dest);
            auto paths = graph.getAlternativePaths(source, dest, 3);
            cout << "\n--- Alternative Paths ---\n";
            for (size_t i = 0; i < paths.size(); i++) {
                cout << "Path " << (i + 1) << ": ";
                for (size_t j = 0; j < paths[i].path.size(); j++) {
                    cout << paths[i].path[j];
                    if (j < paths[i].path.size() - 1) cout << " → ";
                }
                cout << " (Distance: " << paths[i].totalWeight << " km)\n";
            }
        }
        else if (choice == 8) {
            auto cities = graph.getAllCities();
            cout << "\n--- All Cities ---\n";
            for (size_t i = 0; i < cities.size(); i++) {
                cout << (i + 1) << ". " << cities[i] << "\n";
            }
        }
    } while (choice != 0);
}

void itineraryMenu(ItineraryTree& itinerary) {
    int choice;
    do {
        cout << "\n--- ITINERARY MANAGEMENT ---\n";
        cout << "1. Create Itinerary\n";
        cout << "2. Add Day\n";
        cout << "3. Add Activity\n";
        cout << "4. Remove Activity\n";
        cout << "5. Move Activity\n";
        cout << "6. Display Itinerary\n";
        cout << "7. Get Day Schedule\n";
        cout << "8. View Total Cost & Duration\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        cin >> choice;

        if (choice == 1) {
            string name, start, end;
            cout << "Enter trip name: ";
            cin.ignore();
            getline(cin, name);
            cout << "Start date (YYYY-MM-DD): ";
            getline(cin, start);
            cout << "End date (YYYY-MM-DD): ";
            getline(cin, end);
            itinerary.createItinerary(name, start, end);
            cout << "✓ Itinerary created!\n";
        }
        else if (choice == 2) {
            int dayNum;
            string date;
            cout << "Enter day number: ";
            cin >> dayNum;
            cout << "Enter date (YYYY-MM-DD): ";
            cin.ignore();
            getline(cin, date);
            itinerary.addDay(dayNum, date);
            cout << "✓ Day added!\n";
        }
        else if (choice == 3) {
            int dayNum;
            string name, duration, cost;
            cout << "Enter day number: ";
            cin >> dayNum;
            cin.ignore();
            cout << "Activity name: ";
            getline(cin, name);
            cout << "Duration (hours): ";
            getline(cin, duration);
            cout << "Cost ($): ";
            getline(cin, cost);

            map<string, string> activity = {
                {"id", "act_" + to_string(rand() % 10000)},
                {"name", name},
                {"duration", duration},
                {"cost", cost}
            };
            itinerary.addActivity(dayNum, activity);
            cout << "✓ Activity added!\n";
        }
        else if (choice == 4) {
            int dayNum;
            string actId;
            cout << "Enter day number: ";
            cin >> dayNum;
            cout << "Enter activity ID: ";
            cin >> actId;
            if (itinerary.removeActivity(dayNum, actId)) {
                cout << "✓ Activity removed!\n";
            } else {
                cout << "✗ Activity not found!\n";
            }
        }
        else if (choice == 5) {
            int fromDay, toDay;
            string actId;
            cout << "From day: ";
            cin >> fromDay;
            cout << "To day: ";
            cin >> toDay;
            cout << "Activity ID: ";
            cin >> actId;
            if (itinerary.moveActivity(fromDay, toDay, actId)) {
                cout << "✓ Activity moved!\n";
            } else {
                cout << "✗ Failed to move activity!\n";
            }
        }
        else if (choice == 6) {
            cout << itinerary.displayItinerary();
        }
        else if (choice == 7) {
            int dayNum;
            cout << "Enter day number: ";
            cin >> dayNum;
            auto schedule = itinerary.getDaySchedule(dayNum);
            cout << "\n--- Day " << dayNum << " Schedule ---\n";
            for (size_t i = 0; i < schedule.size(); i++) {
                cout << (i + 1) << ". " << schedule[i]["name"] << "\n";
            }
        }
        else if (choice == 8) {
            cout << "\n--- Trip Summary ---\n";
            cout << "Total Duration: " << itinerary.getTotalDuration() << " hours\n";
            cout << "Total Cost: $" << itinerary.getTotalCost() << "\n";
        }
    } while (choice != 0);
}

void activityMenu(ActivityManager& activityMgr) {
    int choice;
    do {
        cout << "\n--- ACTIVITY MANAGEMENT ---\n";
        cout << "1. Add Activity\n";
        cout << "2. View All Activities (by City)\n";
        cout << "3. Sort by Cost\n";
        cout << "4. Sort by Rating\n";
        cout << "5. Sort by Duration\n";
        cout << "6. Filter Activities\n";
        cout << "7. Search by Name\n";
        cout << "8. Search by Category\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        cin >> choice;

        if (choice == 1) {
            string name, location, category;
            double cost, rating, duration;
            cout << "Activity name: ";
            cin.ignore();
            getline(cin, name);
            cout << "Location: ";
            getline(cin, location);
            cout << "Category: ";
            getline(cin, category);
            cout << "Cost ($): ";
            cin >> cost;
            cout << "Rating (0-5): ";
            cin >> rating;
            cout << "Duration (hours): ";
            cin >> duration;

            activityMgr.addActivityToDB(name, location, category, cost, rating, duration);
            cout << "✓ Activity added!\n";
        }
        else if (choice == 2) {
            string city;
            cout << "Enter city: ";
            cin.ignore();
            getline(cin, city);
            auto activities = activityMgr.getAllActivities(city);
            cout << "\n--- Activities in " << city << " ---\n";
            for (size_t i = 0; i < activities.size(); i++) {
                cout << (i + 1) << ". " << activities[i].name
                     << " | $" << activities[i].cost
                     << " | ⭐" << activities[i].rating << "\n";
            }
        }
        else if (choice == 3) {
            string city, order;
            cout << "Enter city: ";
            cin.ignore();
            getline(cin, city);
            cout << "Order (asc/desc): ";
            cin >> order;
            auto activities = activityMgr.getAllActivities(city);
            activities = activityMgr.sortByCost(activities, order);
            cout << "\n--- Sorted by Cost ---\n";
            for (size_t i = 0; i < activities.size(); i++) {
                cout << (i + 1) << ". " << activities[i].name
                     << " | $" << activities[i].cost << "\n";
            }
        }
        else if (choice == 4) {
            string city;
            cout << "Enter city: ";
            cin.ignore();
            getline(cin, city);
            auto activities = activityMgr.getAllActivities(city);
            activities = activityMgr.sortByRating(activities);
            cout << "\n--- Sorted by Rating ---\n";
            for (size_t i = 0; i < activities.size(); i++) {
                cout << (i + 1) << ". " << activities[i].name
                     << " | ⭐" << activities[i].rating << "\n";
            }
        }
        else if (choice == 6) {
            string city;
            double maxCost, minRating, maxDuration;
            cout << "Enter city: ";
            cin.ignore();
            getline(cin, city);
            cout << "Max cost ($): ";
            cin >> maxCost;
            cout << "Min rating (0-5): ";
            cin >> minRating;
            cout << "Max duration (hours): ";
            cin >> maxDuration;

            map<string, double> criteria = {
                {"max_cost", maxCost},
                {"min_rating", minRating},
                {"max_duration", maxDuration}
            };

            auto activities = activityMgr.getAllActivities(city);
            activities = activityMgr.filterActivities(activities, criteria);
            cout << "\n--- Filtered Activities ---\n";
            for (size_t i = 0; i < activities.size(); i++) {
                cout << (i + 1) << ". " << activities[i].name
                     << " | $" << activities[i].cost
                     << " | ⭐" << activities[i].rating
                     << " | " << activities[i].duration << "h\n";
            }
        }
    } while (choice != 0);
}

void musicLibraryMenu(MusicTrie& musicTrie) {
    int choice;
    do {
        cout << "\n--- MUSIC LIBRARY ---\n";
        cout << "1. Add Song\n";
        cout << "2. Search by Prefix\n";
        cout << "3. Autocomplete\n";
        cout << "4. Search by Artist\n";
        cout << "5. View All Songs\n";
        cout << "6. Delete Song\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        cin >> choice;

        if (choice == 1) {
            string name, artist, genre, rating;
            cout << "Song name: ";
            cin.ignore();
            getline(cin, name);
            cout << "Artist: ";
            getline(cin, artist);
            cout << "Genre: ";
            getline(cin, genre);
            cout << "Rating (0-5): ";
            getline(cin, rating);

            map<string, string> metadata = {{"genre", genre}, {"rating", rating}};
            musicTrie.insertSong(name, artist, metadata);
            cout << "✓ Song added!\n";
        }
        else if (choice == 2) {
            string prefix;
            cout << "Enter prefix: ";
            cin.ignore();
            getline(cin, prefix);
            auto songs = musicTrie.searchPrefix(prefix);
            cout << "\n--- Search Results ---\n";
            for (size_t i = 0; i < songs.size(); i++) {
                cout << (i + 1) << ". " << songs[i].name
                     << " by " << songs[i].artist << "\n";
            }
        }
        else if (choice == 3) {
            string prefix;
            int limit;
            cout << "Enter prefix: ";
            cin.ignore();
            getline(cin, prefix);
            cout << "Number of suggestions: ";
            cin >> limit;
            auto songs = musicTrie.autoComplete(prefix, limit);
            cout << "\n--- Autocomplete Suggestions ---\n";
            for (size_t i = 0; i < songs.size(); i++) {
                cout << (i + 1) << ". " << songs[i].name
                     << " by " << songs[i].artist << "\n";
            }
        }
        else if (choice == 4) {
            string artist;
            cout << "Enter artist name: ";
            cin.ignore();
            getline(cin, artist);
            auto songs = musicTrie.searchByArtist(artist);
            cout << "\n--- Songs by " << artist << " ---\n";
            for (size_t i = 0; i < songs.size(); i++) {
                cout << (i + 1) << ". " << songs[i].name << "\n";
            }
        }
        else if (choice == 5) {
            auto songs = musicTrie.getAllSongs();
            cout << "\n--- All Songs ---\n";
            for (size_t i = 0; i < songs.size(); i++) {
                cout << (i + 1) << ". " << songs[i].name
                     << " by " << songs[i].artist << "\n";
            }
        }
        else if (choice == 6) {
            string name;
            cout << "Enter song name: ";
            cin.ignore();
            getline(cin, name);
            if (musicTrie.deleteSong(name)) {
                cout << "✓ Song deleted!\n";
            } else {
                cout << "✗ Song not found!\n";
            }
        }
    } while (choice != 0);
}

void frequencyMenu(FrequencyTracker& tracker, MusicTrie& musicTrie) {
    int choice;
    do {
        cout << "\n--- FREQUENCY TRACKING ---\n";
        cout << "1. Play Song (Increment Count)\n";
        cout << "2. View Play Count\n";
        cout << "3. Get Most Played Songs\n";
        cout << "4. Reset All Frequencies\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        cin >> choice;

        if (choice == 1) {
            string songId;
            cout << "Enter song ID/name: ";
            cin.ignore();
            getline(cin, songId);
            tracker.incrementPlayCount(songId);
            cout << "✓ Play count incremented!\n";
        }
        else if (choice == 2) {
            string songId;
            cout << "Enter song ID/name: ";
            cin.ignore();
            getline(cin, songId);
            cout << "Play count: " << tracker.getPlayCount(songId) << "\n";
        }
        else if (choice == 3) {
            int k;
            cout << "How many top songs: ";
            cin >> k;
            auto topSongs = tracker.getMostPlayed(k);
            cout << "\n--- Most Played Songs ---\n";
            for (size_t i = 0; i < topSongs.size(); i++) {
                cout << (i + 1) << ". " << topSongs[i].first
                     << " (" << topSongs[i].second << " plays)\n";
            }
        }
        else if (choice == 4) {
            tracker.resetFrequencies();
            cout << "✓ All frequencies reset!\n";
        }
    } while (choice != 0);
}

void playlistMenu(PlaylistHeap& playlistHeap, MusicTrie& musicTrie) {
    int choice;
    do {
        cout << "\n--- PLAYLIST GENERATION ---\n";
        cout << "1. Generate Playlist\n";
        cout << "2. View Current Playlist\n";
        cout << "3. Add Song to Playlist\n";
        cout << "4. Remove Song from Playlist\n";
        cout << "5. Shuffle Playlist\n";
        cout << "0. Back\n";
        cout << "Choice: ";
        cin >> choice;

        if (choice == 1) {
            int duration;
            string mood, genre;
            cout << "Trip duration (minutes): ";
            cin >> duration;
            cout << "Mood: ";
            cin.ignore();
            getline(cin, mood);
            cout << "Genre: ";
            getline(cin, genre);

            auto songs = musicTrie.getAllSongs();
            playlistHeap.buildMaxHeap(songs, "rating");
            auto playlist = playlistHeap.generatePlaylist(duration, mood, genre);

            cout << "\n✓ Playlist Generated!\n";
            for (size_t i = 0; i < playlist.size(); i++) {
                cout << (i + 1) << ". " << playlist[i].name
                     << " by " << playlist[i].artist << "\n";
            }
        }
        else if (choice == 2) {
            auto playlist = playlistHeap.getCurrentPlaylist();
            cout << "\n--- Current Playlist ---\n";
            for (size_t i = 0; i < playlist.size(); i++) {
                cout << (i + 1) << ". " << playlist[i].name
                     << " by " << playlist[i].artist << "\n";
            }
        }
        else if (choice == 5) {
            auto shuffled = playlistHeap.shufflePlaylist();
            cout << "\n--- Shuffled Playlist ---\n";
            for (size_t i = 0; i < shuffled.size(); i++) {
                cout << (i + 1) << ". " << shuffled[i].name
                     << " by " << shuffled[i].artist << "\n";
            }
        }
    } while (choice != 0);
}

int main() {
    srand(time(0));

    Graph graph;
    ItineraryTree itinerary;
    ActivityManager activityMgr;
    MusicTrie musicTrie;
    FrequencyTracker tracker;
    PlaylistHeap playlistHeap;

    graph.addCity("New York");
    graph.addCity("Boston");
    graph.addCity("Philadelphia");
    graph.addCity("Washington DC");
    graph.addRoute("New York", "Boston", 215, 50, 4);
    graph.addRoute("New York", "Philadelphia", 95, 30, 2);
    graph.addRoute("Philadelphia", "Washington DC", 140, 35, 2.5);
    graph.addRoute("Boston", "Philadelphia", 310, 65, 6);

    activityMgr.addActivityToDB("Statue of Liberty", "New York", "Sightseeing", 25, 4.8, 3);
    activityMgr.addActivityToDB("Central Park", "New York", "Nature", 0, 4.7, 2);
    activityMgr.addActivityToDB("Broadway Show", "New York", "Entertainment", 150, 4.9, 3);

    musicTrie.insertSong("Shape of You", "Ed Sheeran", {{"genre", "Pop"}, {"rating", "4.5"}});
    musicTrie.insertSong("Bohemian Rhapsody", "Queen", {{"genre", "Rock"}, {"rating", "5.0"}});
    musicTrie.insertSong("Blinding Lights", "The Weeknd", {{"genre", "Pop"}, {"rating", "4.7"}});

    int choice;
    do {
        displayMainMenu();
        cin >> choice;

        switch (choice) {
            case 1:
                routePlanningMenu(graph);
                break;
            case 2:
                itineraryMenu(itinerary);
                break;
            case 3:
                activityMenu(activityMgr);
                break;
            case 4:
                musicLibraryMenu(musicTrie);
                break;
            case 5:
                frequencyMenu(tracker, musicTrie);
                break;
            case 6:
                playlistMenu(playlistHeap, musicTrie);
                break;
            case 0:
                cout << "\n Thank you for using Travel Planning System! \n";
                break;
            default:
                cout << "Invalid choice! Please try again.\n";
        }
    } while (choice != 0);

    return 0;
}


