import React, { useEffect, useState } from "react";
import {
  View, Text, FlatList, StyleSheet, ActivityIndicator,
  RefreshControl, TextInput,
} from "react-native";
import { getTodayAttendance } from "../api";

export default function AttendanceScreen() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState("");

  const fetchData = async () => {
    try {
      const { data } = await getTodayAttendance();
      if (data.rows) setRows(data.rows.reverse()); // newest first
    } catch {}
    setLoading(false);
    setRefreshing(false);
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // poll every 5s
    return () => clearInterval(interval);
  }, []);

  const filtered = rows.filter(r =>
    r.name.toLowerCase().includes(search.toLowerCase())
  );

  const renderItem = ({ item }) => {
    const time = item.checkin_time
      ? new Date(item.checkin_time).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
      : "--";
    return (
      <View style={s.row}>
        <View style={s.avatar}>
          <Text style={s.avatarText}>{item.name[0]}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={s.name}>{item.name}</Text>
          <Text style={s.sub}>
            {item.is_expired ? "⚠️ Expired" : `Expires ${item.expiry_date}`}
          </Text>
        </View>
        <Text style={s.time}>{time}</Text>
      </View>
    );
  };

  if (loading) return <ActivityIndicator style={{ flex: 1 }} color="#e94560" />;

  return (
    <View style={s.root}>
      <Text style={s.header}>Today's Attendance <Text style={s.count}>({filtered.length})</Text></Text>
      <TextInput
        style={s.search}
        placeholder="Search name..."
        placeholderTextColor="#888"
        value={search}
        onChangeText={setSearch}
      />
      <FlatList
        data={filtered}
        keyExtractor={i => String(i.id)}
        renderItem={renderItem}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchData(); }} />}
        ListEmptyComponent={<Text style={s.empty}>No check-ins yet today.</Text>}
      />
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#1a1a2e", padding: 16 },
  header: { fontSize: 20, fontWeight: "700", color: "#fff", marginBottom: 12 },
  count: { color: "#e94560" },
  search: { backgroundColor: "#0f3460", color: "#fff", borderRadius: 10, padding: 12, marginBottom: 12 },
  row: { flexDirection: "row", alignItems: "center", backgroundColor: "#16213e", borderRadius: 12, padding: 12, marginBottom: 8 },
  avatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: "#e94560", alignItems: "center", justifyContent: "center", marginRight: 12 },
  avatarText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  name: { color: "#fff", fontWeight: "600", fontSize: 15 },
  sub: { color: "#aaa", fontSize: 12, marginTop: 2 },
  time: { color: "#e94560", fontWeight: "700", fontSize: 14 },
  empty: { color: "#aaa", textAlign: "center", marginTop: 40, fontSize: 15 },
});
